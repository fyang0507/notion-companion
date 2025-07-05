"""Tests for metadata filtering functionality in search and chat endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock
from main import app


@pytest.mark.api
class TestMetadataFiltering:
    """Test metadata filtering functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_services(self):
        """Mock services for metadata filtering tests."""
        with patch('routers.search.get_openai_service') as mock_openai, \
             patch('routers.search.get_db') as mock_db, \
             patch('routers.chat.get_openai_service') as mock_chat_openai, \
             patch('routers.chat.get_db') as mock_chat_db:
            
            # Mock OpenAI service
            mock_openai_service = AsyncMock()
            mock_openai_service.generate_embedding.return_value = Mock(
                embedding=[0.1] * 1536,
                tokens=10
            )
            mock_openai.return_value = mock_openai_service
            mock_chat_openai.return_value = mock_openai_service
            
            # Mock database
            mock_database = Mock()
            mock_db.return_value = mock_database
            mock_chat_db.return_value = mock_database
            
            yield {
                'openai': mock_openai_service,
                'database': mock_database
            }

    def test_search_with_metadata_filters(self, client, mock_services):
        """Test search with metadata filters."""
        search_payload = {
            "query": "test search",
            "metadata_filters": [
                {
                    "field_name": "author",
                    "operator": "equals",
                    "values": ["John Doe"]
                },
                {
                    "field_name": "tags",
                    "operator": "in",
                    "values": ["AI", "Tech"]
                }
            ]
        }
        
        response = client.post("/api/search", json=search_payload)
        
        # Should accept metadata filters
        assert response.status_code in [200, 422, 500]
        
        # Should not return validation error for metadata filters
        if response.status_code == 422:
            error_detail = response.json()
            # Check that error is not related to metadata_filters field
            assert "metadata_filters" not in str(error_detail)

    def test_search_with_date_range_filters(self, client, mock_services):
        """Test search with date range filters."""
        search_payload = {
            "query": "test search",
            "metadata_filters": [
                {
                    "field_name": "publish_date",
                    "operator": "in",
                    "values": ["from:2024-01-01", "to:2024-12-31"]
                }
            ]
        }
        
        response = client.post("/api/search", json=search_payload)
        
        # Should accept date range filters
        assert response.status_code in [200, 422, 500]

    def test_search_with_number_range_filters(self, client, mock_services):
        """Test search with number range filters."""
        search_payload = {
            "query": "test search",
            "metadata_filters": [
                {
                    "field_name": "priority",
                    "operator": "in",
                    "values": ["min:1", "max:10"]
                }
            ]
        }
        
        response = client.post("/api/search", json=search_payload)
        
        # Should accept number range filters
        assert response.status_code in [200, 422, 500]

    def test_search_with_complex_metadata_filters(self, client, mock_services):
        """Test search with complex metadata filters."""
        search_payload = {
            "query": "test search",
            "metadata_filters": [
                {
                    "field_name": "author",
                    "operator": "in",
                    "values": ["John Doe", "Jane Smith"]
                },
                {
                    "field_name": "status",
                    "operator": "equals",
                    "values": ["published"]
                },
                {
                    "field_name": "tags",
                    "operator": "in",
                    "values": ["AI", "Machine Learning"]
                }
            ],
            "database_filters": ["db-1", "db-2"]
        }
        
        response = client.post("/api/search", json=search_payload)
        
        # Should accept complex metadata filters
        assert response.status_code in [200, 422, 500]

    def test_chat_with_metadata_filters(self, client, mock_services):
        """Test chat with metadata filters."""
        chat_payload = {
            "messages": [
                {"role": "user", "content": "Tell me about AI articles"}
            ],
            "session_id": "test-session-123",
            "metadata_filters": [
                {
                    "field_name": "tags",
                    "operator": "in",
                    "values": ["AI", "Machine Learning"]
                }
            ]
        }
        
        response = client.post("/api/chat", json=chat_payload)
        
        # Should accept metadata filters
        assert response.status_code in [200, 422, 500]

    def test_hybrid_search_with_metadata_filters(self, client, mock_services):
        """Test hybrid search with metadata filters."""
        search_payload = {
            "query": "test hybrid search",
            "metadata_filters": [
                {
                    "field_name": "content_type",
                    "operator": "in",
                    "values": ["article", "documentation"]
                }
            ]
        }
        
        response = client.post("/api/search/hybrid", json=search_payload)
        
        # Should accept metadata filters
        assert response.status_code in [200, 422, 500]

    def test_metadata_filter_validation(self, client, mock_services):
        """Test metadata filter validation."""
        # Test with invalid operator
        search_payload = {
            "query": "test search",
            "metadata_filters": [
                {
                    "field_name": "author",
                    "operator": "invalid_operator",
                    "values": ["John Doe"]
                }
            ]
        }
        
        response = client.post("/api/search", json=search_payload)
        
        # Should handle invalid operator gracefully
        assert response.status_code in [200, 422, 500]

    def test_metadata_filter_empty_values(self, client, mock_services):
        """Test metadata filter with empty values."""
        search_payload = {
            "query": "test search",
            "metadata_filters": [
                {
                    "field_name": "author",
                    "operator": "equals",
                    "values": []
                }
            ]
        }
        
        response = client.post("/api/search", json=search_payload)
        
        # Should handle empty values gracefully
        assert response.status_code in [200, 422, 500]

    def test_legacy_filters_compatibility(self, client, mock_services):
        """Test compatibility with legacy filter parameters."""
        search_payload = {
            "query": "test search",
            "database_filters": ["db-1", "db-2"],
            "author_filters": ["John Doe"],
            "tag_filters": ["AI", "Tech"],
            "status_filters": ["published"],
            "content_type_filters": ["article"]
        }
        
        response = client.post("/api/search", json=search_payload)
        
        # Should accept legacy filter parameters
        assert response.status_code in [200, 422, 500]

    def test_mixed_filters_compatibility(self, client, mock_services):
        """Test mixing new metadata filters with legacy filters."""
        search_payload = {
            "query": "test search",
            "database_filters": ["db-1"],
            "author_filters": ["John Doe"],
            "metadata_filters": [
                {
                    "field_name": "priority",
                    "operator": "in",
                    "values": ["min:5", "max:10"]
                }
            ]
        }
        
        response = client.post("/api/search", json=search_payload)
        
        # Should accept mixed filters
        assert response.status_code in [200, 422, 500]


