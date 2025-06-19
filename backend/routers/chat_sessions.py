"""
Chat Sessions API router for managing chat conversations.
Provides endpoints for creating, retrieving, updating, and deleting chat sessions.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import uuid

from database import get_db
from logging_config import get_logger

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
    workspace_id: str
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
    message_count: int
    last_message_at: datetime
    created_at: datetime
    last_message_preview: Optional[str] = None

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_default_workspace_id(db):
    """Get the default workspace ID for single-workspace model."""
    try:
        workspace_id = db.get_active_workspace_id()
        if workspace_id:
            return workspace_id
        else:
            raise HTTPException(status_code=404, detail="No active workspace found")
    except Exception as e:
        logger.error(f"Error getting default workspace: {e}")
        raise HTTPException(status_code=500, detail="Failed to get workspace")

def generate_chat_title(first_message: str) -> str:
    """Generate a chat title from the first user message."""
    if len(first_message) <= 50:
        return first_message
    return first_message[:47] + "..."

# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/recent", response_model=List[RecentChatSummary])
async def get_recent_chats(
    limit: int = 20,
    db=Depends(get_db)
):
    """Get recent chat sessions for the current workspace."""
    try:
        # First check if chat_sessions table exists
        table_check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'chat_sessions'
        );
        """
        
        table_exists_result = db.execute_query(table_check_query)
        if not table_exists_result or not table_exists_result[0]['exists']:
            logger.info("Chat sessions table does not exist, returning empty list")
            return []
        
        # Only try to get workspace ID after confirming tables exist
        try:
            workspace_id = get_default_workspace_id(db)
        except HTTPException:
            # If no workspace exists, return empty list
            logger.info("No workspace found, returning empty chat list")
            return []
        
        # Check if the function exists
        function_check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.routines 
            WHERE routine_schema = 'public' 
            AND routine_name = 'get_recent_chat_sessions'
        );
        """
        
        function_exists_result = db.execute_query(function_check_query)
        if function_exists_result and function_exists_result[0]['exists']:
            # Use the database function to get recent chats
            query = """
            SELECT * FROM get_recent_chat_sessions(%s, %s)
            """
            result = db.execute_query(query, (workspace_id, limit))
        else:
            # Fallback to direct table query if function doesn't exist
            logger.warning("get_recent_chat_sessions function not found, using direct query")
            query = """
            SELECT 
                cs.id,
                cs.title,
                cs.summary,
                cs.message_count,
                cs.last_message_at,
                cs.created_at,
                (
                    SELECT cm.content
                    FROM chat_messages cm
                    WHERE cm.session_id = cs.id
                    ORDER BY cm.message_order DESC
                    LIMIT 1
                ) as last_message_preview
            FROM chat_sessions cs
            WHERE cs.workspace_id = %s AND cs.status = 'active'
            ORDER BY cs.last_message_at DESC
            LIMIT %s
            """
            result = db.execute_query(query, (workspace_id, limit))
        
        recent_chats = []
        for row in result:
            recent_chats.append(RecentChatSummary(
                id=str(row['id']),
                title=row['title'],
                summary=row['summary'],
                message_count=row['message_count'],
                last_message_at=row['last_message_at'],
                created_at=row['created_at'],
                last_message_preview=row['last_message_preview']
            ))
        
        logger.info(f"Retrieved {len(recent_chats)} recent chats")
        return recent_chats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recent chats: {e}")
        # Return empty list instead of raising error for better UX
        logger.info("Returning empty chat list due to error")
        return []

@router.post("/", response_model=ChatSession)
async def create_chat_session(
    session_data: ChatSessionCreate,
    db=Depends(get_db)
):
    """Create a new chat session."""
    try:
        # Check if chat_sessions table exists
        table_check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'chat_sessions'
        );
        """
        
        table_exists_result = db.execute_query(table_check_query)
        if not table_exists_result or not table_exists_result[0]['exists']:
            raise HTTPException(
                status_code=503, 
                detail="Chat sessions feature not available. Please deploy the chat sessions database schema first."
            )
        
        workspace_id = get_default_workspace_id(db)
        session_id = str(uuid.uuid4())
        
        # Default title if not provided
        title = session_data.title or "New Chat"
        
        query = """
        INSERT INTO chat_sessions (id, workspace_id, title, summary, session_context)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING *
        """
        
        result = db.execute_query(
            query, 
            (session_id, workspace_id, title, session_data.summary, session_data.session_context)
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create chat session")
        
        row = result[0]
        chat_session = ChatSession(
            id=str(row['id']),
            workspace_id=str(row['workspace_id']),
            title=row['title'],
            summary=row['summary'],
            status=row['status'],
            message_count=row['message_count'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            last_message_at=row['last_message_at'],
            session_context=row['session_context'] or {}
        )
        
        logger.info(f"Created new chat session: {session_id}")
        return chat_session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating chat session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create chat session")

@router.get("/{session_id}", response_model=ChatSessionWithMessages)
async def get_chat_session(
    session_id: str,
    db=Depends(get_db)
):
    """Get a chat session with all its messages."""
    try:
        # Use the database function to get session with messages
        query = "SELECT get_chat_session_with_messages(%s) as session_data"
        result = db.execute_query(query, (session_id,))
        
        if not result or not result[0]['session_data']:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        session_data = result[0]['session_data']
        
        # Parse the session data
        session_info = session_data['session']
        messages_info = session_data['messages']
        
        session = ChatSession(
            id=str(session_info['id']),
            workspace_id=str(session_info['workspace_id']),
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
        check_query = "SELECT id FROM chat_sessions WHERE id = %s"
        check_result = db.execute_query(check_query, (session_id,))
        
        if not check_result:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Build update query dynamically
        update_fields = []
        params = []
        
        if session_update.title is not None:
            update_fields.append("title = %s")
            params.append(session_update.title)
        
        if session_update.summary is not None:
            update_fields.append("summary = %s")
            params.append(session_update.summary)
        
        if session_update.status is not None:
            update_fields.append("status = %s")
            params.append(session_update.status)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        update_fields.append("updated_at = NOW()")
        params.append(session_id)
        
        query = f"""
        UPDATE chat_sessions 
        SET {', '.join(update_fields)}
        WHERE id = %s
        RETURNING *
        """
        
        result = db.execute_query(query, params)
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to update chat session")
        
        row = result[0]
        chat_session = ChatSession(
            id=str(row['id']),
            workspace_id=str(row['workspace_id']),
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
            query = """
            UPDATE chat_sessions 
            SET status = 'deleted', updated_at = NOW()
            WHERE id = %s
            RETURNING id
            """
        else:
            # Hard delete
            query = "DELETE FROM chat_sessions WHERE id = %s RETURNING id"
        
        result = db.execute_query(query, (session_id,))
        
        if not result:
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
        # Check if session exists
        check_query = "SELECT id FROM chat_sessions WHERE id = %s AND status = 'active'"
        check_result = db.execute_query(check_query, (session_id,))
        
        if not check_result:
            raise HTTPException(status_code=404, detail="Active chat session not found")
        
        # Get next message order
        order_query = """
        SELECT COALESCE(MAX(message_order), -1) + 1 as next_order 
        FROM chat_messages 
        WHERE session_id = %s
        """
        order_result = db.execute_query(order_query, (session_id,))
        next_order = order_result[0]['next_order'] if order_result else 0
        
        # Generate title from first user message if needed
        if next_order == 0 and message_data.role == 'user':
            title = generate_chat_title(message_data.content)
            update_title_query = """
            UPDATE chat_sessions 
            SET title = %s, updated_at = NOW()
            WHERE id = %s AND title = 'New Chat'
            """
            db.execute_query(update_title_query, (title, session_id))
        
        message_id = str(uuid.uuid4())
        
        # Insert message
        insert_query = """
        INSERT INTO chat_messages (
            id, session_id, role, content, model_used, tokens_used, 
            response_time_ms, citations, context_used, message_order
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
        """
        
        result = db.execute_query(
            insert_query,
            (
                message_id, session_id, message_data.role, message_data.content,
                message_data.model_used, message_data.tokens_used, message_data.response_time_ms,
                message_data.citations, message_data.context_used, next_order
            )
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to add message")
        
        row = result[0]
        message = ChatMessage(
            id=str(row['id']),
            session_id=str(row['session_id']),
            role=row['role'],
            content=row['content'],
            model_used=row['model_used'],
            tokens_used=row['tokens_used'],
            response_time_ms=row['response_time_ms'],
            citations=row['citations'] or [],
            context_used=row['context_used'] or {},
            created_at=row['created_at'],
            message_order=row['message_order']
        )
        
        logger.info(f"Added message to session {session_id}: {message_id}")
        return message
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding message to session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to add message")

@router.post("/{session_id}/save")
async def save_chat_session(
    session_id: str,
    messages: List[ChatMessageCreate],
    db=Depends(get_db)
):
    """Save multiple messages to a chat session at once."""
    try:
        # Check if session exists
        check_query = "SELECT id FROM chat_sessions WHERE id = %s AND status = 'active'"
        check_result = db.execute_query(check_query, (session_id,))
        
        if not check_result:
            raise HTTPException(status_code=404, detail="Active chat session not found")
        
        # Get current message count
        count_query = "SELECT COALESCE(MAX(message_order), -1) as max_order FROM chat_messages WHERE session_id = %s"
        count_result = db.execute_query(count_query, (session_id,))
        start_order = (count_result[0]['max_order'] if count_result else -1) + 1
        
        saved_messages = []
        
        for i, message_data in enumerate(messages):
            message_id = str(uuid.uuid4())
            message_order = start_order + i
            
            # Generate title from first user message if this is the first message
            if message_order == 0 and message_data.role == 'user':
                title = generate_chat_title(message_data.content)
                update_title_query = """
                UPDATE chat_sessions 
                SET title = %s, updated_at = NOW()
                WHERE id = %s AND title = 'New Chat'
                """
                db.execute_query(update_title_query, (title, session_id))
            
            # Insert message
            insert_query = """
            INSERT INTO chat_messages (
                id, session_id, role, content, model_used, tokens_used, 
                response_time_ms, citations, context_used, message_order
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """
            
            result = db.execute_query(
                insert_query,
                (
                    message_id, session_id, message_data.role, message_data.content,
                    message_data.model_used, message_data.tokens_used, message_data.response_time_ms,
                    message_data.citations, message_data.context_used, message_order
                )
            )
            
            if result:
                row = result[0]
                saved_messages.append(ChatMessage(
                    id=str(row['id']),
                    session_id=str(row['session_id']),
                    role=row['role'],
                    content=row['content'],
                    model_used=row['model_used'],
                    tokens_used=row['tokens_used'],
                    response_time_ms=row['response_time_ms'],
                    citations=row['citations'] or [],
                    context_used=row['context_used'] or {},
                    created_at=row['created_at'],
                    message_order=row['message_order']
                ))
        
        logger.info(f"Saved {len(saved_messages)} messages to session {session_id}")
        return {"message": f"Saved {len(saved_messages)} messages", "messages": saved_messages}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving messages to session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save messages")