"""
Database Schema Manager - Single Database Model

This webapp is designed to support ONLY ONE Notion workspace with multiple databases.
No workspace concept exists - all operations are per-database.
"""

from typing import Dict, List, Any, Optional, Tuple
import asyncio
import logging
from datetime import datetime
from database import Database
from services.notion_service import NotionService


class DatabaseSchemaManager:
    """
    Manages Notion database schemas and metadata extraction.
    Single database model - no workspace concept.
    """
    
    def __init__(self, db: Database):
        self.db = db
        self.logger = logging.getLogger(__name__)
        
        # Common field types that we prioritize for extraction
        self.priority_field_types = {
            'date': 10,
            'created_time': 10,
            'last_edited_time': 10,
            'select': 8,
            'multi_select': 8,
            'status': 9,
            'number': 7,
            'checkbox': 6,
            'title': 10,
            'rich_text': 5,
            'url': 4,
            'email': 6,
            'phone_number': 6,
            'people': 7,
            'relation': 6
        }
    
    async def analyze_database_schema(self, database_id: str, notion_service: NotionService) -> Dict[str, Any]:
        """
        Analyze a Notion database to extract its schema and identify queryable fields.
        Single database model - no workspace concept.
        """
        try:
            self.logger.info(f"Analyzing schema for database: {database_id}")
            
            # Get database metadata from Notion
            database_info = await self._get_database_info(database_id, notion_service)
            
            # Get sample pages to understand the data patterns
            sample_pages = await self._get_sample_pages(database_id, notion_service)
            
            # Analyze the schema
            schema_analysis = await self._analyze_properties(database_info, sample_pages)
            
            # Identify which fields to extract for efficient querying
            queryable_fields = await self._identify_queryable_fields(schema_analysis)
            
            # Store the schema (no workspace_id)
            schema_record = {
                'database_id': database_id,
                'database_name': database_info.get('title', [{}])[0].get('plain_text', 'Unknown'),
                'notion_schema': database_info,
                'field_definitions': schema_analysis,
                'queryable_fields': queryable_fields,
                'last_analyzed_at': datetime.utcnow().isoformat()
            }
            
            self._store_schema(schema_record)
            
            self.logger.info(f"Schema analysis completed for {database_id}. "
                           f"Found {len(queryable_fields)} queryable fields.")
            
            return schema_record
            
        except Exception as e:
            self.logger.error(f"Failed to analyze database schema {database_id}: {str(e)}")
            raise
    
    async def _get_database_info(self, database_id: str, notion_service: NotionService) -> Dict[str, Any]:
        """Get database metadata from Notion API."""
        try:
            # Use the Notion client directly to get database info
            return notion_service.client.databases.retrieve(database_id=database_id)
        except Exception as e:
            self.logger.error(f"Failed to get database info for {database_id}: {str(e)}")
            raise
    
    async def _get_sample_pages(self, database_id: str, notion_service: NotionService, 
                              sample_size: int = 20) -> List[Dict[str, Any]]:
        """Get a sample of pages from the database to understand data patterns."""
        try:
            pages = await notion_service.get_database_pages(database_id)
            
            # Return a sample (up to sample_size pages)
            return pages[:sample_size] if len(pages) > sample_size else pages
            
        except Exception as e:
            self.logger.error(f"Failed to get sample pages for {database_id}: {str(e)}")
            return []
    
    async def _analyze_properties(self, database_info: Dict[str, Any], 
                                sample_pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze database properties and sample data to understand the schema."""
        properties = database_info.get('properties', {})
        field_analysis = {}
        
        for field_name, field_config in properties.items():
            field_type = field_config.get('type')
            
            # Analyze this field
            field_analysis[field_name] = {
                'type': field_type,
                'notion_config': field_config,
                'data_patterns': await self._analyze_field_data(field_name, field_type, sample_pages),
                'priority_score': self.priority_field_types.get(field_type, 1),
                'is_commonly_used': self._is_field_commonly_used(field_name, sample_pages),
                'unique_values': await self._get_unique_values_sample(field_name, sample_pages),
                'data_types': await self._infer_data_types(field_name, field_type, sample_pages)
            }
        
        return field_analysis
    
    async def _analyze_field_data(self, field_name: str, field_type: str, 
                                sample_pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze actual data in this field across sample pages."""
        values = []
        non_empty_count = 0
        
        for page in sample_pages:
            properties = page.get('properties', {})
            field_data = properties.get(field_name, {})
            
            value = self._extract_field_value(field_data, field_type)
            if value is not None:
                values.append(value)
                non_empty_count += 1
        
        return {
            'total_samples': len(sample_pages),
            'non_empty_count': non_empty_count,
            'fill_rate': non_empty_count / len(sample_pages) if sample_pages else 0,
            'sample_values': values[:10],  # First 10 values as examples
            'value_count': len(values)
        }
    
    def _extract_field_value(self, field_data: Dict[str, Any], field_type: str) -> Any:
        """Extract the actual value from a Notion field based on its type."""
        if not field_data:
            return None
            
        try:
            if field_type == 'title':
                title_data = field_data.get('title', [])
                return ''.join([t.get('plain_text', '') for t in title_data]) if title_data else None
                
            elif field_type == 'rich_text':
                rich_text = field_data.get('rich_text', [])
                return ''.join([t.get('plain_text', '') for t in rich_text]) if rich_text else None
                
            elif field_type == 'number':
                return field_data.get('number')
                
            elif field_type == 'select':
                select_data = field_data.get('select')
                return select_data.get('name') if select_data else None
                
            elif field_type == 'multi_select':
                multi_select = field_data.get('multi_select', [])
                return [item.get('name') for item in multi_select]
                
            elif field_type == 'date':
                date_data = field_data.get('date')
                if date_data:
                    return {
                        'start': date_data.get('start'),
                        'end': date_data.get('end')
                    }
                    
            elif field_type == 'checkbox':
                return field_data.get('checkbox')
                
            elif field_type == 'url':
                return field_data.get('url')
                
            elif field_type == 'email':
                return field_data.get('email')
                
            elif field_type == 'phone_number':
                return field_data.get('phone_number')
                
            elif field_type == 'status':
                status_data = field_data.get('status')
                return status_data.get('name') if status_data else None
                
            elif field_type in ['created_time', 'last_edited_time']:
                return field_data.get(field_type)
                
            elif field_type == 'people':
                people = field_data.get('people', [])
                return [person.get('name', person.get('id')) for person in people]
                
            elif field_type == 'relation':
                relations = field_data.get('relation', [])
                return [rel.get('id') for rel in relations]
                
            else:
                # For unknown types, return the raw data
                return field_data
                
        except Exception as e:
            self.logger.warning(f"Failed to extract value for field type {field_type}: {str(e)}")
            return None
    
    def _is_field_commonly_used(self, field_name: str, sample_pages: List[Dict[str, Any]]) -> bool:
        """Determine if a field is commonly used (has values in most pages)."""
        if not sample_pages:
            return False
            
        filled_count = 0
        for page in sample_pages:
            field_data = page.get('properties', {}).get(field_name, {})
            if self._has_meaningful_value(field_data):
                filled_count += 1
        
        fill_rate = filled_count / len(sample_pages)
        return fill_rate > 0.3  # Consider commonly used if >30% of pages have values
    
    def _has_meaningful_value(self, field_data: Dict[str, Any]) -> bool:
        """Check if a field has a meaningful (non-empty) value."""
        if not field_data:
            return False
            
        # Check different field types for meaningful values
        for key in ['title', 'rich_text', 'select', 'multi_select', 'number', 
                   'checkbox', 'date', 'url', 'email', 'phone_number', 'status', 'people', 'relation']:
            value = field_data.get(key)
            if value is not None:
                if isinstance(value, list) and len(value) > 0:
                    return True
                elif isinstance(value, (str, int, float, bool)) and value != '':
                    return True
                elif isinstance(value, dict) and value:
                    return True
        
        return False
    
    async def _get_unique_values_sample(self, field_name: str, 
                                      sample_pages: List[Dict[str, Any]]) -> List[Any]:
        """Get a sample of unique values for this field."""
        unique_values = set()
        
        for page in sample_pages:
            field_data = page.get('properties', {}).get(field_name, {})
            value = self._extract_field_value(field_data, '')
            
            if value is not None:
                if isinstance(value, list):
                    unique_values.update(value)
                else:
                    unique_values.add(str(value))
                    
            if len(unique_values) >= 20:  # Limit sample size
                break
        
        return list(unique_values)[:20]
    
    async def _infer_data_types(self, field_name: str, field_type: str, 
                              sample_pages: List[Dict[str, Any]]) -> List[str]:
        """Infer the actual data types we should use for this field."""
        if field_type in ['title', 'rich_text', 'url', 'email', 'phone_number']:
            return ['text']
        elif field_type == 'number':
            return ['number']
        elif field_type in ['date', 'created_time', 'last_edited_time']:
            return ['date', 'datetime']
        elif field_type == 'checkbox':
            return ['boolean']
        elif field_type in ['select', 'status']:
            return ['text']  # Store as text for querying
        elif field_type == 'multi_select':
            return ['array']
        elif field_type == 'people':
            return ['array']
        elif field_type == 'relation':
            return ['array']
        else:
            return ['text']  # Default to text
    
    async def _identify_queryable_fields(self, schema_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Identify which fields should be extracted for efficient querying."""
        queryable_fields = {}
        
        for field_name, analysis in schema_analysis.items():
            # Calculate queryability score
            score = 0
            
            # Priority based on field type
            score += analysis.get('priority_score', 1) * 10
            
            # Boost score if commonly used
            if analysis.get('is_commonly_used', False):
                score += 20
            
            # Boost score based on fill rate
            fill_rate = analysis.get('data_patterns', {}).get('fill_rate', 0)
            score += fill_rate * 15
            
            # Boost score for temporal fields (very important for queries)
            if analysis.get('type') in ['date', 'created_time', 'last_edited_time']:
                score += 25
            
            # Boost score for categorical fields (good for filtering)
            if analysis.get('type') in ['select', 'multi_select', 'status']:
                score += 15
            
            # Consider queryable if score is high enough
            if score >= 30:  # Threshold for queryability
                queryable_fields[field_name] = {
                    'field_type': analysis.get('type'),
                    'data_types': analysis.get('data_types', ['text']),
                    'priority_score': score,
                    'extraction_config': self._get_extraction_config(analysis)
                }
        
        return queryable_fields
    
    def _get_extraction_config(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Get configuration for how to extract and store this field."""
        field_type = analysis.get('type')
        
        config = {
            'extract_to_metadata_table': True,
            'create_index': True,
            'store_raw_value': True
        }
        
        # Type-specific configurations
        if field_type in ['date', 'created_time', 'last_edited_time']:
            config.update({
                'parse_as_date': True,
                'index_type': 'btree',
                'enable_range_queries': True
            })
        elif field_type in ['select', 'status']:
            config.update({
                'normalize_text': True,
                'index_type': 'btree',
                'enable_exact_match': True
            })
        elif field_type == 'multi_select':
            config.update({
                'store_as_array': True,
                'index_type': 'gin',
                'enable_contains_queries': True
            })
        elif field_type == 'number':
            config.update({
                'parse_as_number': True,
                'index_type': 'btree',
                'enable_range_queries': True
            })
        
        return config
    
    def _store_schema(self, schema_record: Dict[str, Any]) -> None:
        """
        Store the analyzed schema in the database.
        Single database model - no workspace_id.
        """
        try:
            self.db.client.table('database_schemas').upsert(schema_record).execute()
            self.logger.info(f"Stored schema for database {schema_record['database_id']}")
        except Exception as e:
            self.logger.error(f"Failed to store schema: {str(e)}")
            raise
    
    async def get_schema(self, database_id: str) -> Optional[Dict[str, Any]]:
        """Get stored schema for a database."""
        try:
            response = self.db.client.table('database_schemas').select(
                '*'
            ).eq('database_id', database_id).execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            self.logger.error(f"Failed to get schema for {database_id}: {str(e)}")
            return None
    
    async def extract_document_metadata(self, document_id: str, page_data: Dict[str, Any], 
                                      database_id: str) -> List[Dict[str, Any]]:
        """
        Extract metadata from a document based on the database schema.
        Single database model - no workspace concept.
        """
        schema = await self.get_schema(database_id)
        if not schema:
            self.logger.warning(f"No schema found for database {database_id}")
            return []
        
        queryable_fields = schema.get('queryable_fields', {})
        extracted_metadata = []
        
        properties = page_data.get('properties', {})
        
        for field_name, field_config in queryable_fields.items():
            if field_name not in properties:
                continue
                
            field_data = properties[field_name]
            raw_value = self._extract_field_value(field_data, field_config['field_type'])
            
            if raw_value is not None:
                # Convert to appropriate typed values
                typed_values = self._convert_to_typed_values(raw_value, field_config)
                
                metadata_record = {
                    'document_id': document_id,
                    'field_name': field_name,
                    'field_type': field_config['field_type'],
                    'raw_value': raw_value,
                    **typed_values
                }
                
                extracted_metadata.append(metadata_record)
        
        return extracted_metadata
    
    def _convert_to_typed_values(self, raw_value: Any, field_config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert raw value to appropriate typed columns."""
        typed_values = {
            'text_value': None,
            'number_value': None,
            'date_value': None,
            'datetime_value': None,
            'boolean_value': None,
            'array_value': None
        }
        
        field_type = field_config['field_type']
        
        try:
            if field_type in ['title', 'rich_text', 'url', 'email', 'phone_number', 'select', 'status']:
                typed_values['text_value'] = str(raw_value) if raw_value else None
                
            elif field_type == 'number':
                typed_values['number_value'] = float(raw_value) if raw_value is not None else None
                
            elif field_type == 'checkbox':
                typed_values['boolean_value'] = bool(raw_value) if raw_value is not None else None
                
            elif field_type in ['multi_select', 'people', 'relation']:
                typed_values['array_value'] = raw_value if isinstance(raw_value, list) else None
                
            elif field_type == 'date':
                if isinstance(raw_value, dict):
                    start_date = raw_value.get('start')
                    if start_date:
                        # Try to parse as date or datetime
                        if 'T' in start_date:
                            typed_values['datetime_value'] = start_date
                        else:
                            typed_values['date_value'] = start_date
                            
            elif field_type in ['created_time', 'last_edited_time']:
                typed_values['datetime_value'] = raw_value
                
        except Exception as e:
            self.logger.warning(f"Failed to convert value {raw_value} for field type {field_type}: {str(e)}")
        
        return typed_values


def get_schema_manager(db: Database) -> DatabaseSchemaManager:
    """Factory function to create DatabaseSchemaManager instance."""
    return DatabaseSchemaManager(db)