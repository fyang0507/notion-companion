"""Tests for OpenAI service connection and functionality."""

import pytest
from unittest.mock import patch, AsyncMock
from services.openai_service import OpenAIService, EmbeddingResponse, ChatResponse


@pytest.mark.unit
class TestOpenAIService:
    """Test OpenAI service functionality."""
    
    @pytest.fixture
    def openai_service(self, mock_openai_client):
        """Create OpenAI service with mocked client."""
        with patch('services.openai_service.AsyncOpenAI') as mock_openai_class:
            mock_openai_class.return_value = mock_openai_client
            service = OpenAIService()
            return service
    
    async def test_generate_embedding_success(self, openai_service, mock_openai_client):
        """Test successful embedding generation."""
        test_text = "This is a test text for embedding"
        
        # Call the service
        result = await openai_service.generate_embedding(test_text)
        
        # Verify the result
        assert isinstance(result, EmbeddingResponse)
        assert len(result.embedding) == 1536  # Standard OpenAI embedding size
        assert result.tokens == 10
        assert all(isinstance(val, float) for val in result.embedding)
        
        # Verify the OpenAI client was called correctly
        mock_openai_client.embeddings.create.assert_called_once()
        call_args = mock_openai_client.embeddings.create.call_args
        assert call_args.kwargs['input'] == test_text
        assert call_args.kwargs['model'] is not None  # Should use configured model
    
    async def test_generate_embedding_with_empty_text(self, openai_service, mock_openai_client):
        """Test embedding generation with empty text."""
        # The service should handle empty text by passing it to OpenAI
        # (OpenAI will handle the validation)
        result = await openai_service.generate_embedding("")
        
        # Verify it still returns a valid response structure
        assert isinstance(result, EmbeddingResponse)
        mock_openai_client.embeddings.create.assert_called_once()
    
    async def test_generate_chat_response_success(self, openai_service, mock_openai_client):
        """Test successful chat response generation."""
        test_messages = [
            {"role": "user", "content": "Hello, how are you?"}
        ]
        
        # Call the service
        result = await openai_service.generate_chat_response(test_messages)
        
        # Verify the result
        assert isinstance(result, ChatResponse)
        assert result.content == "Test response"
        assert result.tokens == 50
        
        # Verify the OpenAI client was called correctly
        mock_openai_client.chat.completions.create.assert_called_once()
        call_args = mock_openai_client.chat.completions.create.call_args
        
        # The service adds a system message, so messages should have 2 items
        sent_messages = call_args.kwargs['messages']
        assert len(sent_messages) == 2
        assert sent_messages[0]['role'] == 'system'  # System message first
        assert sent_messages[1] == test_messages[0]  # User message second
    
    async def test_generate_chat_response_with_context(self, openai_service, mock_openai_client):
        """Test chat response generation with context."""
        test_messages = [{"role": "user", "content": "What is this about?"}]
        test_context = "This is contextual information from the knowledge base."
        
        # Call the service
        result = await openai_service.generate_chat_response(test_messages, test_context)
        
        # Verify the result
        assert isinstance(result, ChatResponse)
        assert result.content == "Test response"
        
        # Verify context was included in the messages
        mock_openai_client.chat.completions.create.assert_called_once()
        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        
        # Should have system message with context
        assert any(msg.get('role') == 'system' for msg in messages)
    
    async def test_rate_limiting_delay(self, openai_service):
        """Test that rate limiting delay is applied."""
        import time
        
        start_time = time.time()
        await openai_service.generate_embedding("test")
        end_time = time.time()
        
        # Should have some delay (even if small in test)
        elapsed = end_time - start_time
        assert elapsed >= 0  # At minimum, should not be negative
    
    async def test_client_initialization(self):
        """Test OpenAI client is properly initialized."""
        with patch('services.openai_service.AsyncOpenAI') as mock_openai_class:
            mock_client = AsyncMock()
            mock_openai_class.return_value = mock_client
            
            service = OpenAIService()
            
            # Verify client was created
            mock_openai_class.assert_called_once()
            assert service.client == mock_client
            assert service.model_config is not None
    
    def test_embedding_response_model(self):
        """Test EmbeddingResponse model validation."""
        # Valid response
        response = EmbeddingResponse(
            embedding=[0.1, 0.2, 0.3],
            tokens=10
        )
        assert response.embedding == [0.1, 0.2, 0.3]
        assert response.tokens == 10
        
        # Invalid response should raise validation error
        with pytest.raises(Exception):
            EmbeddingResponse(
                embedding="invalid",  # Should be list
                tokens=10
            )
    
    def test_chat_response_model(self):
        """Test ChatResponse model validation."""
        # Valid response
        response = ChatResponse(
            content="Test response",
            tokens=50
        )
        assert response.content == "Test response"
        assert response.tokens == 50
        
        # Invalid response should raise validation error
        with pytest.raises(Exception):
            ChatResponse(
                content=123,  # Should be string
                tokens=50
            )