"""
Chat Sessions API router for managing chat conversations.
Provides endpoints for creating, retrieving, updating, and deleting chat sessions.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import uuid

from storage.database import get_db
from shared.logging.logging_config import get_logger
from ingestion.services.openai_service import get_openai_service
from rag.services.chat_session_service import (
    get_chat_session_service, 
    generate_title_from_first_message,
    generate_ai_chat_title,
    generate_ai_chat_summary
)

logger = get_logger(__name__)
router = APIRouter(prefix="/api/chat-sessions", tags=["chat-sessions"])

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ChatMessageCreate(BaseModel):
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    model_used: Optional[str] = Field(None, description="AI model used for assistant messages")
    tokens_used: Optional[int] = Field(None, description="Token count for this message")
    response_time_ms: Optional[int] = Field(None, description="Response time for AI messages")
    citations: Optional[List[dict]] = Field(default_factory=list, description="Citations for the message")
    context_used: Optional[dict] = Field(default_factory=dict, description="Context and filters applied")

class ChatMessage(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    model_used: Optional[str] = None
    tokens_used: Optional[int] = None
    response_time_ms: Optional[int] = None
    citations: List[dict] = []
    context_used: dict = {}
    created_at: datetime
    message_order: int

class ChatSessionCreate(BaseModel):
    title: Optional[str] = Field(None, description="Session title (auto-generated if not provided)")
    summary: Optional[str] = Field(None, description="Session summary")
    session_context: Optional[dict] = Field(default_factory=dict, description="Session context and filters")

class ChatSessionUpdate(BaseModel):
    title: Optional[str] = Field(None, description="New session title")
    summary: Optional[str] = Field(None, description="New session summary")
    status: Optional[str] = Field(None, description="New session status")

class ChatSession(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    status: str
    message_count: int
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime
    session_context: dict = {}

class ChatSessionWithMessages(BaseModel):
    session: ChatSession
    messages: List[ChatMessage]

class RecentChatSummary(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    status: str  # 'active', 'concluded', 'deleted'
    message_count: int
    last_message_at: datetime
    created_at: datetime
    last_message_preview: Optional[str] = None

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

# Removed workspace-related functions for simplified schema

# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/recent", response_model=List[RecentChatSummary])
async def get_recent_chats(
    limit: int = 20,
    db=Depends(get_db)
):
    """Get recent chat sessions (simplified - no workspace concept)."""
    try:
        # Use database method
        result = db.get_recent_chat_sessions(limit)
        
        recent_chats = []
        for row in result:
            recent_chats.append(RecentChatSummary(
                id=str(row['id']),
                title=row['title'],
                summary=row['summary'],
                status=row.get('status', 'active'),  # Default to active for backward compatibility
                message_count=row['message_count'],
                last_message_at=row['last_message_at'],
                created_at=row['created_at'],
                last_message_preview=row.get('last_message_preview')
            ))
        
        logger.info(f"Retrieved {len(recent_chats)} recent chats")
        return recent_chats
        
    except Exception as e:
        logger.error(f"Error getting recent chats: {e}")
        # Return empty list instead of raising error for better UX
        return []

@router.post("/", response_model=ChatSession)
async def create_chat_session(
    session_data: ChatSessionCreate,
    db=Depends(get_db)
):
    """Create a new chat session (simplified)."""
    try:
        # Prepare session data
        session_data_dict = {
            'title': session_data.title or "New Chat",
            'summary': session_data.summary,
            'status': 'active',  # Explicitly set status to active
            'session_context': session_data.session_context or {}
        }
        
        # Use database method
        result = db.create_chat_session(session_data_dict)
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create chat session")
        
        chat_session = ChatSession(
            id=str(result['id']),
            title=result['title'],
            summary=result['summary'],
            status=result['status'],
            message_count=result['message_count'],
            created_at=result['created_at'],
            updated_at=result['updated_at'],
            last_message_at=result['last_message_at'],
            session_context=result['session_context'] or {}
        )
        
        logger.info(f"Created new chat session: {result['id']}")
        return chat_session
        
    except Exception as e:
        logger.error(f"Error creating chat session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create chat session")

@router.get("/{session_id}", response_model=ChatSessionWithMessages)
async def get_chat_session(
    session_id: str,
    db=Depends(get_db)
):
    """Get a chat session with all its messages (simplified)."""
    try:
        # Use database method
        result = db.get_chat_session_with_messages(session_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Parse the session data
        session_info = result['session']
        messages_info = result['messages']
        
        session = ChatSession(
            id=str(session_info['id']),
            title=session_info['title'],
            summary=session_info['summary'],
            status=session_info['status'],
            message_count=session_info['message_count'],
            created_at=session_info['created_at'],
            updated_at=session_info['updated_at'],
            last_message_at=session_info['last_message_at'],
            session_context=session_info['session_context'] or {}
        )
        
        messages = []
        for msg in messages_info:
            messages.append(ChatMessage(
                id=str(msg['id']),
                session_id=str(msg['session_id']),
                role=msg['role'],
                content=msg['content'],
                model_used=msg['model_used'],
                tokens_used=msg['tokens_used'],
                response_time_ms=msg['response_time_ms'],
                citations=msg['citations'] or [],
                context_used=msg['context_used'] or {},
                created_at=msg['created_at'],
                message_order=msg['message_order']
            ))
        
        return ChatSessionWithMessages(session=session, messages=messages)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve chat session")

@router.put("/{session_id}", response_model=ChatSession)
async def update_chat_session(
    session_id: str,
    session_update: ChatSessionUpdate,
    db=Depends(get_db)
):
    """Update a chat session."""
    try:
        # Check if session exists
        check_response = db.client.table('chat_sessions').select('id').eq('id', session_id).execute()
        
        if not check_response.data:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Build update data dynamically
        update_data = {}
        
        if session_update.title is not None:
            update_data['title'] = session_update.title
        
        if session_update.summary is not None:
            update_data['summary'] = session_update.summary
        
        if session_update.status is not None:
            update_data['status'] = session_update.status
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        update_data['updated_at'] = 'now()'
        
        # Use Supabase client for update
        update_response = db.client.table('chat_sessions').update(
            update_data
        ).eq('id', session_id).select('*').execute()
        
        if not update_response.data:
            raise HTTPException(status_code=500, detail="Failed to update chat session")
        
        row = update_response.data[0]
        chat_session = ChatSession(
            id=str(row['id']),
            title=row['title'],
            summary=row['summary'],
            status=row['status'],
            message_count=row['message_count'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            last_message_at=row['last_message_at'],
            session_context=row['session_context'] or {}
        )
        
        logger.info(f"Updated chat session: {session_id}")
        return chat_session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating chat session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update chat session")

@router.delete("/{session_id}")
async def delete_chat_session(
    session_id: str,
    soft_delete: bool = True,
    db=Depends(get_db)
):
    """Delete a chat session (soft delete by default)."""
    try:
        if soft_delete:
            # Soft delete by changing status
            result = db.client.table('chat_sessions').update({
                'status': 'deleted',
                'updated_at': 'now()'
            }).eq('id', session_id).execute()
        else:
            # Hard delete
            result = db.client.table('chat_sessions').delete().eq('id', session_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        action = "soft deleted" if soft_delete else "deleted"
        logger.info(f"Chat session {action}: {session_id}")
        
        return {"message": f"Chat session {action} successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chat session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete chat session")

@router.post("/{session_id}/messages", response_model=ChatMessage)
async def add_message_to_session(
    session_id: str,
    message_data: ChatMessageCreate,
    db=Depends(get_db)
):
    """Add a message to a chat session."""
    try:
        # Convert to database format
        message_dict = {
            'role': message_data.role,
            'content': message_data.content,
            'model_used': message_data.model_used,
            'tokens_used': message_data.tokens_used,
            'response_time_ms': message_data.response_time_ms,
            'citations': message_data.citations,
            'context_used': message_data.context_used
        }
        
        # Use database method to add message
        result = db.add_message_to_session(session_id, message_dict)
        
        if not result:
            raise HTTPException(status_code=404, detail="Active chat session not found")
        
        # Generate title from first user message using LLM (max 10 words)
        if result.get('message_order') == 0 and message_data.role == 'user':
            try:
                title = await generate_title_from_first_message(message_data.content)
                success = db.update_session_title(session_id, title)
                if success:
                    logger.info(f"Generated title from first message for session {session_id}: {title}")
            except Exception as e:
                logger.error(f"Failed to generate title from first message: {e}")
                # Keep "New Chat" as fallback
        
        # Convert result to ChatMessage format
        message = ChatMessage(
            id=str(result['id']),
            session_id=str(result['session_id']),
            role=result['role'],
            content=result['content'],
            model_used=result.get('model_used'),
            tokens_used=result.get('tokens_used'),
            response_time_ms=result.get('response_time_ms'),
            citations=result.get('citations') or [],
            context_used=result.get('context_used') or {},
            created_at=result['created_at'],
            message_order=result['message_order']
        )
        
        logger.info(f"Added message to session {session_id}: {result['id']}")
        return message
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding message to session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to add message")



@router.post("/{session_id}/conclude-for-new-chat")
async def conclude_for_new_chat(
    session_id: str,
    db=Depends(get_db)
):
    """
    Conclude current session when starting a new chat.
    Used when user clicks 'New Chat' button.
    """
    try:
        chat_service = get_chat_session_service()
        result = await chat_service.handle_new_chat_trigger(session_id)
        return result
        
    except Exception as e:
        logger.error(f"Error handling new chat trigger: {e}")
        raise HTTPException(status_code=500, detail="Failed to handle new chat")

@router.post("/{session_id}/conclude")
async def conclude_chat_session(
    session_id: str,
    reason: str = "manual",
    db=Depends(get_db)
):
    """
    Conclude a chat session with automatic title/summary regeneration.
    
    Reasons: 'new_chat', 'window_close', 'window_refresh', 'resume_other', 'idle', 'manual'
    """
    try:
        chat_service = get_chat_session_service()
        result = await chat_service.conclude_session(session_id, reason)
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error concluding session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to conclude session")

class ResumeRequest(BaseModel):
    resuming_session_id: str

@router.post("/{session_id}/conclude-for-resume")
async def conclude_for_resume(
    session_id: str,
    request: ResumeRequest,
    db=Depends(get_db)
):
    """
    Conclude current session when resuming another conversation.
    Used when user selects a chat from 'Recent' history.
    """
    try:
        chat_service = get_chat_session_service()
        result = await chat_service.handle_resume_other_trigger(session_id, request.resuming_session_id)
        return result
        
    except Exception as e:
        logger.error(f"Error handling resume trigger: {e}")
        raise HTTPException(status_code=500, detail="Failed to handle resume")

@router.post("/{session_id}/window-close")
async def handle_window_close(
    session_id: str,
    db=Depends(get_db)
):
    """
    Handle session conclusion when user closes the webapp window.
    Should be called by frontend beforeunload event.
    """
    try:
        chat_service = get_chat_session_service()
        result = await chat_service.handle_window_close_trigger(session_id)
        return result
        
    except Exception as e:
        logger.error(f"Error handling window close: {e}")
        raise HTTPException(status_code=500, detail="Failed to handle window close")

@router.post("/{session_id}/window-refresh")
async def handle_window_refresh(
    session_id: str,
    db=Depends(get_db)
):
    """
    Handle session conclusion when user refreshes the webapp window.
    Should be called by frontend before page refresh.
    """
    try:
        chat_service = get_chat_session_service()
        result = await chat_service.handle_window_refresh_trigger(session_id)
        return result
        
    except Exception as e:
        logger.error(f"Error handling window refresh: {e}")
        raise HTTPException(status_code=500, detail="Failed to handle window refresh")

@router.post("/{session_id}/resume")
async def resume_chat_session(
    session_id: str,
    db=Depends(get_db)
):
    """Resume a concluded chat session (making it active and concluding any currently active session)."""
    try:
        chat_service = get_chat_session_service()
        result = await chat_service.ensure_single_active_session(session_id)
        logger.info(f"Resumed chat session {session_id}")
        return result
    except Exception as e:
        logger.error(f"Error resuming session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to resume chat session")

@router.get("/current-active")
async def get_current_active_session(db=Depends(get_db)):
    """Get the currently active session (should be at most 1)."""
    try:
        active_session = db.get_active_session()
        if active_session:
            return {
                "active_session": {
                    "id": str(active_session['id']),
                    "title": active_session['title'],
                    "status": active_session['status'],
                    "last_message_at": active_session['last_message_at']
                }
            }
        else:
            return {"active_session": None}
    except Exception as e:
        logger.error(f"Error getting current active session: {e}")
        raise HTTPException(status_code=500, detail="Failed to get current active session")