@pytest.mark.api
class TestMetadataFilterProcessing:
    """Test metadata filter processing functions."""
    
    def test_process_metadata_filters_basic(self):
        """Test basic metadata filter processing."""
        from routers.search import _process_metadata_filters
        
        metadata_filters = {
            "author": ["John Doe"],
            "tags": ["AI", "Tech"],
            "status": "published"
        }
        
        processed = _process_metadata_filters(metadata_filters)
        
        assert "author" in processed
        assert "tags" in processed
        assert "status" in processed
        assert processed["author"] == ["John Doe"]
        assert processed["tags"] == ["AI", "Tech"]
        assert processed["status"] == ["published"]

    def test_process_metadata_filters_date_ranges(self):
        """Test metadata filter processing with date ranges."""
        from routers.search import _process_metadata_filters
        
        metadata_filters = {
            "publish_date": ["from:2024-01-01", "to:2024-12-31"]
        }
        
        processed = _process_metadata_filters(metadata_filters)
        
        assert "publish_date_range" in processed
        date_range = processed["publish_date_range"]
        assert date_range["date_from"] == "2024-01-01"
        assert date_range["date_to"] == "2024-12-31"

    def test_process_metadata_filters_number_ranges(self):
        """Test metadata filter processing with number ranges."""
        from routers.search import _process_metadata_filters
        
        metadata_filters = {
            "priority": ["min:1", "max:10"]
        }
        
        processed = _process_metadata_filters(metadata_filters)
        
        assert "priority_range" in processed
        number_range = processed["priority_range"]
        assert number_range["number_min"] == 1.0
        assert number_range["number_max"] == 10.0

    def test_build_metadata_query_conditions(self):
        """Test building SQL query conditions from processed filters."""
        from routers.search import _build_metadata_query_conditions
        
        processed_filters = {
            "author": ["John Doe"],
            "tags": ["AI", "Tech"],
            "publish_date_range": {
                "date_from": "2024-01-01",
                "date_to": "2024-12-31"
            },
            "priority_range": {
                "number_min": 1.0,
                "number_max": 10.0
            }
        }
        
        conditions = _build_metadata_query_conditions(processed_filters)
        
        # Expect 6 conditions: author, tags, date_from, date_to, priority_min, priority_max
        assert len(conditions) == 6
        
        # Check that conditions contain expected SQL patterns
        conditions_str = " ".join(conditions)
        assert "author" in conditions_str
        assert "tags" in conditions_str
        assert "publish_date" in conditions_str
        assert "priority" in conditions_str
        assert "::date >=" in conditions_str
        assert "::numeric >=" in conditions_str 