"""
Chat endpoint with streaming responses and enhanced metadata filtering.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import tomllib

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from database import get_db
from models import *
from services.openai_service import get_openai_service
from services.chat_session_service import get_chat_session_service
from services.rag_search_service import RAGSearchService, FilterProcessor
from config.model_config import get_model_config
from logging_config import get_logger, log_performance

router = APIRouter()
logger = logging.getLogger(__name__)

# Filter preparation logic moved to shared FilterProcessor in rag_search_service.py

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    logger = get_logger(__name__)
    start_time = time.time()
    
    try:
        logger.info("Chat request received", extra={
            'message_count': len(request.messages)
        })
        
        db = get_db()
        
        # Database should be guaranteed to be initialized at startup
        # If this fails, it indicates a serious application state issue
        if db.client is None:
            logger.error("CRITICAL: Database client is None despite startup initialization")
            raise HTTPException(status_code=500, detail="Database connection lost - server restart required")
        
        openai_service = get_openai_service()
        model_config = get_model_config()
        
        # Get search configuration
        search_config = model_config.get_vector_search_config()
        
        # Get chat interface configuration
        interface_config = model_config.get_chat_interface_config()
        
        # Get chat model configuration for logging
        chat_config = model_config.get_chat_config()
        
        # Get the latest user message to find relevant sources
        latest_user_message = request.messages[-1].content if request.messages else ""
        logger.debug("Processing user message", extra={
            'message_length': len(latest_user_message),
            'message_preview': latest_user_message[:interface_config.message_preview_length] + "..." if len(latest_user_message) > interface_config.message_preview_length else latest_user_message
        })
        
        # Use unified RAG search service (steps 1-5)
        search_start = time.time()
        
        # Initialize RAG search service
        rag_service = RAGSearchService(db, openai_service, search_config)
        
        # Prepare filters using consolidated logic
        filters = FilterProcessor.prepare_filters(request)
        
        # Execute complete RAG pipeline (steps 1-5)
        rag_results = await rag_service.search_and_retrieve(
            query=latest_user_message,
            filters=filters,
            match_threshold=search_config.match_threshold,
            match_count=search_config.match_count_default * 2  # Get more results for source building
        )
        
        # TODO: Step 6 - Agentic iteration (future enhancement)
        # The AI assistant will evaluate if retrieved chunks are sufficient to answer the query.
        # If not, it can:
        # - Modify the query for better semantic matching
        # - Adjust metadata filters to be more inclusive
        # - Try different search strategies
        # - Iterate until satisfactory results are found
        # Example implementation:
        # if not _are_chunks_sufficient(rag_results['chunks'], latest_user_message):
        #     modified_query = await _generate_alternative_query(latest_user_message, rag_results)
        #     expanded_filters = _expand_filters(filters)
        #     rag_results = await rag_service.search_and_retrieve(modified_query, expanded_filters)
        
        search_duration = (time.time() - search_start) * 1000
        search_metadata = rag_results['search_metadata']
        
        logger.info(f"RAG search completed", extra={
            'execution_time_ms': search_metadata['execution_time_ms'],
            'search_strategy': search_metadata['search_strategy'],
            'total_found': search_metadata['total_found'],
            'final_returned': search_metadata['final_returned'],
            'threshold_used': search_config.match_threshold
        })
        
        # Convert RAG results to source format for chat context
        all_sources = []
        for result in rag_results['chunks']:
            # Use enriched content if available for better context
            content = result.get('enriched_content', result.get('content', ''))
            
            all_sources.append({
                'id': result.get('chunk_id', result.get('id', '')),
                'title': result.get('title', ''),
                'content': content,
                'similarity': result.get('final_score', result.get('combined_score', result.get('similarity', 0.0))),
                'notion_page_id': result.get('notion_page_id', ''),
                'page_url': result.get('page_url', ''),
                'type': result.get('result_type', 'chunk'),
                'metadata': result.get('metadata', {})
            })
        
        # Take top sources based on configuration
        top_sources = all_sources[:interface_config.top_sources_limit]
        
        # Check if no relevant documents were found
        if not top_sources:
            logger.info("No relevant documents found for user query", extra={
                'query_preview': latest_user_message[:interface_config.message_preview_length] + "..." if len(latest_user_message) > interface_config.message_preview_length else latest_user_message,
                'total_found': search_metadata['total_found'],
                'threshold_used': search_config.match_threshold
            })
            
            # Return response without routing to LLM - use simple hardcoded multilingual response
            async def generate_no_results_stream() -> AsyncGenerator[str, None]:
                # Simple language detection and hardcoded response to save costs
                def contains_chinese(text):
                    """Simple check if text contains Chinese characters"""
                    return any('\u4e00' <= char <= '\u9fff' for char in text)
                
                if contains_chinese(latest_user_message):
                    no_results_message = "很抱歉，我在您的 Notion 工作区中没有找到与您的问题相关的文档。请尝试重新表述您的问题，或确保相关内容已同步到您的工作区。"
                else:
                    no_results_message = "I couldn't find any relevant documents in your Notion workspace that match your query. Please try rephrasing your question or make sure the relevant content has been synced to your workspace."
                
                yield f"data: {json.dumps({'content': no_results_message})}\n\n"
                
                # Save user message to session if session_id is provided
                if request.session_id and latest_user_message:
                    try:
                        user_message_data = {
                            'role': 'user',
                            'content': latest_user_message,
                            'context_used': {
                                'database_filters': filters.get('database_filter', []),
                                'search_threshold': search_config.match_threshold,
                                'search_results_count': 0
                            }
                        }
                        db.add_message_to_session(request.session_id, user_message_data)
                        
                        # Save assistant no-results message too
                        assistant_message_data = {
                            'role': 'assistant',
                            'content': no_results_message,
                            'citations': [],
                            'context_used': {
                                'database_filters': filters.get('database_filter', []),
                                'search_threshold': search_config.match_threshold,
                                'search_results_count': 0,
                                'model_used': 'no-llm',
                                'response_time_ms': 0
                            }
                        }
                        db.add_message_to_session(request.session_id, assistant_message_data)
                        logger.info(f"Saved no-results conversation to session {request.session_id}")
                    except Exception as e:
                        logger.error(f"Failed to save no-results conversation to session: {e}")
                
                total_duration = (time.time() - start_time) * 1000
                logger.info("Chat request completed - no relevant documents", extra={
                    'total_duration_ms': total_duration
                })
                
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(
                generate_no_results_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        
        # Build context from top sources using configured content length
        context = "\n\n".join([
            f"Source: {source['title']}\nContent: {source['content'][:interface_config.context_content_length]}"
            for source in top_sources
        ])
        
        # Convert messages to dict format
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Save user message to session if session_id is provided
        user_message_content = latest_user_message
        if request.session_id and user_message_content:
            try:
                user_message_data = {
                    'role': 'user',
                    'content': user_message_content,
                    'context_used': {
                        'database_filters': filters.get('database_filter', []),
                        'search_threshold': search_config.match_threshold,
                        'search_results_count': len(top_sources)
                    }
                }
                db.add_message_to_session(request.session_id, user_message_data)
                logger.info(f"Saved user message to session {request.session_id}")
            except Exception as e:
                logger.error(f"Failed to save user message to session: {e}")
        
        # Generate streaming response
        logger.info("Starting streaming response generation", extra={
            'context_length': len(context),
            'top_sources_count': len(top_sources)
        })
        
        async def generate_stream() -> AsyncGenerator[str, None]:
            stream_start = time.time()
            chunks_generated = 0
            assistant_response = ""  # Collect full response for saving
            
            try:
                async for chunk in openai_service.generate_streaming_response(messages, context):
                    chunks_generated += 1
                    assistant_response += chunk  # Collect response
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
                
                stream_duration = (time.time() - stream_start) * 1000
                log_performance("llm_streaming", stream_duration,
                               chunks_generated=chunks_generated,
                               context_length=len(context))
                
                # After streaming content, send citations
                citations = []
                if top_sources:
                    for source in top_sources:
                        citations.append({
                            'id': source['id'],
                            'title': source['title'],
                            'url': source['page_url'] or f"notion://{source['notion_page_id']}",
                            'preview': source['content'][:interface_config.citation_preview_length] + '...' if len(source['content']) > interface_config.citation_preview_length else source['content'],
                            'score': round(source['similarity'], 2),
                            'type': source['type'],
                            'metadata': source['metadata']
                        })
                    yield f"data: {json.dumps({'citations': citations})}\n\n"
                    
                    logger.info("Citations sent", extra={
                        'citations_count': len(citations)
                    })
                
                # Save assistant message to session BEFORE sending [DONE]
                if request.session_id and assistant_response:
                    try:
                        assistant_message_data = {
                            'role': 'assistant',
                            'content': assistant_response,
                            'citations': citations,
                            'context_used': {
                                'database_filters': filters.get('database_filter', []),
                                'search_threshold': search_config.match_threshold,
                                'search_results_count': len(top_sources),
                                'model_used': chat_config.model,  # Get actual model from config
                                'response_time_ms': int(stream_duration)
                            },
                            'tokens_used': chunks_generated,  # Approximate
                            'response_time_ms': int(stream_duration)
                        }
                        db.add_message_to_session(request.session_id, assistant_message_data)
                        logger.info(f"Saved assistant message to session {request.session_id}")
                    except Exception as e:
                        logger.error(f"Failed to save assistant message to session: {e}", exc_info=True)
                
                total_duration = (time.time() - start_time) * 1000
                logger.info("Chat request completed successfully", extra={
                    'total_duration_ms': total_duration,
                    'chunks_generated': chunks_generated
                })
                
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error("Error during streaming response", extra={
                    'error': str(e),
                    'chunks_generated': chunks_generated
                }, exc_info=True)
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        
    except Exception as e:
        total_duration = (time.time() - start_time) * 1000
        logger.error("Chat request failed", extra={
            'error': str(e),
            'duration_ms': total_duration
        }, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat API error: {str(e)}")