"""
Chat endpoint with streaming responses and enhanced metadata filtering.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime, date
from pathlib import Path
import tomllib
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from storage.database import get_db
from api.models.models import *
from ingestion.services.openai_service import get_openai_service
from rag.services.chat_session_service import get_chat_session_service
from rag.services.rag_search_service import RAGSearchService, FilterProcessor
from shared.config.model_config import get_model_config
from shared.logging.logging_config import get_logger, log_performance

router = APIRouter()
logger = logging.getLogger(__name__)

def convert_frontend_filters_to_backend(request: ChatRequest) -> Dict[str, Any]:
    """Convert frontend filter format to backend filter format."""
    filters = {}
    
    # Database filters (already in correct format)
    if request.database_filters:
        filters['database_ids'] = request.database_filters
    
    # Convert metadata filters from Record<string, string[]> to List[MetadataFilter]
    if request.metadata_filters:
        backend_metadata_filters = []
        for field_name, values in request.metadata_filters.items():
            backend_metadata_filters.append(MetadataFilter(
                field_name=field_name,
                operator='in',
                values=values
            ))
        filters['metadata_filters'] = backend_metadata_filters
    
    # Content type filters (already in correct format)
    if request.content_type_filters:
        filters['content_type_filters'] = request.content_type_filters
    
    # Convert date range filter from frontend format to backend format
    if request.date_range_filter:
        backend_date_filter = DateRangeFilter()
        if request.date_range_filter.from_:
            try:
                backend_date_filter.from_date = datetime.fromisoformat(request.date_range_filter.from_).date()
            except ValueError:
                pass
        if request.date_range_filter.to:
            try:
                backend_date_filter.to_date = datetime.fromisoformat(request.date_range_filter.to).date()
            except ValueError:
                pass
        filters['date_range_filter'] = backend_date_filter
    
    # Search query filter (used in full-text search)
    if request.search_query_filter:
        filters['search_query_filter'] = request.search_query_filter
    
    return filters

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    logger = get_logger(__name__)
    start_time = time.time()
    
    try:
        logger.info("Chat request received", extra={
            'message_count': len(request.messages),
            'session_id': request.session_id,
            'stream': request.stream
        })
        
        db = get_db()
        
        # Database should be guaranteed to be initialized at startup
        # If this fails, it indicates a serious application state issue
        if db.client is None:
            logger.error("CRITICAL: Database client is None despite startup initialization")
            raise HTTPException(status_code=500, detail="Database connection lost - server restart required")
        
        openai_service = get_openai_service()
        chat_service = get_chat_session_service()
        model_config = get_model_config()
        
        # Extract latest user message
        latest_user_message = None
        for message in reversed(request.messages):
            if message.role == "user":
                latest_user_message = message
                break
        
        if not latest_user_message:
            raise HTTPException(status_code=400, detail="No user message found")
        
        # Check if this is a streaming request
        if request.stream:
            return StreamingResponse(
                chat_stream_generator(
                    request, 
                    latest_user_message, 
                    db, 
                    openai_service, 
                    chat_service, 
                    model_config
                ),
                media_type="text/event-stream"
            )
        else:
            # Handle non-streaming request
            response = await generate_chat_response(
                request,
                latest_user_message,
                db,
                openai_service,
                chat_service,
                model_config
            )
            
            # Log performance
            duration_ms = (time.time() - start_time) * 1000
            log_performance(
                operation="chat_response",
                duration_ms=duration_ms,
                metadata={
                    'session_id': request.session_id,
                    'message_count': len(request.messages),
                    'response_length': len(response.message),
                    'source_count': len(response.sources)
                }
            )
            
            return response
            
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"Chat request failed: {str(e)}", extra={
            'session_id': request.session_id,
            'duration_ms': duration_ms,
            'error': str(e)
        }, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

async def chat_stream_generator(
    request: ChatRequest,
    latest_user_message: ChatMessage,
    db,
    openai_service,
    chat_service,
    model_config
) -> AsyncGenerator[str, None]:
    """Generate streaming chat response."""
    try:
        # Initialize search service
        search_config = model_config.get_vector_search_config()
        rag_service = RAGSearchService(db, openai_service, search_config)
        
        # Convert frontend filters to backend format
        filters = convert_frontend_filters_to_backend(request)
        
        # Create a temporary SearchRequest-like object for FilterProcessor
        class FilterRequest:
            def __init__(self, filters_dict):
                self.database_filters = filters_dict.get('database_ids')
                self.metadata_filters = filters_dict.get('metadata_filters')
                self.content_type_filters = filters_dict.get('content_type_filters')
                self.date_range_filter = filters_dict.get('date_range_filter')
        
        filter_request = FilterRequest(filters)
        prepared_filters = FilterProcessor.prepare_filters(filter_request)
        
        # Use existing search_and_retrieve method
        search_result = await rag_service.search_and_retrieve(
            query=latest_user_message.content,
            filters=prepared_filters,
            match_count=request.limit or 10
        )
        
        # Extract chunks from search result
        chunks = search_result.get('chunks', [])
        
        # Convert search results to context
        context_chunks = []
        for chunk in chunks:
            # Use enriched content if available, otherwise use regular content
            content = chunk.get('enriched_content', chunk.get('content', ''))
            context_chunks.append(f"Content: {content}")
        
        context = "\n\n".join(context_chunks[:5])  # Limit context
        
        # Generate streaming response
        messages = [
            {"role": "user", "content": latest_user_message.content}
        ]
        
        # Stream the response
        async for chunk in openai_service.generate_streaming_response(messages, context):
            if chunk:
                yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
        
        yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
        
    except Exception as e:
        logger.error(f"Streaming chat failed: {str(e)}")
        yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

async def generate_chat_response(
    request: ChatRequest,
    latest_user_message: ChatMessage,
    db,
    openai_service,
    chat_service,
    model_config
) -> ChatResponse:
    """Generate non-streaming chat response."""
    
    # Initialize search service
    search_config = model_config.get_vector_search_config()
    rag_service = RAGSearchService(db, openai_service, search_config)
    
    # Convert frontend filters to backend format
    filters = convert_frontend_filters_to_backend(request)
    
    # Create a temporary SearchRequest-like object for FilterProcessor
    class FilterRequest:
        def __init__(self, filters_dict):
            self.database_filters = filters_dict.get('database_ids')
            self.metadata_filters = filters_dict.get('metadata_filters')
            self.content_type_filters = filters_dict.get('content_type_filters')
            self.date_range_filter = filters_dict.get('date_range_filter')
    
    filter_request = FilterRequest(filters)
    prepared_filters = FilterProcessor.prepare_filters(filter_request)
    
    # Use existing search_and_retrieve method
    search_result = await rag_service.search_and_retrieve(
        query=latest_user_message.content,
        filters=prepared_filters,
        match_count=request.limit or 10
    )
    
    # Extract chunks from search result
    chunks = search_result.get('chunks', [])
    
    # Convert search results to context
    context_chunks = []
    for chunk in chunks:
        # Use enriched content if available, otherwise use regular content
        content = chunk.get('enriched_content', chunk.get('content', ''))
        context_chunks.append(f"Content: {content}")
    
    context = "\n\n".join(context_chunks[:5])  # Limit context
    
    # Generate response
    messages = [
        {"role": "user", "content": latest_user_message.content}
    ]
    
    response = await openai_service.generate_chat_response(messages, context)
    response_content = response.content
    
    # Convert search results to response format
    sources = []
    for chunk in chunks:
        sources.append(SearchResult(
            id=chunk.get('id', chunk.get('chunk_id', '')),
            title=chunk.get('title', ''),
            content=chunk.get('enriched_content', chunk.get('content', '')),
            similarity=chunk.get('similarity', 0.0),
            metadata=chunk.get('metadata', {}),
            notion_page_id=chunk.get('notion_page_id', '')
        ))
    
    return ChatResponse(
        message=response_content,
        sources=sources,
        session_id=request.session_id,
        tokens_used=0  # TODO: implement token counting
    )