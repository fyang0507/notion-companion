"""Shared test fixtures and configuration."""

import os
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
from typing import Dict, Any, Generator

# Test environment setup
os.environ["TESTING"] = "true"
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["NOTION_ACCESS_TOKEN"] = "test-token"
os.environ["NEXT_PUBLIC_SUPABASE_URL"] = "https://test.supabase.co"
os.environ["NEXT_PUBLIC_SUPABASE_ANON_KEY"] = "test-anon-key"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-service-key"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    mock_client = AsyncMock()
    
    # Mock embedding response
    mock_embedding_response = Mock()
    mock_embedding_response.data = [
        Mock(embedding=[0.1] * 1536)
    ]
    mock_embedding_response.usage = Mock(total_tokens=10)
    mock_client.embeddings.create.return_value = mock_embedding_response
    
    # Mock chat completion response
    mock_chat_response = Mock()
    mock_chat_response.choices = [
        Mock(message=Mock(content="Test response"))
    ]
    mock_chat_response.usage = Mock(total_tokens=50)
    mock_client.chat.completions.create.return_value = mock_chat_response
    
    return mock_client


@pytest.fixture
def mock_notion_client():
    """Mock Notion client for testing."""
    mock_client = Mock()
    
    # Mock search response
    mock_client.search.return_value = {
        "results": [
            {
                "id": "test-page-id",
                "properties": {
                    "Name": {"title": [{"text": {"content": "Test Page"}}]},
                    "Content": {"rich_text": [{"text": {"content": "Test content"}}]}
                },
                "last_edited_time": "2023-01-01T00:00:00.000Z"
            }
        ],
        "has_more": False
    }
    
    # Mock database query response
    mock_client.databases.query.return_value = {
        "results": [
            {
                "id": "test-page-id",
                "properties": {
                    "Name": {"title": [{"text": {"content": "Test Page"}}]},
                    "Content": {"rich_text": [{"text": {"content": "Test content"}}]}
                },
                "last_edited_time": "2023-01-01T00:00:00.000Z"
            }
        ],
        "has_more": False
    }
    
    # Mock page retrieval
    mock_client.pages.retrieve.return_value = {
        "id": "test-page-id",
        "properties": {
            "Name": {"title": [{"text": {"content": "Test Page"}}]}
        }
    }
    
    return mock_client


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for testing."""
    mock_client = Mock()
    
    # Mock table operations
    mock_table = Mock()
    mock_client.table.return_value = mock_table
    
    # Mock successful responses
    mock_response = Mock()
    mock_response.data = []
    mock_response.count = 0
    mock_response.execute.return_value = mock_response
    
    mock_table.select.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.delete.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = mock_response
    
    # Mock RPC calls
    mock_client.rpc.return_value = mock_response
    
    return mock_client


@pytest.fixture
def sample_documents() -> Dict[str, Any]:
    """Sample document data for testing."""
    return {
        "test_document": {
            "id": "test-doc-id",
            "title": "Test Document",
            "content": "This is test content for our document.",
            "database_id": "test-db-id",
            "page_id": "test-page-id",
            "last_edited": "2023-01-01T00:00:00.000Z"
        },
        "test_chunks": [
            {
                "id": "chunk-1",
                "content": "First chunk of content",
                "chunk_index": 0,
                "document_id": "test-doc-id"
            },
            {
                "id": "chunk-2", 
                "content": "Second chunk of content",
                "chunk_index": 1,
                "document_id": "test-doc-id"
            }
        ]
    }


@pytest.fixture
def sample_chat_session() -> Dict[str, Any]:
    """Sample chat session data for testing."""
    return {
        "id": "test-session-id",
        "title": "Test Chat Session",
        "status": "active",
        "created_at": "2023-01-01T00:00:00.000Z",
        "updated_at": "2023-01-01T00:00:00.000Z"
    }


@pytest.fixture
def sample_embedding() -> list[float]:
    """Sample embedding vector for testing."""
    return [0.1] * 1536  # Standard OpenAI embedding dimension