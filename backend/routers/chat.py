from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from database import get_db
from services.openai_service import get_openai_service
from models import ChatRequest
from logging_config import get_logger, log_performance
import json
import time
from typing import AsyncGenerator

router = APIRouter()

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    logger = get_logger(__name__)
    start_time = time.time()
    
    try:
        logger.info("Chat request received", extra={
            'message_count': len(request.messages),
            'selected_databases': request.selected_databases,
            'selected_workspaces': request.selected_workspaces
        })
        
        db = get_db()
        openai_service = get_openai_service()
        
        # Get the latest user message to find relevant sources
        latest_user_message = request.messages[-1].content if request.messages else ""
        logger.debug("Processing user message", extra={
            'message_length': len(latest_user_message),
            'message_preview': latest_user_message[:100] + "..." if len(latest_user_message) > 100 else latest_user_message
        })
        
        # Generate embedding for the user's message to find relevant sources
        embedding_start = time.time()
        embedding_response = await openai_service.generate_embedding(latest_user_message)
        embedding_duration = (time.time() - embedding_start) * 1000
        log_performance("embedding_generation", embedding_duration, 
                       message_length=len(latest_user_message))
        
        # Find relevant documents and chunks using vector search
        search_start = time.time()
        doc_results = db.vector_search_for_single_workspace(
            query_embedding=embedding_response.embedding,
            match_threshold=0.1,  # Lower threshold for better results
            match_count=3
        )
        
        chunk_results = db.vector_search_chunks_for_single_workspace(
            query_embedding=embedding_response.embedding,
            match_threshold=0.1,  # Lower threshold for better results
            match_count=3
        )
        search_duration = (time.time() - search_start) * 1000
        log_performance("vector_search", search_duration,
                       doc_results_count=len(doc_results),
                       chunk_results_count=len(chunk_results))
        
        logger.info("Vector search completed", extra={
            'doc_results': len(doc_results),
            'chunk_results': len(chunk_results),
            'search_duration_ms': search_duration
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
                'content': chunk['chunk_content'],
                'similarity': chunk['similarity'],
                'notion_page_id': chunk['notion_page_id'],
                'page_url': chunk.get('page_url', ''),
                'type': 'chunk',
                'metadata': {'chunk_index': chunk['chunk_index']}
            })
        
        # Sort by similarity and take top 5 sources
        all_sources.sort(key=lambda x: x['similarity'], reverse=True)
        top_sources = all_sources[:5]
        
        # Build context from top sources
        context = "\n\n".join([
            f"Source: {source['title']}\nContent: {source['content'][:500]}"
            for source in top_sources
        ]) if top_sources else None
        
        # Convert messages to dict format
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Generate streaming response
        logger.info("Starting streaming response generation", extra={
            'context_length': len(context) if context else 0,
            'top_sources_count': len(top_sources)
        })
        
        async def generate_stream() -> AsyncGenerator[str, None]:
            stream_start = time.time()
            chunks_generated = 0
            
            try:
                async for chunk in openai_service.generate_streaming_response(messages, context):
                    chunks_generated += 1
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
                
                stream_duration = (time.time() - stream_start) * 1000
                log_performance("llm_streaming", stream_duration,
                               chunks_generated=chunks_generated,
                               context_length=len(context) if context else 0)
                
                # After streaming content, send citations
                if top_sources:
                    citations = []
                    for source in top_sources:
                        citations.append({
                            'id': source['id'],
                            'title': source['title'],
                            'url': source['page_url'] or f"notion://{source['notion_page_id']}",
                            'preview': source['content'][:200] + '...' if len(source['content']) > 200 else source['content'],
                            'score': round(source['similarity'], 2),
                            'type': source['type'],
                            'metadata': source['metadata']
                        })
                    yield f"data: {json.dumps({'citations': citations})}\n\n"
                    
                    logger.info("Citations sent", extra={
                        'citations_count': len(citations)
                    })
                
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