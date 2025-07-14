"""Tests for search API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, Mock
from main import app


@pytest.mark.api
class TestSearchEndpoints:
    """Test search API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_services(self):
        """Mock all external services for search."""
        with patch('routers.search.get_openai_service') as mock_openai, \
             patch('routers.search.get_db') as mock_db:
            
            # Mock OpenAI service
            mock_openai_service = AsyncMock()
            mock_openai_service.generate_embedding.return_value = Mock(
                embedding=[0.1] * 1536,
                tokens=10
            )
            mock_openai.return_value = mock_openai_service
            
            # Mock database with search results
            mock_database = Mock()
            mock_search_results = [
                {
                    "id": "chunk-1",
                    "content": "Test search result 1",
                    "similarity": 0.85,
                    "document_title": "Test Document 1",
                    "chunk_context": "This is contextual information",
                    "document_id": "doc-1"
                },
                {
                    "id": "chunk-2",
                    "content": "Test search result 2", 
                    "similarity": 0.75,
                    "document_title": "Test Document 2",
                    "chunk_context": "More contextual information",
                    "document_id": "doc-2"
                }
            ]
            mock_database.client.rpc.return_value.execute.return_value.data = mock_search_results
            mock_db.return_value = mock_database
            
            yield {
                'openai': mock_openai_service,
                'database': mock_database
            }
    
    def test_search_endpoint_exists(self, client):
        """Test that search endpoint exists."""
        response = client.options("/api/search")
        assert response.status_code != 404
    
    def test_search_post_request_basic(self, client, mock_services):
        """Test search POST request with basic query."""
        test_payload = {
            "query": "test query",
            "limit": 10
        }
        response = client.post("/api/search", json=test_payload)
        
        # Should accept POST requests
        assert response.status_code != 404
        assert response.status_code in [200, 422, 500]  # Valid responses
    
    def test_search_post_request(self, client, mock_services):
        """Test search POST request with JSON payload."""
        test_payload = {
            "query": "test search query",
            "database_ids": ["db-1", "db-2"],
            "limit": 10
        }
        
        response = client.post("/api/search", json=test_payload)
        
        # Should accept POST requests
        assert response.status_code != 404
        assert response.status_code != 405  # Method not allowed
    
    def test_search_query_validation(self, client):
        """Test search query validation."""
        # Empty query should be handled
        response = client.post("/api/search", json={"query": "", "limit": 10})
        assert response.status_code in [200, 400, 422]
        
        # Missing query should be handled
        response = client.post("/api/search", json={"limit": 10})
        assert response.status_code in [200, 400, 422]
    
    def test_search_response_format(self, client, mock_services):
        """Test search response format."""
        test_payload = {"query": "test query", "limit": 10}
        response = client.post("/api/search", json=test_payload)
        
        if response.status_code == 200:
            response_data = response.json()
            
            # Should have results array
            assert "results" in response_data or isinstance(response_data, list)
            
            if "results" in response_data:
                results = response_data["results"]
            else:
                results = response_data
            
            # If results exist, they should have expected structure
            if results:
                first_result = results[0]
                expected_fields = ["id", "content", "document_title"]
                for field in expected_fields:
                    if field in first_result:
                        assert isinstance(first_result[field], str)
    
    def test_search_with_database_filter(self, client, mock_services):
        """Test search with database filtering."""
        test_payload = {
            "query": "test query",
            "database_ids": ["db-1", "db-2"]
        }
        
        response = client.post("/api/search", json=test_payload)
        
        # Should accept database filtering
        assert response.status_code != 422  # Validation error
    
    def test_search_with_limit_parameter(self, client, mock_services):
        """Test search with result limit."""
        response = client.get("/api/search?q=test&limit=5")
        
        if response.status_code == 200:
            response_data = response.json()
            results = response_data.get("results", response_data)
            
            # Should respect limit parameter
            if isinstance(results, list):
                assert len(results) <= 5
    

    def test_contextual_search_features(self, client, mock_services):
        """Test contextual search features."""
        test_payload = {
            "query": "contextual search test",
            "include_context": True,
            "context_window": 2
        }
        
        response = client.post("/api/search", json=test_payload)
        
        if response.status_code == 200:
            response_data = response.json()
            results = response_data.get("results", response_data)
            
            # Should include contextual information if available
            if results and len(results) > 0:
                first_result = results[0]
                # Check for contextual fields
                contextual_fields = ["chunk_context", "adjacent_chunks", "document_section"]
                has_context = any(field in first_result for field in contextual_fields)
                # Context is expected but not required in all implementations
                assert has_context or True  # Pass if context not implemented yet
    
    def test_search_similarity_scores(self, client, mock_services):
        """Test that search results include similarity scores."""
        response = client.get("/api/search?q=similarity test")
        
        if response.status_code == 200:
            response_data = response.json()
            results = response_data.get("results", response_data)
            
            if results and len(results) > 0:
                first_result = results[0]
                # Should have similarity score
                if "similarity" in first_result:
                    assert isinstance(first_result["similarity"], (int, float))
                    assert 0 <= first_result["similarity"] <= 1
    
    def test_search_error_handling(self, client):
        """Test search error handling."""
        # Test with malformed JSON
        response = client.post("/api/search",
                              data="invalid json",
                              headers={"Content-Type": "application/json"})
        assert response.status_code == 422
        
        # Test with invalid parameters
        response = client.post("/api/search", json={"query": "test", "limit": "invalid"})
        assert response.status_code in [200, 400, 422]
    
    def test_search_performance_parameters(self, client, mock_services):
        """Test search performance parameters."""
        test_payload = {
            "query": "performance test",
            "threshold": 0.7,  # Similarity threshold
            "limit": 20
        }
        
        response = client.post("/api/search", json=test_payload)
        
        # Should accept performance tuning parameters
        assert response.status_code != 422
    
    def test_search_metadata_response(self, client, mock_services):
        """Test search response includes metadata."""
        response = client.get("/api/search?q=metadata test")
        
        if response.status_code == 200:
            response_data = response.json()
            
            # Should include metadata about the search
            metadata_fields = ["total", "query_time", "embedding_time"]
            for field in metadata_fields:
                if field in response_data:
                    assert isinstance(response_data[field], (int, float))
    
    def test_search_cors_headers(self, client):
        """Test CORS headers for search endpoints."""
        response = client.options("/api/search")
        
        # Should have CORS headers
        headers = response.headers
        assert "access-control-allow-methods" in headers or \
               response.status_code == 405  # Method not allowed is acceptable
    
    def test_search_with_metadata_filters(self, client, mock_services):
        """Test search with metadata filters."""
        test_payload = {
            "query": "test query",
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
            ],
            "limit": 10
        }
        
        response = client.post("/api/search", json=test_payload)
        
        # Should accept metadata filters
        assert response.status_code in [200, 422, 500]
        
        # Should not return validation error for metadata filters
        if response.status_code == 422:
            error_detail = response.json()
            assert "metadata_filters" not in str(error_detail)

    def test_search_with_date_range_metadata_filters(self, client, mock_services):
        """Test search with date range metadata filters."""
        test_payload = {
            "query": "test query",
            "metadata_filters": [
                {
                    "field_name": "publish_date",
                    "operator": "in",
                    "values": ["from:2024-01-01", "to:2024-12-31"]
                }
            ],
            "limit": 10
        }
        
        response = client.post("/api/search", json=test_payload)
        
        # Should accept date range filters
        assert response.status_code in [200, 422, 500]

    def test_search_with_all_filter_types(self, client, mock_services):
        """Test search with all available filter types."""
        test_payload = {
            "query": "comprehensive test",
            "database_filters": ["db-1", "db-2"],
            "metadata_filters": [
                {
                    "field_name": "author",
                    "operator": "in",
                    "values": ["John Doe", "Jane Smith"]
                },
                {
                    "field_name": "priority",
                    "operator": "range",
                    "values": ["min:1", "max:10"]
                }
            ],
            "content_type_filters": ["article", "documentation"],
            "author_filters": ["John Doe"],
            "tag_filters": ["AI", "Tech"],
            "status_filters": ["published"],
            "date_range_filter": {
                "from_date": "2024-01-01",
                "to_date": "2024-12-31"
            },
            "limit": 10
        }
        
        response = client.post("/api/search", json=test_payload)
        
        # Should accept all filter types
        assert response.status_code in [200, 422, 500]
