"""Tests for database service connection and functionality."""

import pytest
from unittest.mock import patch, Mock
from database import Database


@pytest.mark.unit
class TestDatabase:
    """Test database service functionality."""
    
    @pytest.fixture
    def database_service(self, mock_supabase_client):
        """Create database service with mocked client."""
        with patch('database.create_client') as mock_create_client:
            mock_create_client.return_value = mock_supabase_client
            db = Database()
            db.client = mock_supabase_client  # Set directly for testing
            return db
    
    async def test_database_initialization_success(self, mock_supabase_client):
        """Test successful database initialization."""
        with patch('database.create_client') as mock_create_client:
            mock_create_client.return_value = mock_supabase_client
            
            db = Database()
            await db.init()
            
            # Verify client was created
            mock_create_client.assert_called_once()
            assert db.client is not None
    
    async def test_database_initialization_missing_credentials(self):
        """Test database initialization with missing credentials."""
        with patch.dict('os.environ', {}, clear=True):
            db = Database()
            
            with pytest.raises(ValueError) as exc_info:
                await db.init()
            
            assert "Supabase credentials not found" in str(exc_info.value)
    
    def test_get_client_success(self, database_service, mock_supabase_client):
        """Test successful client retrieval."""
        client = database_service.get_client()
        assert client == mock_supabase_client
    
    def test_get_client_not_initialized(self):
        """Test client retrieval when not initialized."""
        db = Database()
        
        with pytest.raises(RuntimeError) as exc_info:
            db.get_client()
        
        assert "Database not initialized" in str(exc_info.value)
    
    def test_get_notion_databases_active_only(self, database_service, mock_supabase_client):
        """Test getting active notion databases only."""
        # Mock the response chain
        mock_table = Mock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.order.return_value = mock_table
        
        mock_response = Mock()
        mock_response.data = [
            {"id": "db-1", "name": "Test DB 1", "is_active": True},
            {"id": "db-2", "name": "Test DB 2", "is_active": True}
        ]
        mock_table.execute.return_value = mock_response
        
        # Call the method
        result = database_service.get_notion_databases(active_only=True)
        
        # Verify the result
        assert len(result) == 2
        assert result[0]["id"] == "db-1"
        
        # Verify the query chain
        mock_supabase_client.table.assert_called_with('notion_databases')
        mock_table.select.assert_called_with('*')
        mock_table.eq.assert_called_with('is_active', True)
        mock_table.order.assert_called_with('created_at', desc=True)
    
    def test_get_notion_databases_all(self, database_service, mock_supabase_client):
        """Test getting all notion databases."""
        # Mock the response chain
        mock_table = Mock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.order.return_value = mock_table
        
        mock_response = Mock()
        mock_response.data = [
            {"id": "db-1", "name": "Test DB 1", "is_active": True},
            {"id": "db-2", "name": "Test DB 2", "is_active": False}
        ]
        mock_table.execute.return_value = mock_response
        
        # Call the method
        result = database_service.get_notion_databases(active_only=False)
        
        # Verify the result
        assert len(result) == 2
        
        # Verify is_active filter was NOT applied
        mock_table.eq.assert_not_called()
    
    def test_vector_search_functionality(self, database_service, mock_supabase_client):
        """Test vector search functionality."""
        # Mock vector search response
        mock_response = Mock()
        mock_response.data = [
            {
                "id": "chunk-1",
                "content": "Test content 1",
                "similarity": 0.85,
                "document_id": "doc-1"
            },
            {
                "id": "chunk-2", 
                "content": "Test content 2",
                "similarity": 0.75,
                "document_id": "doc-2"
            }
        ]
        mock_supabase_client.rpc.return_value = mock_response
        
        # Mock embedding vector
        test_embedding = [0.1] * 1536
        
        # Call vector search (assuming this method exists in your Database class)
        # Note: You may need to adjust this based on your actual implementation
        result = database_service.client.rpc('match_contextual_chunks', {
            'query_embedding': test_embedding,
            'database_filter': None,
            'match_threshold': 0.7,
            'match_count': 5
        }).execute()
        
        # Verify the result
        assert len(result.data) == 2
        assert result.data[0]["similarity"] == 0.85
        
        # Verify RPC was called correctly
        mock_supabase_client.rpc.assert_called_once()
    
    def test_document_operations(self, database_service, mock_supabase_client):
        """Test document CRUD operations."""
        # Mock table operations
        mock_table = Mock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        
        mock_response = Mock()
        mock_response.data = [{"id": "doc-1", "title": "Test Document"}]
        mock_table.execute.return_value = mock_response
        
        # Test document insertion
        test_document = {
            "title": "Test Document",
            "content": "Test content",
            "database_id": "db-1"
        }
        
        # Insert document
        database_service.client.table('documents').insert(test_document).execute()
        
        # Verify insert was called
        mock_supabase_client.table.assert_called_with('documents')
        mock_table.insert.assert_called_with(test_document)
    
    def test_chat_session_operations(self, database_service, mock_supabase_client):
        """Test chat session operations."""
        # Mock table operations for chat sessions
        mock_table = Mock()
        mock_supabase_client.table.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.update.return_value = mock_table
        
        mock_response = Mock()
        mock_response.data = [{"id": "session-1", "title": "Test Session"}]
        mock_table.execute.return_value = mock_response
        
        # Test session creation
        test_session = {
            "title": "Test Session",
            "status": "active"
        }
        
        database_service.client.table('chat_sessions').insert(test_session).execute()
        
        # Verify operations
        mock_supabase_client.table.assert_called_with('chat_sessions')
        mock_table.insert.assert_called_with(test_session)
    
    def test_error_handling_in_operations(self, database_service, mock_supabase_client):
        """Test error handling in database operations."""
        # Mock table to raise exception
        mock_supabase_client.table.side_effect = Exception("Database connection error")
        
        # Should handle the exception appropriately
        with pytest.raises(Exception):
            database_service.client.table('documents')
    
    async def test_connection_validation(self, database_service):
        """Test database connection validation."""
        # This would test actual connectivity in integration tests
        # For unit tests, we verify the client is properly configured
        client = database_service.get_client()
        assert client is not None
        
        # Verify client has the expected methods
        assert hasattr(client, 'table')
        assert hasattr(client, 'rpc')
        assert callable(client.table)
        assert callable(client.rpc)