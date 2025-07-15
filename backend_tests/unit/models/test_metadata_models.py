"""Tests for metadata filtering models."""

import pytest
from datetime import date
from pydantic import ValidationError
from models import MetadataFilter, SearchRequest, ChatRequest, DateRangeFilter


@pytest.mark.unit
class TestMetadataFilterModel:
    """Test MetadataFilter model."""
    
    def test_metadata_filter_creation(self):
        """Test basic MetadataFilter creation."""
        filter_obj = MetadataFilter(
            field_name="author",
            operator="equals",
            values=["John Doe"]
        )
        
        assert filter_obj.field_name == "author"
        assert filter_obj.operator == "equals"
        assert filter_obj.values == ["John Doe"]
        assert filter_obj.field_type is None

    def test_metadata_filter_with_field_type(self):
        """Test MetadataFilter with field type."""
        filter_obj = MetadataFilter(
            field_name="priority",
            operator="range",
            values=["1", "10"],
            field_type="number"
        )
        
        assert filter_obj.field_name == "priority"
        assert filter_obj.operator == "range"
        assert filter_obj.values == ["1", "10"]
        assert filter_obj.field_type == "number"

    def test_metadata_filter_validation_required_fields(self):
        """Test MetadataFilter validation for required fields."""
        # Missing field_name
        with pytest.raises(ValidationError) as exc_info:
            MetadataFilter(
                operator="equals",
                values=["test"]
            )
        assert "field_name" in str(exc_info.value)
        
        # Missing operator
        with pytest.raises(ValidationError) as exc_info:
            MetadataFilter(
                field_name="author",
                values=["test"]
            )
        assert "operator" in str(exc_info.value)
        
        # Missing values
        with pytest.raises(ValidationError) as exc_info:
            MetadataFilter(
                field_name="author",
                operator="equals"
            )
        assert "values" in str(exc_info.value)

    def test_metadata_filter_empty_values(self):
        """Test MetadataFilter with empty values."""
        filter_obj = MetadataFilter(
            field_name="author",
            operator="equals",
            values=[]
        )
        
        assert filter_obj.values == []

    def test_metadata_filter_mixed_value_types(self):
        """Test MetadataFilter with mixed value types."""
        filter_obj = MetadataFilter(
            field_name="mixed_field",
            operator="in",
            values=["string", 123, True]
        )
        
        assert filter_obj.values == ["string", 123, True]

    def test_metadata_filter_serialization(self):
        """Test MetadataFilter serialization."""
        filter_obj = MetadataFilter(
            field_name="author",
            operator="equals",
            values=["John Doe"],
            field_type="text"
        )
        
        data = filter_obj.model_dump()
        expected = {
            "field_name": "author",
            "operator": "equals",
            "values": ["John Doe"],
            "field_type": "text"
        }
        
        assert data == expected

    def test_metadata_filter_deserialization(self):
        """Test MetadataFilter deserialization."""
        data = {
            "field_name": "tags",
            "operator": "in",
            "values": ["AI", "Tech"]
        }
        
        filter_obj = MetadataFilter(**data)
        
        assert filter_obj.field_name == "tags"
        assert filter_obj.operator == "in"
        assert filter_obj.values == ["AI", "Tech"]


@pytest.mark.unit
class TestSearchRequestWithMetadataFilters:
    """Test SearchRequest with metadata filters."""
    
    def test_search_request_with_metadata_filters(self):
        """Test SearchRequest with metadata filters."""
        request = SearchRequest(
            query="test search",
            metadata_filters=[
                MetadataFilter(
                    field_name="author",
                    operator="equals",
                    values=["John Doe"]
                ),
                MetadataFilter(
                    field_name="tags",
                    operator="in",
                    values=["AI", "Tech"]
                )
            ]
        )
        
        assert request.query == "test search"
        assert len(request.metadata_filters) == 2
        assert request.metadata_filters[0].field_name == "author"
        assert request.metadata_filters[1].field_name == "tags"

    def test_search_request_with_all_filter_types(self):
        """Test SearchRequest with all filter types."""
        request = SearchRequest(
            query="comprehensive search",
            database_filters=["db-1", "db-2"],
            metadata_filters=[
                MetadataFilter(
                    field_name="custom_field",
                    operator="equals",
                    values=["custom_value"]
                )
            ],
            content_type_filters=["article", "documentation"],
            date_range_filter=DateRangeFilter(
                from_date="2024-01-01",
                to_date="2024-12-31"
            )
        )
        
        assert request.query == "comprehensive search"
        assert request.database_filters == ["db-1", "db-2"]
        assert len(request.metadata_filters) == 1
        assert request.content_type_filters == ["article", "documentation"]
        assert request.date_range_filter.from_date == date(2024, 1, 1)
        assert request.date_range_filter.to_date == date(2024, 12, 31)

    def test_search_request_validation(self):
        """Test SearchRequest validation."""
        # Missing query
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(
                metadata_filters=[
                    MetadataFilter(
                        field_name="author",
                        operator="equals",
                        values=["John Doe"]
                    )
                ]
            )
        assert "query" in str(exc_info.value)

    def test_search_request_default_values(self):
        """Test SearchRequest default values."""
        request = SearchRequest(query="test")
        
        assert request.query == "test"
        assert request.limit == 10
        assert request.database_filters is None
        assert request.metadata_filters is None
        assert request.content_type_filters is None
        assert request.date_range_filter is None


