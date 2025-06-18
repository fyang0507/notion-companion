from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from database import get_db
from services.openai_service import get_openai_service
from models import ChatRequest
import json
from typing import AsyncGenerator

router = APIRouter()

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        db = get_db()
        openai_service = get_openai_service()
        
        # Get the latest user message to find relevant sources
        latest_user_message = request.messages[-1].content if request.messages else ""
        
        # Generate embedding for the user's message to find relevant sources
        embedding_response = await openai_service.generate_embedding(latest_user_message)
        
        # Find relevant documents and chunks using vector search
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
        async def generate_stream() -> AsyncGenerator[str, None]:
            try:
                async for chunk in openai_service.generate_streaming_response(messages, context):
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
                
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
                
                yield "data: [DONE]\n\n"
            except Exception as e:
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
        raise HTTPException(status_code=500, detail=f"Chat API error: {str(e)}")