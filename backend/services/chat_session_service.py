"""
Chat Session Service for handling chat session lifecycle and metadata updates.
Handles chat conclusion triggers and automatic title/summary regeneration.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
from database import get_db
from logging_config import get_logger
from services.openai_service import get_openai_service

logger = get_logger(__name__)

def is_chinese_text(text: str) -> bool:
    """Check if text contains Chinese characters."""
    chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
    return chinese_chars > len(text) * 0.3  # More than 30% Chinese characters

async def generate_title_from_first_message(first_message: str) -> str:
    """Generate a concise title from the first user message using 8 words/chars rule + GPT."""
    try:
        openai_service = get_openai_service()
        
        # Rule: 8 words (English) or 8 characters (Chinese)
        if is_chinese_text(first_message):
            # Chinese: use 8 characters
            if len(first_message.strip()) <= 8:
                return first_message.strip()
        else:
            # English: use 8 words
            word_count = len(first_message.strip().split())
            if word_count <= 8:
                return first_message.strip()
        
        # Otherwise, use LLM to create a concise title
        messages = [{"role": "user", "content": first_message}]
        
        # Use the existing generate_chat_title method but with 8-word limit
        title = await openai_service.generate_chat_title(messages, max_words=8)
        
        return title if title and title != "New Chat" else first_message.strip()
        
    except Exception as e:
        logger.error(f"Failed to generate title from first message: {e}")
        # Fallback: use first 8 words/chars based on language
        if is_chinese_text(first_message):
            return first_message.strip()[:8]
        else:
            words = first_message.strip().split()
            if len(words) <= 8:
                return first_message.strip()
            return ' '.join(words[:8])

async def generate_ai_chat_title(session_id: str, db) -> str:
    """Generate an AI-powered chat title based on conversation context."""
    try:
        # Get messages for this session
        messages_query = """
        SELECT role, content FROM chat_messages 
        WHERE session_id = %s 
        ORDER BY message_order ASC
        LIMIT 6
        """
        
        result = db.execute_query(messages_query, (session_id,))
        
        if not result or len(result) < 2:  # Need at least user + assistant message
            return "New Chat"
        
        # Convert to format expected by OpenAI service
        messages = [{"role": row['role'], "content": row['content']} for row in result]
        
        # Generate title using AI with 8-word limit
        openai_service = get_openai_service()
        title = await openai_service.generate_chat_title(messages, max_words=8)
        
        return title
        
    except Exception as e:
        logger.error(f"Failed to generate AI title for session {session_id}: {e}")
        # Fallback to simple title if available
        if result and len(result) > 0:
            first_user_msg = next((row['content'] for row in result if row['role'] == 'user'), '')
            if first_user_msg:
                if is_chinese_text(first_user_msg):
                    return first_user_msg[:8] if len(first_user_msg) > 8 else first_user_msg
                else:
                    words = first_user_msg.split()
                    if len(words) <= 8:
                        return first_user_msg
                    else:
                        return ' '.join(words[:8])
        return "New Chat"

async def generate_ai_chat_summary(session_id: str, db) -> str:
    """Generate an AI-powered chat summary based on conversation context."""
    try:
        # Get messages for this session
        messages_query = """
        SELECT role, content FROM chat_messages 
        WHERE session_id = %s 
        ORDER BY message_order ASC
        LIMIT 12
        """
        
        result = db.execute_query(messages_query, (session_id,))
        
        if not result or len(result) < 2:  # Need at least user + assistant message
            return ""
        
        # Convert to format expected by OpenAI service
        messages = [{"role": row['role'], "content": row['content']} for row in result]
        
        # Generate summary using AI
        openai_service = get_openai_service()
        summary = await openai_service.generate_chat_summary(messages)
        
        return summary
        
    except Exception as e:
        logger.error(f"Failed to generate AI summary for session {session_id}: {e}")
        return ""

class ChatSessionService:
    """Service for managing chat session lifecycle and metadata."""
    
    def __init__(self):
        self.db = get_db()
        self._idle_check_task = None
        self._is_running = False
    
    async def start_idle_monitoring(self):
        """Start the idle timeout monitoring task."""
        if self._is_running:
            return
        
        self._is_running = True
        self._idle_check_task = asyncio.create_task(self._monitor_idle_sessions())
        logger.info("Chat session idle monitoring started")
    
    async def stop_idle_monitoring(self):
        """Stop the idle timeout monitoring task."""
        self._is_running = False
        if self._idle_check_task:
            self._idle_check_task.cancel()
            try:
                await self._idle_check_task
            except asyncio.CancelledError:
                pass
        logger.info("Chat session idle monitoring stopped")
    
    async def _monitor_idle_sessions(self):
        """Monitor and conclude idle sessions (10 minutes without activity)."""
        while self._is_running:
            try:
                # Check for sessions idle for more than 10 minutes
                idle_threshold = datetime.now() - timedelta(minutes=10)
                
                # Find active sessions that haven't had messages in 10+ minutes
                idle_sessions_query = """
                SELECT id, title, summary, message_count, last_message_at
                FROM chat_sessions 
                WHERE status = 'active' 
                    AND last_message_at < %s
                    AND message_count >= 2
                """
                
                idle_sessions = self.db.execute_query(idle_sessions_query, (idle_threshold,))
                
                if idle_sessions:
                    logger.info(f"Found {len(idle_sessions)} idle sessions to conclude")
                    
                    for session in idle_sessions:
                        await self._conclude_session_due_to_idle(
                            session_id=str(session['id']),
                            current_title=session['title'],
                            current_summary=session['summary']
                        )
                
                # Sleep for 2 minutes before next check
                await asyncio.sleep(120)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in idle session monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _conclude_session_due_to_idle(self, session_id: str, current_title: str, current_summary: Optional[str]):
        """Conclude a session that has become idle."""
        try:
            logger.info(f"Concluding idle session: {session_id}")
            
            update_data = {
                'status': 'concluded',  # Mark as concluded instead of keeping active
                'updated_at': 'now()'
            }
            
            # Re-generate title based on full conversation
            try:
                ai_title = await generate_ai_chat_title(session_id, self.db)
                if ai_title and ai_title != "New Chat" and ai_title != current_title:
                    update_data['title'] = ai_title
                    logger.info(f"Updated idle session {session_id} title: {ai_title}")
            except Exception as e:
                logger.error(f"Failed to generate title for idle session {session_id}: {e}")
            
            # Generate summary if not exists
            if not current_summary:
                try:
                    ai_summary = await generate_ai_chat_summary(session_id, self.db)
                    if ai_summary:
                        update_data['summary'] = ai_summary
                        logger.info(f"Generated summary for idle session {session_id}: {ai_summary}")
                except Exception as e:
                    logger.error(f"Failed to generate summary for idle session {session_id}: {e}")
            
            # Use Supabase client for update
            update_response = self.db.client.table('chat_sessions').update(
                update_data
            ).eq('id', session_id).eq('status', 'active').execute()  # Only update if still active
            
            if update_response.data:
                logger.info(f"Successfully concluded idle session: {session_id}")
            else:
                logger.error(f"Failed to update idle session: {session_id}")
            
        except Exception as e:
            logger.error(f"Error concluding idle session {session_id}: {e}")
    
    async def conclude_session(self, session_id: str, reason: str = "manual") -> dict:
        """
        Conclude a chat session and regenerate title/summary.
        
        Args:
            session_id: The session to conclude
            reason: Reason for conclusion ('new_chat', 'window_close', 'window_refresh', 'resume_other', 'idle', 'manual')
        
        Returns:
            dict with updated title and summary
        """
        try:
            # Get current session info (allow active and concluded sessions)
            session_query = """
            SELECT id, title, summary, message_count, status
            FROM chat_sessions 
            WHERE id = %s AND status IN ('active', 'concluded')
            """
            
            session_result = self.db.execute_query(session_query, (session_id,))
            
            if not session_result:
                raise ValueError(f"Session not found: {session_id}")
            
            session_info = session_result[0]
            current_title = session_info['title']
            current_summary = session_info['summary']
            message_count = session_info['message_count']
            
            # Only process if there are meaningful conversations
            if message_count < 2:
                logger.info(f"Session {session_id} has insufficient content for conclusion (message_count: {message_count})")
                return {"message": "Session has insufficient content for conclusion"}
            
            logger.info(f"Processing session {session_id} for conclusion (message_count: {message_count}, reason: {reason})")
            
            update_data = {}
            
            # Always re-generate title with AI at session conclusion
            try:
                ai_title = await generate_ai_chat_title(session_id, self.db)
                if ai_title and ai_title != "New Chat" and ai_title != current_title:
                    update_data['title'] = ai_title
                    logger.info(f"Re-generated session {session_id} title on conclusion ({reason}): {ai_title}")
            except Exception as e:
                logger.error(f"Failed to generate title during conclusion: {e}")
            
            # Always generate summary at session conclusion
            try:
                ai_summary = await generate_ai_chat_summary(session_id, self.db)
                if ai_summary and ai_summary != current_summary:
                    update_data['summary'] = ai_summary
                    logger.info(f"Generated summary for session {session_id} on conclusion ({reason}): {ai_summary}")
            except Exception as e:
                logger.error(f"Failed to generate summary during conclusion: {e}")
            
            update_data['status'] = 'concluded'  # Mark as concluded
            update_data['updated_at'] = 'now()'
            
            # Update session (allow updating both active and concluded sessions)
            current_status = session_info['status']
            
            # Only update status if it's currently active
            if current_status == 'active':
                update_response = self.db.client.table('chat_sessions').update(
                    update_data
                ).eq('id', session_id).execute()
            else:
                # For already concluded sessions, just update title/summary if needed
                update_data_without_status = {k: v for k, v in update_data.items() if k != 'status'}
                if update_data_without_status:
                    update_response = self.db.client.table('chat_sessions').update(
                        update_data_without_status
                    ).eq('id', session_id).execute()
                else:
                    # No updates needed
                    update_response = type('obj', (object,), {'data': [{'id': session_id}]})()
            
            if update_response.data:
                logger.info(f"Successfully processed session {session_id} conclusion request due to {reason}")
                # Get the updated title and summary from what we just set
                final_title = update_data.get('title', current_title)
                final_summary = update_data.get('summary', current_summary)
                return {
                    "message": f"Session processed successfully ({reason})",
                    "title": final_title,
                    "summary": final_summary
                }
            else:
                return {
                    "message": f"Session not found ({reason})",
                    "title": current_title,
                    "summary": current_summary
                }
            
        except Exception as e:
            logger.error(f"Error concluding session {session_id}: {e}")
            raise
    
    async def handle_new_chat_trigger(self, current_session_id: Optional[str] = None) -> dict:
        """Handle chat conclusion when user starts a new chat."""
        if current_session_id:
            return await self.conclude_session(current_session_id, "new_chat")
        return {"message": "No current session to conclude"}
    
    async def handle_window_close_trigger(self, session_id: str) -> dict:
        """Handle chat conclusion when user closes the webapp window."""
        return await self.conclude_session(session_id, "window_close")
    
    async def handle_window_refresh_trigger(self, session_id: str) -> dict:
        """Handle chat conclusion when user refreshes the webapp window."""
        return await self.conclude_session(session_id, "window_refresh")
    
    async def handle_resume_other_trigger(self, current_session_id: str, resuming_session_id: str) -> dict:
        """Handle chat conclusion when user resumes another conversation."""
        result = await self.conclude_session(current_session_id, "resume_other")
        logger.info(f"Concluded session {current_session_id} to resume {resuming_session_id}")
        
        # Resume the target session
        success = self.db.resume_session(resuming_session_id)
        if success:
            logger.info(f"Successfully resumed session {resuming_session_id}")
            result["resumed_session"] = resuming_session_id
        else:
            logger.error(f"Failed to resume session {resuming_session_id}")
            result["error"] = f"Failed to resume session {resuming_session_id}"
        
        return result
    
    async def ensure_single_active_session(self, target_session_id: str) -> dict:
        """Ensure only one session is active at a time."""
        try:
            # Get current active session
            current_active = self.db.get_active_session()
            
            if current_active and current_active['id'] != target_session_id:
                # Conclude the current active session
                await self.conclude_session(current_active['id'], "new_session_started")
                logger.info(f"Concluded previous active session {current_active['id']} to make room for {target_session_id}")
            
            # Resume/activate the target session if it's concluded
            if not current_active or current_active['id'] != target_session_id:
                success = self.db.resume_session(target_session_id)
                if success:
                    logger.info(f"Activated session {target_session_id}")
                    return {"message": f"Session {target_session_id} is now active"}
                else:
                    logger.error(f"Failed to activate session {target_session_id}")
                    return {"message": f"Failed to activate session {target_session_id}"}
            
            return {"message": f"Session {target_session_id} is already active"}
            
        except Exception as e:
            logger.error(f"Error ensuring single active session: {e}")
            raise

# Global service instance
_chat_session_service = None

def get_chat_session_service() -> ChatSessionService:
    """Get the global chat session service instance."""
    global _chat_session_service
    if _chat_session_service is None:
        _chat_session_service = ChatSessionService()
    return _chat_session_service