@pytest.mark.unit
class TestChatRequestWithMetadataFilters:
    """Test ChatRequest with metadata filters."""
    
    def test_chat_request_with_metadata_filters(self):
        """Test ChatRequest with metadata filters."""
        request = ChatRequest(
            messages=[
                {"role": "user", "content": "Tell me about AI"}
            ],
            session_id="test-session-123",
            metadata_filters=[
                MetadataFilter(
                    field_name="tags",
                    operator="in",
                    values=["AI", "Machine Learning"]
                )
            ]
        )
        
        assert len(request.messages) == 1
        assert request.session_id == "test-session-123"
        assert len(request.metadata_filters) == 1
        assert request.metadata_filters[0].field_name == "tags"

    def test_chat_request_with_all_filter_types(self):
        """Test ChatRequest with all filter types."""
        request = ChatRequest(
            messages=[
                {"role": "user", "content": "Comprehensive chat query"}
            ],
            session_id="test-session-456",
            database_filters=["db-1"],
            metadata_filters=[
                MetadataFilter(
                    field_name="author",
                    operator="equals",
                    values=["Expert Author"]
                )
            ],
            content_type_filters=["article"],
            date_range_filter=DateRangeFilter(
                from_date="2024-01-01"
            )
        )
        
        assert len(request.messages) == 1
        assert request.session_id == "test-session-456"
        assert request.database_filters == ["db-1"]
        assert len(request.metadata_filters) == 1
        assert request.content_type_filters == ["article"]
        assert request.date_range_filter.from_date == date(2024, 1, 1)

    def test_chat_request_validation(self):
        """Test ChatRequest validation."""
        # Missing messages
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(
                session_id="test-session-123",
                metadata_filters=[
                    MetadataFilter(
                        field_name="author",
                        operator="equals",
                        values=["John Doe"]
                    )
                ]
            )
        assert "messages" in str(exc_info.value)

    def test_chat_request_serialization(self):
        """Test ChatRequest serialization with metadata filters."""
        request = ChatRequest(
            messages=[
                {"role": "user", "content": "Test message"}
            ],
            session_id="test-session-123",
            metadata_filters=[
                MetadataFilter(
                    field_name="author",
                    operator="equals",
                    values=["John Doe"]
                )
            ]
        )
        
        data = request.model_dump()
        
        assert "messages" in data
        assert "session_id" in data
        assert "metadata_filters" in data
        assert len(data["metadata_filters"]) == 1
        assert data["metadata_filters"][0]["field_name"] == "author"


@pytest.mark.unit
class TestDateRangeFilter:
    """Test DateRangeFilter model."""
    
    def test_date_range_filter_creation(self):
        """Test DateRangeFilter creation."""
        filter_obj = DateRangeFilter(
            from_date="2024-01-01",
            to_date="2024-12-31"
        )
        
        assert filter_obj.from_date == date(2024, 1, 1)
        assert filter_obj.to_date == date(2024, 12, 31)

    def test_date_range_filter_optional_fields(self):
        """Test DateRangeFilter with optional fields."""
        # Only from_date
        filter_obj = DateRangeFilter(from_date="2024-01-01")
        assert filter_obj.from_date == date(2024, 1, 1)
        assert filter_obj.to_date is None
        
        # Only to_date
        filter_obj = DateRangeFilter(to_date="2024-12-31")
        assert filter_obj.from_date is None
        assert filter_obj.to_date == date(2024, 12, 31)

    def test_date_range_filter_empty(self):
        """Test DateRangeFilter with no dates."""
        filter_obj = DateRangeFilter()
        assert filter_obj.from_date is None
        assert filter_obj.to_date is None 