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
        
        # Get relevant context from documents (single-workspace app)
        documents = db.get_documents_for_single_workspace(limit=5)
        
        context = "\n\n".join([
            f"Document: {doc['title']}\nContent: {doc['content'][:500]}"
            for doc in documents
        ]) if documents else None
        
        # Convert messages to dict format
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Generate streaming response
        async def generate_stream() -> AsyncGenerator[str, None]:
            try:
                async for chunk in openai_service.generate_streaming_response(messages, context):
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
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