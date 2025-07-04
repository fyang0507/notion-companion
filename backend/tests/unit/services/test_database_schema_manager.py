"""Tests for simplified Database Schema Manager."""

import pytest
from unittest.mock import patch, Mock
from pathlib import Path
import tomllib
from datetime import datetime

from services.database_schema_manager import DatabaseSchemaManager, get_schema_manager
from database import Database


@pytest.mark.unit
class TestDatabaseSchemaManager:
    """Test simplified Database Schema Manager functionality."""
    
    @pytest.fixture
    def database_service(self, mock_supabase_client):
        """Create database service with mocked client."""
        with patch('database.create_client') as mock_create_client:
            mock_create_client.return_value = mock_supabase_client
            db = Database()
            db.client = mock_supabase_client
            return db
    
    @pytest.fixture
    def schema_manager(self, database_service):
        """Create schema manager instance."""
        return DatabaseSchemaManager(database_service)
    
    @pytest.fixture
    def real_config_data(self):
        """Load real configuration from databases.toml."""
        config_path = Path(__file__).parent.parent.parent.parent / 'config' / 'databases.toml'
        with open(config_path, 'rb') as f:
            return tomllib.load(f)

    def test_load_database_config_real_config(self, schema_manager, real_config_data):
        """Test loading real database configuration."""
        test_db_id = "1519782c4f4a80dc9deff9768446a113"
        
        config = schema_manager._load_database_config(test_db_id)
        
        # Verify the configuration is loaded correctly
        assert config is not None
        assert config.get('name') == "他山之石"
        assert config.get('database_id') == test_db_id
        assert config.get('description') == "其他人的好文章"
        
        # Verify metadata configuration
        metadata = config.get('metadata', {})
        assert 'author' in metadata
        assert 'published_date' in metadata
        assert 'status' in metadata
        assert 'select' in metadata
        assert 'tags' in metadata
        
        # Verify specific field mappings
        assert metadata['author']['notion_field'] == "Author"
        assert metadata['author']['type'] == "text"
        assert metadata['published_date']['notion_field'] == "Date"
        assert metadata['published_date']['type'] == "date"
        assert metadata['status']['notion_field'] == "Status"
        assert metadata['status']['type'] == "status"
        assert metadata['select']['notion_field'] == "Select"
        assert metadata['select']['type'] == "select"
        assert metadata['tags']['notion_field'] == "Multi-select"
        assert metadata['tags']['type'] == "multi_select"

    def test_load_database_config_missing_database(self, schema_manager):
        """Test loading configuration for non-existent database."""
        config = schema_manager._load_database_config("non-existent-id")
        assert config == {}

    def test_extract_field_value_text_field(self, schema_manager):
        """Test extracting values from text fields."""
        field_data = {"text": [{"plain_text": "Test content"}]}
        result = schema_manager._extract_field_value(field_data, "text")
        assert result == "Test content"
        
        # Test with empty content
        field_data = {"text": []}
        result = schema_manager._extract_field_value(field_data, "text")
        assert result is None

    def test_extract_field_value_select_field(self, schema_manager):
        """Test extracting values from select fields."""
        field_data = {"select": {"name": "Option A"}}
        result = schema_manager._extract_field_value(field_data, "select")
        assert result == "Option A"
        
        # Test with no selection
        field_data = {"select": None}
        result = schema_manager._extract_field_value(field_data, "select")
        assert result is None

    def test_extract_field_value_multi_select_field(self, schema_manager):
        """Test extracting values from multi-select fields."""
        field_data = {"multi_select": [{"name": "Tag1"}, {"name": "Tag2"}]}
        result = schema_manager._extract_field_value(field_data, "multi_select")
        assert result == ["Tag1", "Tag2"]

    def test_extract_field_value_date_field(self, schema_manager):
        """Test extracting values from date fields."""
        field_data = {"date": {"start": "2023-01-15", "end": "2023-01-16"}}
        result = schema_manager._extract_field_value(field_data, "date")
        assert result == {"start": "2023-01-15", "end": "2023-01-16"}
        
        # Test with only start date
        field_data = {"date": {"start": "2023-01-15"}}
        result = schema_manager._extract_field_value(field_data, "date")
        assert result == {"start": "2023-01-15", "end": None}

    def test_extract_field_value_status_field(self, schema_manager):
        """Test extracting values from status fields."""
        field_data = {"status": {"name": "In Progress"}}
        result = schema_manager._extract_field_value(field_data, "status")
        assert result == "In Progress"

    def test_extract_field_value_number_field(self, schema_manager):
        """Test extracting values from number fields."""
        field_data = {"number": 42}
        result = schema_manager._extract_field_value(field_data, "number")
        assert result == 42
        
        # Test with null number
        field_data = {"number": None}
        result = schema_manager._extract_field_value(field_data, "number")
        assert result is None

    def test_extract_field_value_checkbox_field(self, schema_manager):
        """Test extracting values from checkbox fields."""
        field_data = {"checkbox": True}
        result = schema_manager._extract_field_value(field_data, "checkbox")
        assert result is True
        
        field_data = {"checkbox": False}
        result = schema_manager._extract_field_value(field_data, "checkbox")
        assert result is False

    @pytest.mark.anyio
    async def test_extract_document_metadata_real_config(self, schema_manager):
        """Test document metadata extraction with real configuration."""
        # Mock page data with real field values
        page_data = {
            'properties': {
                'Author': {'text': [{'plain_text': '张三'}]},
                'Date': {'date': {'start': '2023-01-15'}},
                'Status': {'status': {'name': '已读'}},
                'Select': {'select': {'name': '技术'}},
                'Multi-select': {'multi_select': [{'name': 'AI'}, {'name': '编程'}]}
            },
            'created_time': '2023-01-15T10:00:00.000Z',
            'last_edited_time': '2023-01-15T10:30:00.000Z'
        }
        
        result = await schema_manager.extract_document_metadata(
            'doc-1', page_data, '1519782c4f4a80dc9deff9768446a113'
        )
        
        # Verify basic structure
        assert result['document_id'] == 'doc-1'
        assert result['database_id'] == '1519782c4f4a80dc9deff9768446a113'
        
        # Verify field mappings (config names)
        assert result['author'] == '张三'
        assert result['published_date'] == {'start': '2023-01-15', 'end': None}
        assert result['status'] == '已读'
        assert result['select'] == '技术'
        assert result['tags'] == ['AI', '编程']
        
        # Verify timestamps
        assert result['created_date'] == '2023-01-15T10:00:00.000Z'
        assert result['modified_date'] == '2023-01-15T10:30:00.000Z'

    @pytest.mark.anyio
    async def test_extract_document_metadata_no_config(self, schema_manager):
        """Test metadata extraction when no configuration exists."""
        page_data = {'properties': {}}
        
        result = await schema_manager.extract_document_metadata(
            'doc-1', page_data, 'non-existent-db'
        )
        
        # Should return minimal metadata
        assert result['document_id'] == 'doc-1'
        assert result['database_id'] == 'non-existent-db'
        assert len(result) == 2  # Only document_id and database_id

    @pytest.mark.anyio
    async def test_extract_document_metadata_missing_fields(self, schema_manager):
        """Test metadata extraction when some fields are missing."""
        # Page data missing some configured fields
        page_data = {
            'properties': {
                'Author': {'text': [{'plain_text': '张三'}]},
                # Missing Date, Status, etc.
            },
            'created_time': '2023-01-15T10:00:00.000Z'
        }
        
        result = await schema_manager.extract_document_metadata(
            'doc-1', page_data, '1519782c4f4a80dc9deff9768446a113'
        )
        
        # Should have author but not other fields
        assert result['author'] == '张三'
        assert 'published_date' not in result
        assert 'status' not in result
        assert result['created_date'] == '2023-01-15T10:00:00.000Z'

    def test_get_schema_manager_factory(self, database_service):
        """Test schema manager factory function."""
        manager = get_schema_manager(database_service)
        
        assert isinstance(manager, DatabaseSchemaManager)
        assert manager.db == database_service

    def test_supported_field_types(self, schema_manager):
        """Test supported field types configuration."""
        expected_types = {'text', 'number', 'select', 'status', 'multi_select', 'date', 'checkbox'}
        assert schema_manager.supported_field_types == expected_types
