from supabase import create_client, Client
import os
from typing import Optional, List, Dict, Any

class Database:
    def __init__(self):
        self.client: Optional[Client] = None
    
    async def init(self):
        supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        supabase_key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")
        
        self.client = create_client(supabase_url, supabase_key)
    
    def get_client(self) -> Client:
        if not self.client:
            raise RuntimeError("Database not initialized. Call init() first.")
        return self.client
    
    def get_single_workspace_id(self) -> Optional[str]:
        """Get the single workspace ID for single-workspace app."""
        response = self.client.table('workspaces').select('id').limit(1).execute()
        if response.data:
            return response.data[0]['id']
        return None
    
    def get_documents(self, workspace_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        response = self.client.table('documents').select(
            'content, title, extracted_metadata'
        ).eq('workspace_id', workspace_id).order(
            'created_at', desc=True
        ).limit(limit).execute()
        
        return response.data
    
    def get_documents_for_single_workspace(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get documents for single-workspace app."""
        workspace_id = self.get_single_workspace_id()
        if not workspace_id:
            return []
        return self.get_documents(workspace_id, limit)
    
    def vector_search(self, query_embedding: List[float], workspace_id: str, 
                          match_threshold: float = 0.7, match_count: int = 10) -> List[Dict[str, Any]]:
        try:
            # Try the hybrid_search_documents function that exists in the database
            response = self.client.rpc('hybrid_search_documents', {
                'query_embedding': query_embedding,
                'workspace_id_param': workspace_id,
                'match_threshold': match_threshold,
                'match_count': match_count
            }).execute()
            return response.data
        except Exception as e:
            print(f"Error in vector_search: {e}")
            return []
    
    def upsert_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        response = self.client.table('documents').upsert(document_data).execute()
        return response.data
    
    def delete_document(self, notion_page_id: str) -> bool:
        # First delete associated chunks
        self.delete_document_chunks_by_page(notion_page_id)
        
        # Then delete the document
        response = self.client.table('documents').delete().eq(
            'notion_page_id', notion_page_id
        ).execute()
        return len(response.data) > 0
    
    def upsert_document_chunks(self, chunks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        response = self.client.table('document_chunks').upsert(chunks_data).execute()
        return response.data
    
    def delete_document_chunks_by_page(self, notion_page_id: str) -> bool:
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
    
    def update_workspace_sync_time(self, workspace_id: str) -> bool:
        from datetime import datetime
        response = self.client.table('workspaces').update({
            'last_sync_at': datetime.utcnow().isoformat()
        }).eq('id', workspace_id).execute()
        return len(response.data) > 0
    
    def vector_search_chunks(self, query_embedding: List[float], workspace_id: str, 
                                 match_threshold: float = 0.7, match_count: int = 10) -> List[Dict[str, Any]]:
        try:
            # For now, return empty list since match_chunks function is not deployed
            # User will need to deploy the full schema.sql to Supabase for chunk search
            print(f"Chunk search not available - schema functions not deployed")
            return []
        except Exception as e:
            print(f"Error in vector_search_chunks: {e}")
            return []
    
    def vector_search_for_single_workspace(self, query_embedding: List[float], 
                                         match_threshold: float = 0.7, match_count: int = 10) -> List[Dict[str, Any]]:
        """Vector search for single-workspace app."""
        workspace_id = self.get_single_workspace_id()
        if not workspace_id:
            return []
        return self.vector_search(query_embedding, workspace_id, match_threshold, match_count)
    
    def vector_search_chunks_for_single_workspace(self, query_embedding: List[float], 
                                                match_threshold: float = 0.7, match_count: int = 10) -> List[Dict[str, Any]]:
        """Vector search chunks for single-workspace app."""
        workspace_id = self.get_single_workspace_id()
        if not workspace_id:
            return []
        return self.vector_search_chunks(query_embedding, workspace_id, match_threshold, match_count)
    
    def get_active_workspace_id(self) -> Optional[str]:
        """Get the active workspace ID for the single-workspace model."""
        try:
            response = self.client.table('workspaces').select('id').eq('is_active', True).order('created_at', desc=True).limit(1).execute()
            if response.data:
                return response.data[0]['id']
            return None
        except Exception as e:
            print(f"Error getting active workspace: {e}")
            return None
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Temporary implementation of execute_query for basic compatibility.
        This is a simplified version that handles specific query patterns.
        """
        try:
            # Handle table existence checks
            if "information_schema.tables" in query and "table_name = 'chat_sessions'" in query:
                try:
                    self.client.table('chat_sessions').select('id').limit(1).execute()
                    return [{'exists': True}]
                except:
                    return [{'exists': False}]
            
            elif "information_schema.tables" in query and "table_name = 'chat_messages'" in query:
                try:
                    self.client.table('chat_messages').select('id').limit(1).execute()
                    return [{'exists': True}]
                except:
                    return [{'exists': False}]
            
            # Handle function existence checks
            elif "information_schema.routines" in query:
                # For now, assume functions don't exist (fallback to direct queries)
                return [{'exists': False}]
            
            # Handle chat session creation
            elif "INSERT INTO chat_sessions" in query:
                if params and len(params) >= 5:
                    session_id, workspace_id, title, summary, session_context = params[:5]
                    response = self.client.table('chat_sessions').insert({
                        'id': session_id,
                        'workspace_id': workspace_id,
                        'title': title,
                        'summary': summary,
                        'session_context': session_context or {}
                    }).execute()
                    return response.data
            
            # Handle basic SELECT queries for chat_sessions
            elif "SELECT id FROM chat_sessions WHERE id =" in query and params:
                session_id = params[0]
                response = self.client.table('chat_sessions').select('id').eq('id', session_id).execute()
                return response.data
            
            # Handle chat session soft delete (UPDATE)
            elif "UPDATE chat_sessions" in query and "SET status = 'deleted'" in query and params:
                from datetime import datetime
                session_id = params[0]
                response = self.client.table('chat_sessions').update({
                    'status': 'deleted',
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('id', session_id).execute()
                # Return the response with id field to match RETURNING id expectation
                if response.data:
                    return [{'id': row['id']} for row in response.data]
                return []
            
            # Handle chat session hard delete
            elif "DELETE FROM chat_sessions WHERE id =" in query and params:
                session_id = params[0]
                response = self.client.table('chat_sessions').delete().eq('id', session_id).execute()
                # Return the response with id field to match RETURNING id expectation
                if response.data:
                    return [{'id': row['id']} for row in response.data]
                return []
            
            # Handle recent chats query (fallback)
            elif "FROM chat_sessions cs" in query and "ORDER BY cs.last_message_at DESC" in query:
                if params and len(params) >= 2:
                    workspace_id, limit = params[:2]
                    response = self.client.table('chat_sessions').select(
                        'id, title, summary, message_count, last_message_at, created_at'
                    ).eq('workspace_id', workspace_id).eq('status', 'active').order(
                        'last_message_at', desc=True
                    ).limit(limit).execute()
                    
                    # Add None for last_message_preview since we don't have chat messages yet
                    result = []
                    for row in response.data:
                        row_dict = dict(row)
                        row_dict['last_message_preview'] = None
                        result.append(row_dict)
                    return result
            
            # Handle more complex queries by returning empty list (graceful degradation)
            else:
                # Silent fallback for unimplemented queries
                return []
                
        except Exception as e:
            print(f"Error in execute_query: {e}")
            return []

# Global database instance
db = Database()

async def init_db():
    await db.init()

def get_db() -> Database:
    return db