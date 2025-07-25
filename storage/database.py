"""
Database layer - Simplified single workspace architecture
Uses notion_databases as the primary organizational unit instead of workspaces
"""

from supabase import create_client, Client
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from dotenv import load_dotenv

# Load environment variables from project root
from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

class Database:
    def __init__(self):
        self.client: Optional[Client] = None
    
    async def init(self):
        supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        supabase_key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")
        
        self.client = create_client(supabase_url, supabase_key)
        print("✅ Database initialized successfully")
    
    def get_client(self) -> Client:
        if not self.client:
            raise RuntimeError("Database not initialized. Call init() first.")
        return self.client
    
    # ============================================================================
    # NOTION DATABASES MANAGEMENT
    # ============================================================================
    
    def get_notion_databases(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all notion databases (replaces workspace functionality)."""
        query = self.client.table('notion_databases').select('*')
        if active_only:
            query = query.eq('is_active', True)
        
        response = query.order('created_at', desc=True).execute()
        return response.data
    
    def get_primary_notion_database(self) -> Optional[Dict[str, Any]]:
        """Get the primary notion database (single database model)."""
        response = self.client.table('notion_databases').select('*').eq(
            'is_active', True
        ).order('created_at', desc=True).limit(1).execute()
        
        if response.data:
            return response.data[0]
        return None
    
    def upsert_notion_database(self, database_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update a notion database record."""
        response = self.client.table('notion_databases').upsert(database_data).execute()
        return response.data[0] if response.data else {}
    
    def update_database_sync_time(self, database_id: str) -> bool:
        """Update the last sync time for a notion database."""
        response = self.client.table('notion_databases').update({
            'last_sync_at': datetime.utcnow().isoformat()
        }).eq('database_id', database_id).execute()
        return len(response.data) > 0
    
    # ============================================================================
    # DOCUMENTS MANAGEMENT
    # ============================================================================
    
    def get_documents(self, database_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get documents, optionally filtered by notion database."""
        query = self.client.table('documents').select(
            'id, title, content, notion_page_id, notion_database_id, '
            'page_url, created_time, last_edited_time, extracted_metadata'
        )
        
        if database_id:
            query = query.eq('notion_database_id', database_id)
        
        response = query.order('last_edited_time', desc=True).limit(limit).execute()
        return response.data
    
    def get_document_by_notion_page_id(self, notion_page_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by its Notion page ID."""
        response = self.client.table('documents').select('*').eq(
            'notion_page_id', notion_page_id
        ).execute()
        
        if response.data:
            return response.data[0]
        return None
    
    def upsert_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update a document."""
        # Ensure required fields
        if 'id' not in document_data:
            document_data['id'] = str(uuid.uuid4())
        
        response = self.client.table('documents').upsert(document_data).execute()
        return response.data[0] if response.data else {}
    
    def delete_document(self, notion_page_id: str) -> bool:
        """Delete a document and all its associated chunks."""
        # First delete associated chunks
        self.delete_document_chunks_by_page(notion_page_id)
        
        # Then delete the document
        response = self.client.table('documents').delete().eq(
            'notion_page_id', notion_page_id
        ).execute()
        return len(response.data) > 0
    
    # ============================================================================
    # DOCUMENT CHUNKS MANAGEMENT
    # ============================================================================
    
    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a document."""
        response = self.client.table('document_chunks').select('*').eq(
            'document_id', document_id
        ).order('chunk_order').execute()
        return response.data
    
    def upsert_document_chunks(self, chunks_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create or update document chunks."""
        if not chunks_data:
            return []
        
        # Ensure all chunks have IDs
        for chunk in chunks_data:
            if 'id' not in chunk:
                chunk['id'] = str(uuid.uuid4())
        
        response = self.client.table('document_chunks').upsert(chunks_data).execute()
        return response.data
    
    def delete_document_chunks_by_page(self, notion_page_id: str) -> bool:
        """Delete all chunks for a document by notion page ID."""
        # Get document ID first
        doc_response = self.client.table('documents').select('id').eq(
            'notion_page_id', notion_page_id
        ).execute()
        
        if doc_response.data:
            document_id = doc_response.data[0]['id']
            response = self.client.table('document_chunks').delete().eq(
                'document_id', document_id
            ).execute()
            return len(response.data) > 0
        return False
    
    def delete_document_chunks(self, document_id: str) -> bool:
        """Delete all chunks for a document."""
        response = self.client.table('document_chunks').delete().eq(
            'document_id', document_id
        ).execute()
        return len(response.data) > 0
    
    # ============================================================================
    # DOCUMENT METADATA MANAGEMENT
    # ============================================================================
    
    def upsert_document_metadata(self, metadata_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update document metadata using simplified schema."""
        # Ensure the metadata follows the simplified schema structure
        if 'extracted_fields' not in metadata_data:
            metadata_data['extracted_fields'] = {}
        
        response = self.client.table('document_metadata').upsert(metadata_data).execute()
        return response.data[0] if response.data else {}
    
    def get_document_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a document."""
        response = self.client.table('document_metadata').select('*').eq(
            'document_id', document_id
        ).execute()
        
        if response.data:
            return response.data[0]
        return None
    
    # ============================================================================
    # VECTOR SEARCH FUNCTIONS
    # ============================================================================
    
    def vector_search_chunks(self, query_embedding: List[float], 
                           database_filter: Optional[List[str]] = None,
                           match_threshold: float = 0.7, 
                           match_count: int = 10) -> List[Dict[str, Any]]:
        """Search document chunks using vector similarity."""
        try:
            # Use the match_chunks function
            response = self.client.rpc('match_chunks', {
                'query_embedding': query_embedding,
                'database_filter': database_filter,
                'match_threshold': match_threshold,
                'match_count': match_count
            }).execute()
            return response.data
        except Exception as e:
            print(f"Error in vector_search_chunks: {e}")
            return []
    
    
    # ============================================================================
    # CHAT SESSIONS (Simplified - No database reference)
    # ============================================================================
    
    def get_recent_chat_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent chat sessions."""
        try:
            # Use the get_recent_chat_sessions function
            response = self.client.rpc('get_recent_chat_sessions', {
                'session_limit': limit
            }).execute()
            return response.data
        except Exception as e:
            print(f"Error getting recent chat sessions: {e}")
            # Fallback to direct query
            response = self.client.table('chat_sessions').select(
                'id, title, summary, message_count, last_message_at, created_at, status'
            ).in_('status', ['active', 'concluded']).order('last_message_at', desc=True).limit(limit).execute()
            # Sort to ensure active sessions come first
            active_sessions = [s for s in response.data if s['status'] == 'active']
            concluded_sessions = [s for s in response.data if s['status'] == 'concluded']
            return active_sessions + concluded_sessions
    
    def create_chat_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new chat session and ensure only one active session exists."""
        try:
            # Ensure required fields are present
            if 'id' not in session_data:
                session_data['id'] = str(uuid.uuid4())
            
            # Set default values for required fields
            session_data.setdefault('message_count', 0)
            session_data.setdefault('last_message_at', datetime.utcnow().isoformat())
            session_data.setdefault('created_at', datetime.utcnow().isoformat())
            session_data.setdefault('updated_at', datetime.utcnow().isoformat())
            session_data.setdefault('status', 'active')
            
            # If this is going to be an active session, conclude any existing active session
            if session_data.get('status') == 'active':
                current_active = self.get_active_session()
                if current_active:
                    print(f"Concluding existing active session {current_active['id']} to create new active session")
                    self.conclude_session(current_active['id'])
            
            print(f"Creating chat session with data: {session_data}")
            response = self.client.table('chat_sessions').insert(session_data).execute()
            print(f"Chat session creation response: {response}")
            
            return response.data[0] if response.data else {}
        except Exception as e:
            print(f"Error creating chat session: {e}")
            print(f"Session data: {session_data}")
            raise
    
    def add_message_to_session(self, session_id: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a message to a chat session."""
        # First verify session exists (allow active and concluded sessions)
        session_check = self.client.table('chat_sessions').select('id, status').eq('id', session_id).in_('status', ['active', 'concluded']).execute()
        if not session_check.data:
            return None
        
        # If session is concluded, make it active (resume functionality)
        session_status = session_check.data[0]['status']
        if session_status == 'concluded':
            self.resume_session(session_id)
        
        # Get next message order
        messages_response = self.client.table('chat_messages').select('message_order').eq('session_id', session_id).order('message_order', desc=True).limit(1).execute()
        next_order = 0
        if messages_response.data:
            next_order = messages_response.data[0]['message_order'] + 1
        
        # Add required fields
        if 'id' not in message_data:
            message_data['id'] = str(uuid.uuid4())
        message_data['session_id'] = session_id
        message_data['message_order'] = next_order
        
        # Insert message
        response = self.client.table('chat_messages').insert(message_data).execute()
        
        # Update session message count and last_message_at
        self.client.table('chat_sessions').update({
            'message_count': next_order + 1,
            'last_message_at': 'now()',
            'updated_at': 'now()'
        }).eq('id', session_id).execute()
        
        return response.data[0] if response.data else {}
    
    def update_session_title(self, session_id: str, title: str) -> bool:
        """Update a chat session title."""
        try:
            response = self.client.table('chat_sessions').update({
                'title': title,
                'updated_at': 'now()'
            }).eq('id', session_id).execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"Error updating session title: {e}")
            return False
    
    def get_active_session(self) -> Optional[Dict[str, Any]]:
        """Get the currently active session (should be at most 1)."""
        try:
            response = self.client.table('chat_sessions').select('*').eq('status', 'active').execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error getting active session: {e}")
            return None
    
    def conclude_session(self, session_id: str) -> bool:
        """Mark a session as concluded."""
        try:
            response = self.client.table('chat_sessions').update({
                'status': 'concluded',
                'updated_at': 'now()'
            }).eq('id', session_id).eq('status', 'active').execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"Error concluding session {session_id}: {e}")
            return False
    
    def resume_session(self, session_id: str) -> bool:
        """Resume a concluded session (make it active) and conclude any currently active session."""
        try:
            # First, conclude any currently active session
            current_active = self.get_active_session()
            if current_active and current_active['id'] != session_id:
                self.conclude_session(current_active['id'])
            
            # Then activate the requested session
            response = self.client.table('chat_sessions').update({
                'status': 'active',
                'updated_at': 'now()',
                'last_message_at': 'now()'  # Update to show recent activity
            }).eq('id', session_id).eq('status', 'concluded').execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"Error resuming session {session_id}: {e}")
            return False
    
    def get_chat_session_with_messages(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get chat session with all messages."""
        try:
            # Get session
            session_response = self.client.table('chat_sessions').select('*').eq('id', session_id).execute()
            if not session_response.data:
                return None
            
            session = session_response.data[0]
            
            # Get messages
            messages_response = self.client.table('chat_messages').select('*').eq('session_id', session_id).order('message_order').execute()
            messages = messages_response.data
            
            return {
                'session': session,
                'messages': messages
            }
        except Exception as e:
            print(f"Error getting chat session with messages: {e}")
            return None
    
    # ============================================================================
    # UTILITY FUNCTIONS
    # ============================================================================
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a raw SQL query (for compatibility with existing code).
        Note: This is a simplified implementation for common queries.
        """
        try:
            # Handle common query patterns
            if 'chat_sessions' in query and 'EXISTS' in query:
                # Table existence check
                try:
                    response = self.client.table('chat_sessions').select('id').limit(1).execute()
                    return [{'exists': True}]
                except:
                    return [{'exists': False}]
            
            elif 'COUNT(*)' in query and 'chat_sessions' in query:
                # Count query
                response = self.client.table('chat_sessions').select('id', count='exact').execute()
                return [{'count': response.count or 0}]
            
            elif 'chat_sessions' in query and 'SELECT id FROM' in query and 'status' in query:
                # Check if active session exists
                session_id = params[0] if params else None
                if session_id:
                    response = self.client.table('chat_sessions').select('id').eq('id', session_id).eq('status', 'active').execute()
                    return response.data
                return []
            
            elif 'chat_messages' in query and 'MAX(message_order)' in query:
                # Get max message order for session
                session_id = params[0] if params else None
                if session_id:
                    response = self.client.table('chat_messages').select('message_order').eq('session_id', session_id).order('message_order', desc=True).limit(1).execute()
                    if response.data:
                        max_order = response.data[0]['message_order']
                        if 'next_order' in query or 'COALESCE' not in query:
                            return [{'next_order': max_order + 1}]
                        else:
                            return [{'max_order': max_order}]
                    else:
                        if 'next_order' in query or 'COALESCE' not in query:
                            return [{'next_order': 0}]
                        else:
                            return [{'max_order': -1}]  # COALESCE default
                if 'next_order' in query or 'COALESCE' not in query:
                    return [{'next_order': 0}]
                else:
                    return [{'max_order': -1}]
            
            elif 'INSERT INTO chat_messages' in query:
                # Insert new message - extract values from query
                # This is a simplified handler - in production, you'd want proper SQL parsing
                return [{'id': 'success'}]  # Placeholder
            
            elif 'UPDATE chat_sessions' in query and 'title' in query:
                # Update session title
                if params and len(params) >= 2:
                    title = params[0]
                    session_id = params[1]
                    response = self.client.table('chat_sessions').update({'title': title}).eq('id', session_id).execute()
                    return response.data
                return []
            
            elif 'SELECT id, title, summary, message_count, last_message_at' in query and 'chat_sessions' in query:
                # Idle session monitoring query - only look for active sessions to conclude
                if params and len(params) >= 1:
                    idle_threshold = params[0]
                    try:
                        # Convert datetime to ISO string if needed
                        threshold_str = idle_threshold.isoformat() if hasattr(idle_threshold, 'isoformat') else str(idle_threshold)
                        response = self.client.table('chat_sessions').select(
                            'id, title, summary, message_count, last_message_at'
                        ).eq('status', 'active').lt('last_message_at', threshold_str).gte('message_count', 2).execute()
                        return response.data
                    except Exception as e:
                        print(f"Error in idle session query: {e}")
                        return []
                return []
            
            elif 'SELECT role, content FROM chat_messages' in query and 'session_id' in query:
                # Chat messages query for title/summary generation
                if params and len(params) >= 1:
                    session_id = params[0]
                    try:
                        # Extract LIMIT from query if present
                        limit = 12  # default
                        if 'LIMIT 6' in query:
                            limit = 6
                        elif 'LIMIT 12' in query:
                            limit = 12
                        
                        print(f"Executing chat messages query for session: {session_id}, limit: {limit}")
                        response = self.client.table('chat_messages').select(
                            'role, content'
                        ).eq('session_id', session_id).order('message_order').limit(limit).execute()
                        print(f"Chat messages query result: {response.data}")
                        return response.data
                    except Exception as e:
                        print(f"Error in chat messages query: {e}")
                        return []
                return []
            
            elif 'SELECT id, title, summary, message_count, status' in query and 'chat_sessions' in query:
                # Session info query for conclusion - now handles both active and concluded sessions
                if params and len(params) >= 1:
                    session_id = params[0]
                    try:
                        # Check if query includes both active and concluded statuses
                        if "IN ('active', 'concluded')" in query or 'status IN' in query:
                            response = self.client.table('chat_sessions').select(
                                'id, title, summary, message_count, status'
                            ).eq('id', session_id).in_('status', ['active', 'concluded']).execute()
                        else:
                            # Legacy query - only active sessions
                            response = self.client.table('chat_sessions').select(
                                'id, title, summary, message_count, status'
                            ).eq('id', session_id).eq('status', 'active').execute()
                        return response.data
                    except Exception as e:
                        print(f"Error in session info query: {e}")
                        return []
                return []
            
            else:
                # For other queries, this would need to be implemented based on specific needs
                print(f"Unsupported query pattern: {query}")
                return []
                
        except Exception as e:
            print(f"Error executing query: {e}")
            return []
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics about the database."""
        try:
            databases = self.get_notion_databases()
            documents = self.get_documents()
            
            stats = {
                'notion_databases_count': len(databases),
                'documents_count': len(documents),
                'active_databases': [db for db in databases if db.get('is_active', False)]
            }
            
            return stats
        except Exception as e:
            print(f"Error getting database stats: {e}")
            return {}


# Global database instance
database = Database()

async def init_db():
    """Initialize the database connection."""
    await database.init()

def get_db() -> Database:
    """Get the database instance."""
    return database