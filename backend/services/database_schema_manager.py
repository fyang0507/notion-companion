"""
Database Schema Manager - Simple Configuration-based Metadata Extraction

Supported field types: text, number, select, status, multi_select, date, checkbox
"""

from typing import Dict, List, Any, Optional
import logging
import tomllib
from datetime import datetime
from pathlib import Path
from database import Database
from services.notion_service import NotionService


class DatabaseSchemaManager:
    """Simple Notion database metadata extraction based on configuration."""
    
    def __init__(self, db: Database):
        self.db = db
        self.logger = logging.getLogger(__name__)
        
        # Supported Notion field types
        self.supported_field_types = {
            'text', 'number', 'select', 'status', 'multi_select', 'date', 'checkbox'
        }
    
    def _load_database_config(self, database_id: str) -> Dict[str, Any]:
        """Load database configuration from databases.toml file."""
        config_path = Path(__file__).parent.parent / 'config' / 'databases.toml'
        
        try:
            with open(config_path, 'rb') as f:
                config_data = tomllib.load(f)
            
            for db_config in config_data.get('databases', []):
                if db_config.get('database_id') == database_id:
                    return db_config
                    
            self.logger.warning(f"No configuration found for database {database_id}")
            return {}
            
        except Exception as e:
            self.logger.error(f"Failed to load database configuration: {str(e)}")
            return {}
    
    def _extract_field_value(self, field_data: Dict[str, Any], field_type: str) -> Any:
        """Extract value from a Notion field."""
        if not field_data:
            return None
            
        try:
            if field_type == 'text':
                text_data = field_data.get('text', [])
                return ''.join([t.get('plain_text', '') for t in text_data]) if text_data else None
            elif field_type == 'number':
                return field_data.get('number')
            elif field_type == 'select':
                select_data = field_data.get('select')
                return select_data.get('name') if select_data else None
            elif field_type == 'multi_select':
                multi_select = field_data.get('multi_select', [])
                return [item.get('name') for item in multi_select]
            elif field_type == 'status':
                status_data = field_data.get('status')
                return status_data.get('name') if status_data else None
            elif field_type == 'date':
                date_data = field_data.get('date')
                if date_data:
                    return {
                        'start': date_data.get('start'),
                        'end': date_data.get('end')
                    }
            elif field_type == 'checkbox':
                return field_data.get('checkbox')
            else:
                return None
                
        except Exception as e:
            self.logger.warning(f"Failed to extract {field_type} field: {str(e)}")
            return None
    
    async def extract_document_metadata(self, document_id: str, page_data: Dict[str, Any], 
                                      database_id: str) -> Dict[str, Any]:
        """Extract metadata from a document based on configuration."""
        config = self._load_database_config(database_id)
        metadata_config = config.get('metadata', {})
        
        if not metadata_config:
            return {'document_id': document_id, 'database_id': database_id}
        
        properties = page_data.get('properties', {})
        metadata = {
            'document_id': document_id,
            'database_id': database_id
        }
        
        # Extract configured fields
        for config_name, field_config in metadata_config.items():
            notion_field = field_config.get('notion_field')
            field_type = field_config.get('type')
            
            if notion_field in properties:
                field_data = properties[notion_field]
                value = self._extract_field_value(field_data, field_type)
                if value is not None:
                    metadata[config_name] = value
        
        # Add timestamps
        if 'created_time' in page_data:
            metadata['created_date'] = page_data['created_time']
        if 'last_edited_time' in page_data:
            metadata['modified_date'] = page_data['last_edited_time']
        
        return metadata


def get_schema_manager(db: Database) -> DatabaseSchemaManager:
    """Factory function to create DatabaseSchemaManager instance."""
    return DatabaseSchemaManager(db)