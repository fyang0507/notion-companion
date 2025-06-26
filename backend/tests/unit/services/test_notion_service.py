"""Tests for Notion service connection and functionality."""

import pytest
from unittest.mock import patch, Mock
from services.notion_service import NotionService


@pytest.mark.unit
class TestNotionService:
    """Test Notion service functionality."""
    
    @pytest.fixture
    def notion_service(self, mock_notion_client):
        """Create Notion service with mocked client."""
        with patch('services.notion_service.Client') as mock_client_class:
            mock_client_class.return_value = mock_notion_client
            service = NotionService(access_token="test-token")
            return service
    
    async def test_service_initialization(self):
        """Test Notion service initialization."""
        with patch('services.notion_service.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            service = NotionService(access_token="test-token")
            
            # Verify client was created with correct token
            mock_client_class.assert_called_once_with(auth="test-token")
            assert service.client == mock_client
    
    async def test_search_pages_success(self, notion_service, mock_notion_client):
        """Test successful page search."""
        # Mock the search response
        mock_response = {
            "results": [
                {
                    "id": "page-1",
                    "properties": {
                        "Name": {"title": [{"text": {"content": "Test Page 1"}}]}
                    }
                },
                {
                    "id": "page-2", 
                    "properties": {
                        "Name": {"title": [{"text": {"content": "Test Page 2"}}]}
                    }
                }
            ],
            "has_more": False
        }
        mock_notion_client.search.return_value = mock_response
        
        # Call the service
        result = await notion_service.search_pages()
        
        # Verify the result
        assert len(result) == 2
        assert result[0]["id"] == "page-1"
        assert result[1]["id"] == "page-2"
        
        # Verify the client was called correctly
        mock_notion_client.search.assert_called_once()
        call_args = mock_notion_client.search.call_args
        assert call_args.kwargs["filter"]["property"] == "object"
        assert call_args.kwargs["filter"]["value"] == "page"
    
    async def test_search_pages_with_query(self, notion_service, mock_notion_client):
        """Test page search with specific query."""
        mock_response = {
            "results": [{"id": "page-1"}],
            "has_more": False
        }
        mock_notion_client.search.return_value = mock_response
        
        # Call the service with query
        result = await notion_service.search_pages(query="test query")
        
        # Verify the query was passed
        mock_notion_client.search.assert_called_once()
        call_args = mock_notion_client.search.call_args
        assert call_args.kwargs["query"] == "test query"
    
    async def test_search_pages_with_pagination(self, notion_service, mock_notion_client):
        """Test page search handles pagination."""
        # First response with more pages
        first_response = {
            "results": [{"id": "page-1"}],
            "has_more": True,
            "next_cursor": "cursor-123"
        }
        # Second response (final)
        second_response = {
            "results": [{"id": "page-2"}],
            "has_more": False
        }
        
        mock_notion_client.search.side_effect = [first_response, second_response]
        
        # Call the service
        result = await notion_service.search_pages()
        
        # Verify pagination was handled
        assert len(result) == 2
        assert mock_notion_client.search.call_count == 2
        
        # Verify second call used cursor
        second_call_args = mock_notion_client.search.call_args
        assert second_call_args.kwargs["start_cursor"] == "cursor-123"
    
    async def test_search_pages_error_handling(self, notion_service, mock_notion_client):
        """Test error handling in page search."""
        # Mock client to raise exception
        mock_notion_client.search.side_effect = Exception("API Error")
        
        # Call should raise exception
        with pytest.raises(Exception) as exc_info:
            await notion_service.search_pages()
        
        assert "Failed to search Notion pages" in str(exc_info.value)
    
    async def test_get_page_success(self, notion_service, mock_notion_client):
        """Test successful page retrieval."""
        test_page_id = "test-page-id"
        mock_response = {
            "id": test_page_id,
            "properties": {
                "Name": {"title": [{"text": {"content": "Test Page"}}]}
            }
        }
        mock_notion_client.pages.retrieve.return_value = mock_response
        
        # Call the service
        result = await notion_service.get_page(test_page_id)
        
        # Verify the result
        assert result["id"] == test_page_id
        assert result["properties"]["Name"]["title"][0]["text"]["content"] == "Test Page"
        
        # Verify the client was called correctly
        mock_notion_client.pages.retrieve.assert_called_once_with(page_id=test_page_id)
    
    async def test_get_page_error_handling(self, notion_service, mock_notion_client):
        """Test error handling in page retrieval."""
        test_page_id = "invalid-page-id"
        
        # Mock client to raise exception
        mock_notion_client.pages.retrieve.side_effect = Exception("Page not found")
        
        # Call should raise exception
        with pytest.raises(Exception) as exc_info:
            await notion_service.get_page(test_page_id)
        
        assert f"Failed to retrieve page {test_page_id}" in str(exc_info.value)
    
    async def test_search_pages_pagination_safety_limit(self, notion_service, mock_notion_client):
        """Test pagination safety limit prevents infinite loops."""
        # Create responses that would exceed 1000 if not limited
        responses = []
        # Create 15 pages of 100 results each (would be 1500 total)
        for i in range(15):
            is_last = i == 14
            response = {
                "results": [{"id": f"page-{i * 100 + j}"} for j in range(100)],
                "has_more": not is_last,
                "next_cursor": f"cursor-{i}" if not is_last else None
            }
            responses.append(response)
        
        mock_notion_client.search.side_effect = responses
        
        # Call the service
        result = await notion_service.search_pages()
        
        # Should stop at safety limit (1000 pages)
        assert len(result) <= 1000
        # Should have made exactly 10 calls to reach the 1000 limit
        assert mock_notion_client.search.call_count == 10
    
    async def test_search_pages_page_size_parameter(self, notion_service, mock_notion_client):
        """Test page size parameter is passed correctly."""
        mock_response = {"results": [], "has_more": False}
        mock_notion_client.search.return_value = mock_response
        
        # Call with custom page size
        await notion_service.search_pages(page_size=50)
        
        # Verify page size was passed
        mock_notion_client.search.assert_called_once()
        call_args = mock_notion_client.search.call_args
        assert call_args.kwargs["page_size"] == 50