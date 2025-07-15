"""Integration tests for database operations."""

import pytest
from unittest.mock import patch, Mock, AsyncMock
import asyncio
from database import Database, get_db, init_db


@pytest.mark.integration
class TestDatabaseIntegration:
    """Integration tests for database operations."""
    
    @pytest.fixture
    async def database_with_mock_client(self, mock_supabase_client):
        """Create database instance with mocked Supabase client."""
        with patch('database.create_client') as mock_create_client:
            mock_create_client.return_value = mock_supabase_client
            
            # Initialize database
            await init_db()
            db = get_db()
            
            yield db
    
    async def test_database_initialization_flow(self, mock_supabase_client):
        """Test complete database initialization flow."""
        with patch('database.create_client') as mock_create_client:
            mock_create_client.return_value = mock_supabase_client
            
            # Test initialization
            await init_db()
            
            # Verify client creation
            mock_create_client.assert_called_once()
            
            # Test get_db after initialization
            db = get_db()
            assert db is not None
            assert db.client == mock_supabase_client
    
    async def test_notion_database_workflow(self, database_with_mock_client, mock_supabase_client):
        """Test complete Notion database management workflow."""
        db = database_with_mock_client
        
        # Mock table operations for notion_databases
        mock_table = Mock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.update.return_value = mock_table
        
        # Mock response for getting databases
        mock_response = Mock()
        mock_response.data = [
            {
                "id": "db-1",
                "name": "Test Database",
                "notion_database_id": "notion-db-1",
                "is_active": True,
                "created_at": "2023-01-01T00:00:00Z"
            }
        ]
        mock_table.execute.return_value = mock_response
        
        # Test getting notion databases
        databases = db.get_notion_databases()
        
        # Verify results
        assert len(databases) == 1
        assert databases[0]["name"] == "Test Database"
        
        # Verify query chain was called correctly
        mock_supabase_client.table.assert_called_with('notion_databases')
        mock_table.select.assert_called_with('*')
        mock_table.eq.assert_called_with('is_active', True)
    
    async def test_document_storage_workflow(self, database_with_mock_client, mock_supabase_client):
        """Test complete document storage workflow."""
        db = database_with_mock_client
        
        # Mock document operations
        mock_table = Mock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        
        # Mock successful insertion
        mock_response = Mock()
        mock_response.data = [{
            "id": "doc-1",
            "title": "Test Document",
            "content": "Test content",
            "database_id": "db-1"
        }]
        mock_table.execute.return_value = mock_response
        
        # Test document insertion
        test_document = {
            "title": "Test Document",
            "content": "Test content", 
            "database_id": "db-1",
            "page_id": "notion-page-1",
            "last_edited": "2023-01-01T00:00:00Z"
        }
        
        result = db.client.table('documents').insert(test_document).execute()
        
        # Verify insertion
        mock_supabase_client.table.assert_called_with('documents')
        mock_table.insert.assert_called_with(test_document)
        assert result.data[0]["title"] == "Test Document"
    
    async def test_vector_search_workflow(self, database_with_mock_client, mock_supabase_client):
        """Test complete vector search workflow."""
        db = database_with_mock_client
        
        # Mock vector search RPC call
        mock_response = Mock()
        mock_response.data = [
            {
                "id": "chunk-1",
                "content": "First matching chunk",
                "similarity": 0.85,
                "document_id": "doc-1",
                "document_title": "Test Document 1",
                "chunk_context": "Context for first chunk"
            },
            {
                "id": "chunk-2",
                "content": "Second matching chunk",
                "similarity": 0.75,
                "document_id": "doc-2", 
                "document_title": "Test Document 2",
                "chunk_context": "Context for second chunk"
            }
        ]
        mock_supabase_client.rpc.return_value.execute.return_value = mock_response
        
        # Test vector search
        test_embedding = [0.1] * 1536
        search_params = {
            'query_embedding': test_embedding,
            'database_filter': ['db-1', 'db-2'],
            'match_threshold': 0.7,
            'match_count': 5
        }
        
        result = db.client.rpc('match_contextual_chunks', search_params).execute()
        
        # Verify search results
        assert len(result.data) == 2
        assert result.data[0]["similarity"] == 0.85
        assert result.data[1]["similarity"] == 0.75
        
        # Verify RPC was called correctly
        mock_supabase_client.rpc.assert_called_with('match_contextual_chunks', search_params)
    
    async def test_chat_session_workflow(self, database_with_mock_client, mock_supabase_client):
        """Test complete chat session workflow."""
        db = database_with_mock_client
        
        # Mock chat session operations
        mock_table = Mock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.update.return_value = mock_table
        
        # Mock session creation response
        mock_create_response = Mock()
        mock_create_response.data = [{
            "id": "session-1",
            "title": "New Chat Session",
            "status": "active",
            "created_at": "2023-01-01T00:00:00Z"
        }]
        
        # Mock message addition response  
        mock_message_response = Mock()
        mock_message_response.data = [{
            "id": "msg-1",
            "session_id": "session-1", 
            "content": "Hello",
            "role": "user",
            "created_at": "2023-01-01T00:00:00Z"
        }]
        
        mock_table.execute.side_effect = [mock_create_response, mock_message_response]
        
        # Test session creation
        new_session = {
            "title": "New Chat Session",
            "status": "active"
        }
        
        session_result = db.client.table('chat_sessions').insert(new_session).execute()
        
        # Test message addition
        new_message = {
            "session_id": "session-1",
            "content": "Hello",
            "role": "user"
        }
        
        message_result = db.client.table('chat_messages').insert(new_message).execute()
        
        # Verify results
        assert session_result.data[0]["title"] == "New Chat Session"
        assert message_result.data[0]["content"] == "Hello"
    
    async def test_contextual_chunk_workflow(self, database_with_mock_client, mock_supabase_client):
        """Test contextual chunk operations workflow."""
        db = database_with_mock_client
        
        # Mock get_chunk_with_context RPC
        mock_response = Mock()
        mock_response.data = {
            "id": "chunk-1",
            "content": "Main chunk content",
            "chunk_context": "This chunk discusses...",
            "chunk_summary": "Summary of the chunk",
            "prev_chunk": {
                "id": "chunk-0",
                "content": "Previous chunk content"
            },
            "next_chunk": {
                "id": "chunk-2", 
                "content": "Next chunk content"
            },
            "document_title": "Test Document"
        }
        mock_supabase_client.rpc.return_value.execute.return_value = mock_response
        
        # Test contextual chunk retrieval
        result = db.client.rpc('get_chunk_with_context', {
            'chunk_id_param': 'chunk-1',
            'include_adjacent': True
        }).execute()
        
        # Verify contextual data
        assert result.data["id"] == "chunk-1"
        assert "chunk_context" in result.data
        assert "prev_chunk" in result.data
        assert "next_chunk" in result.data
        
        # Verify RPC call
        mock_supabase_client.rpc.assert_called_with('get_chunk_with_context', {
            'chunk_id_param': 'chunk-1',
            'include_adjacent': True
        })
    
    async def test_database_error_recovery(self, database_with_mock_client, mock_supabase_client):
        """Test database error handling and recovery."""
        db = database_with_mock_client
        
        # Mock connection failure
        mock_supabase_client.table.side_effect = Exception("Connection failed")
        
        # Test error handling
        with pytest.raises(Exception) as exc_info:
            db.client.table('documents')
        
        assert "Connection failed" in str(exc_info.value)
        
        # Test recovery - reset the side effect
        mock_table = Mock()
        mock_supabase_client.table.side_effect = None
        mock_supabase_client.table.return_value = mock_table
        
        # Should work after recovery
        result = db.client.table('documents')
        assert result == mock_table
    
    async def test_concurrent_database_operations(self, database_with_mock_client, mock_supabase_client):
        """Test concurrent database operations."""
        db = database_with_mock_client
        
        # Mock multiple operations
        mock_table = Mock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.execute.return_value = Mock(data=[])
        
        # Test concurrent operations
        async def fetch_documents():
            return db.client.table('documents').select('*').execute()
        
        async def fetch_sessions():
            return db.client.table('chat_sessions').select('*').execute()
        
        # Run concurrently
        doc_result, session_result = await asyncio.gather(
            fetch_documents(),
            fetch_sessions()
        )
        
        # Verify both operations completed
        assert doc_result.data == []
        assert session_result.data == []
        
        # Verify both table calls were made
        assert mock_supabase_client.table.call_count >= 2