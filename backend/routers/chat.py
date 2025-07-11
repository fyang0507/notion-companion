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
from services.contextual_search_engine import ContextualSearchEngine
from config.model_config import get_model_config
from logging_config import get_logger, log_performance

router = APIRouter()
logger = logging.getLogger(__name__)

def _load_database_configurations() -> List[Dict[str, Any]]:
    """Load all database configurations from databases.toml."""
    config_path = Path(__file__).parent.parent / 'config' / 'databases.toml'
    
    try:
        with open(config_path, 'rb') as f:
            config_data = tomllib.load(f)
        return config_data.get('databases', [])
    except Exception as e:
        logger.error(f"Failed to load database configurations: {str(e)}")
        return []

def _get_field_type_mapping() -> Dict[str, str]:
    """Create a mapping of field names to their configured types."""
    field_type_mapping = {}
    
    configurations = _load_database_configurations()
    for config in configurations:
        metadata_config = config.get('metadata', {})
        for field_name, field_config in metadata_config.items():
            field_type = field_config.get('type', 'text')
            field_type_mapping[field_name] = field_type
    
    return field_type_mapping

def _prepare_chat_filters(request: ChatRequest) -> Dict[str, Any]:
    """Prepare filter parameters for chat with configuration-based field types."""
    filters = {}
    
    # Basic filters
    if request.database_filters:
        filters['database_filter'] = request.database_filters
    if request.content_type_filters:
        filters['content_type_filter'] = request.content_type_filters
    if request.author_filters:
        filters['author_filter'] = request.author_filters
    if request.tag_filters:
        filters['tag_filter'] = request.tag_filters
    if request.status_filters:
        filters['status_filter'] = request.status_filters
    
    # Date range filter
    if request.date_range_filter:
        date_range = {}
        if request.date_range_filter.from_date:
            date_range['from'] = request.date_range_filter.from_date.isoformat()
        if request.date_range_filter.to_date:
            date_range['to'] = request.date_range_filter.to_date.isoformat()
        if date_range:
            filters['date_range_filter'] = date_range
    
    # Metadata filters based on configuration
    if request.metadata_filters:
        # Get field type mappings from configuration
        field_type_mapping = _get_field_type_mapping()
        
        # Separate filters by configured field type
        text_filters = {}
        number_filters = {}
        select_filters = {}
        checkbox_filters = {}
        
        for filter_item in request.metadata_filters:
            field_name = filter_item.field_name
            operator = filter_item.operator
            values = filter_item.values
            
            # Get field type from configuration
            field_type = field_type_mapping.get(field_name)
            
            if not field_type:
                logger.warning(f"Field '{field_name}' not found in configuration, skipping filter")
                continue
            
            # Route to appropriate filter type based on configuration
            if field_type in ['text', 'rich_text']:
                if operator == 'equals':
                    text_filters[field_name] = values[0] if values else ""
                elif operator == 'in':
                    text_filters[field_name] = values
                elif operator == 'contains':
                    text_filters[field_name] = values
                    
            elif field_type in ['select', 'status']:
                if operator == 'equals':
                    select_filters[field_name] = values[0] if values else ""
                elif operator == 'in':
                    select_filters[field_name] = values
                    
            elif field_type == 'multi_select':
                # Multi-select maps to tag_filter
                if operator == 'equals':
                    if field_name not in filters:
                        filters['tag_filter'] = {field_name: [values[0]] if values else []}
                    else:
                        filters['tag_filter'][field_name] = [values[0]] if values else []
                elif operator == 'in':
                    if field_name not in filters:
                        filters['tag_filter'] = {field_name: values}
                    else:
                        filters['tag_filter'][field_name] = values
                        
            elif field_type == 'number':
                if operator == 'range' and values:
                    range_filter = {}
                    for value in values:
                        str_value = str(value)
                        if str_value.startswith('min:'):
                            range_filter['min'] = float(str_value[4:])
                        elif str_value.startswith('max:'):
                            range_filter['max'] = float(str_value[4:])
                    
                    if range_filter:
                        number_filters[field_name] = range_filter
                elif operator == 'equals':
                    number_filters[field_name] = {'equals': float(values[0]) if values else 0}
                    
            elif field_type == 'checkbox':
                if operator == 'equals' and values:
                    bool_value = str(values[0]).lower() in ['true', '1', 'yes']
                    checkbox_filters[field_name] = bool_value
                    
            elif field_type == 'date':
                # Date fields map to date_range_filter
                if operator == 'range' and values:
                    date_range = {}
                    for value in values:
                        str_value = str(value)
                        if str_value.startswith('from:'):
                            date_range['from'] = str_value[5:]
                        elif str_value.startswith('to:'):
                            date_range['to'] = str_value[3:]
                    
                    if date_range:
                        if 'date_range_filter' not in filters:
                            filters['date_range_filter'] = {}
                        filters['date_range_filter'].update(date_range)
        
        # Add type-specific filters to the main filters dict
        if text_filters:
            filters['text_filter'] = text_filters
        if number_filters:
            filters['number_filter'] = number_filters
        if select_filters:
            filters['select_filter'] = select_filters
        if checkbox_filters:
            filters['checkbox_filter'] = checkbox_filters
    
    return filters

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
        
        # Generate embedding for the user's message to find relevant sources
        embedding_start = time.time()
        embedding_response = await openai_service.generate_embedding(latest_user_message)
        embedding_duration = (time.time() - embedding_start) * 1000
        log_performance("embedding_generation", embedding_duration, 
                       message_length=len(latest_user_message))
        
        # Find relevant documents and chunks using enhanced metadata search when filters are provided
        # Check if advanced metadata filters are provided
        filters = _prepare_chat_filters(request)
        has_advanced_filters = any(key in filters for key in [
            'metadata_filters', 'author_filter', 'tag_filter', 'status_filter', 'date_range_filter',
            'text_filter', 'number_filter', 'select_filter', 'checkbox_filter'
        ])
        
        search_start = time.time()
        
        if has_advanced_filters:
            # Use enhanced metadata search for advanced filtering
            contextual_engine = ContextualSearchEngine(db, openai_service, search_config)
            combined_results = await contextual_engine.enhanced_metadata_search(
                query=latest_user_message,
                filters=filters,
                match_threshold=search_config.match_threshold,
                match_count=search_config.match_count_default * 2  # Get more results to separate docs/chunks
            )
            
            # Separate documents and chunks from combined results
            doc_results = [r for r in combined_results if r.get('result_type') == 'document']
            chunk_results = [r for r in combined_results if r.get('result_type') == 'chunk']
            
            search_method = "enhanced_metadata_search"
        else:
            # Use standard vector search for basic database filtering
            database_filter = request.database_filters if request.database_filters else None
            
            doc_results = db.vector_search_documents(
                query_embedding=embedding_response.embedding,
                database_filter=database_filter,
                match_threshold=search_config.match_threshold,
                match_count=search_config.match_count_default
            )
            
            chunk_results = db.vector_search_chunks(
                query_embedding=embedding_response.embedding,
                database_filter=database_filter,
                match_threshold=search_config.match_threshold,
                match_count=search_config.match_count_default
            )
            
            search_method = "vector_search"
        
        search_duration = (time.time() - search_start) * 1000
        log_performance(search_method, search_duration,
                       doc_results_count=len(doc_results),
                       chunk_results_count=len(chunk_results))
        
        logger.info(f"{search_method} completed", extra={
            'doc_results': len(doc_results),
            'chunk_results': len(chunk_results),
            'search_duration_ms': search_duration,
            'threshold_used': search_config.match_threshold
        })
        
        # Combine and sort all results by similarity
        all_sources = []
        
        # Add document results
        for doc in doc_results:
            all_sources.append({
                'id': doc['id'],
                'title': doc['title'],
                'content': doc['content'],
                'similarity': doc['similarity'],
                'notion_page_id': doc['notion_page_id'],
                'page_url': doc.get('page_url', ''),
                'type': 'document',
                'metadata': doc.get('metadata', {})
            })
        
        # Add chunk results  
        for chunk in chunk_results:
            all_sources.append({
                'id': chunk['chunk_id'],
                'title': chunk['title'],
                'content': chunk['content'],
                'similarity': chunk['similarity'],
                'notion_page_id': chunk['notion_page_id'],
                'page_url': chunk.get('page_url', ''),
                'type': 'chunk',
                'metadata': {'chunk_index': chunk.get('chunk_index', 0)}
            })
        
        # Sort by similarity and take top sources based on configuration
        all_sources.sort(key=lambda x: x['similarity'], reverse=True)
        top_sources = all_sources[:interface_config.top_sources_limit]
        
        # Check if no relevant documents were found
        if not top_sources:
            logger.info("No relevant documents found for user query", extra={
                'query_preview': latest_user_message[:interface_config.message_preview_length] + "..." if len(latest_user_message) > interface_config.message_preview_length else latest_user_message,
                'doc_results_count': len(doc_results),
                'chunk_results_count': len(chunk_results),
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
                                'database_filters': database_filter or [],
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
                                'database_filters': database_filter or [],
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
                        'database_filters': database_filter or [],
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
                                'database_filters': database_filter or [],
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