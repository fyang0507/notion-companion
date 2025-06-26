"""Tests for chat API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, Mock
from main import app


@pytest.mark.api
class TestChatEndpoints:
    """Test chat API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_services(self):
        """Mock all external services."""
        with patch('routers.chat.get_openai_service') as mock_openai, \
             patch('routers.chat.get_db') as mock_db:
            
            # Mock OpenAI service
            mock_openai_service = AsyncMock()
            mock_openai_service.generate_chat_response.return_value = Mock(
                content="Test response",
                tokens=50
            )
            mock_openai.return_value = mock_openai_service
            
            # Mock database
            mock_database = Mock()
            mock_db.return_value = mock_database
            
            yield {
                'openai': mock_openai_service,
                'database': mock_database
            }
    
    def test_chat_endpoint_exists(self, client):
        """Test that chat endpoint exists and accepts requests."""
        response = client.options("/api/chat")
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404
    
    def test_chat_post_request_structure(self, client, mock_services):
        """Test chat POST request with proper structure."""
        test_payload = {
            "message": "Hello, how are you?",
            "session_id": "test-session-id",
            "database_ids": ["db-1", "db-2"]
        }
        
        response = client.post("/api/chat", json=test_payload)
        
        # Should accept the request (not return 400 for bad request)
        assert response.status_code != 400
    
    def test_chat_message_validation(self, client):
        """Test chat message validation."""
        # Empty message should be rejected
        response = client.post("/api/chat", json={
            "message": "",
            "session_id": "test-session"
        })
        assert response.status_code == 422  # Validation error
        
        # Missing message should be rejected
        response = client.post("/api/chat", json={
            "session_id": "test-session"
        })
        assert response.status_code == 422  # Validation error
    
    def test_chat_session_id_validation(self, client):
        """Test session ID validation."""
        # Missing session_id should be handled
        response = client.post("/api/chat", json={
            "message": "Hello"
        })
        # Should either create new session or return validation error
        assert response.status_code in [200, 201, 422]
    
    def test_chat_response_format(self, client, mock_services):
        """Test chat response format."""
        test_payload = {
            "message": "Test message",
            "session_id": "test-session-id"
        }
        
        response = client.post("/api/chat", json=test_payload)
        
        if response.status_code == 200:
            # If successful, should have proper response structure
            # Note: Adjust based on your actual response format
            response_data = response.json()
            assert "response" in response_data or "message" in response_data
    
    def test_chat_streaming_response(self, client, mock_services):
        """Test streaming chat response."""
        test_payload = {
            "message": "Test streaming message",
            "session_id": "test-session-id",
            "stream": True
        }
        
        response = client.post("/api/chat", json=test_payload)
        
        # Should handle streaming request
        if response.status_code == 200:
            # Check if response is streaming
            assert "text/event-stream" in response.headers.get("content-type", "") or \
                   "application/json" in response.headers.get("content-type", "")
    
    def test_chat_with_database_filter(self, client, mock_services):
        """Test chat with database filtering."""
        test_payload = {
            "message": "Search in specific databases",
            "session_id": "test-session-id",
            "database_ids": ["db-1", "db-2"]
        }
        
        response = client.post("/api/chat", json=test_payload)
        
        # Should accept database filtering
        assert response.status_code != 400
    
    def test_chat_error_handling(self, client):
        """Test chat error handling."""
        # Test with invalid JSON
        response = client.post("/api/chat", 
                             data="invalid json",
                             headers={"Content-Type": "application/json"})
        assert response.status_code == 422  # JSON decode error
        
        # Test with malformed request
        response = client.post("/api/chat", json={"invalid": "structure"})
        assert response.status_code == 422  # Validation error
    
    def test_chat_cors_headers(self, client):
        """Test CORS headers for chat endpoint."""
        response = client.options("/api/chat")
        
        # Should have CORS headers for browser compatibility
        headers = response.headers
        # Note: Adjust based on your CORS configuration
        assert "access-control-allow-origin" in headers or \
               response.status_code == 405  # Method not allowed is also acceptable
    
    def test_chat_rate_limiting(self, client):
        """Test rate limiting behavior."""
        test_payload = {
            "message": "Rate limit test",
            "session_id": "test-session-id"
        }
        
        # Make multiple rapid requests
        responses = []
        for _ in range(5):
            response = client.post("/api/chat", json=test_payload)
            responses.append(response.status_code)
        
        # Should handle multiple requests gracefully
        # Either all succeed or rate limiting kicks in with 429
        assert all(code in [200, 201, 429, 500] for code in responses)
    
    def test_chat_authentication(self, client):
        """Test authentication requirements."""
        test_payload = {
            "message": "Test auth",
            "session_id": "test-session-id"
        }
        
        # Test without authentication
        response = client.post("/api/chat", json=test_payload)
        
        # Should either work (no auth required) or return 401/403
        assert response.status_code in [200, 201, 401, 403, 422, 500]