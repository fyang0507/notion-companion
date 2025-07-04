"""
Metadata API Router - Dynamic Field Discovery and Aggregation

Provides endpoints for discovering available metadata fields, getting field values,
and aggregating metadata across databases for dynamic filtering.
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
import tomllib
from pathlib import Path
import asyncio

from database import get_db
from services.database_schema_manager import get_schema_manager
from logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/metadata", tags=["metadata"])

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class FieldDefinition(BaseModel):
    field_name: str
    field_type: str  # 'text', 'number', 'select', 'multi_select', 'date', 'checkbox', 'status'
    notion_field: str
    description: Optional[str] = None
    is_filterable: bool = True
    sample_values: Optional[List[Any]] = None

class DatabaseSchema(BaseModel):
    database_id: str
    database_name: str
    field_definitions: List[FieldDefinition]
    total_documents: int
    last_analyzed_at: Optional[datetime] = None
    is_active: bool = True

class AggregatedFieldInfo(BaseModel):
    field_name: str
    field_type: str
    databases: List[str]  # Database IDs that have this field
    unique_values: List[Any]
    value_counts: Dict[str, int]
    total_values: int

class FilterOptions(BaseModel):
    authors: List[str]
    tags: List[str]
    statuses: List[str]
    content_types: List[str]
    databases: List[Dict[str, str]]  # [{"id": "db_id", "name": "DB Name"}]
    date_ranges: Dict[str, Any]  # {"earliest": "date", "latest": "date"}

class MetadataStatsResponse(BaseModel):
    total_databases: int
    total_documents: int
    total_fields: int
    field_coverage: Dict[str, int]  # Field name -> count of databases that have it
    last_updated: datetime

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _load_database_configurations() -> List[Dict[str, Any]]:
    """Load all database configurations from databases.toml."""
    config_path = Path(__file__).parent.parent / 'config' / 'databases.toml'
    
    try:
        with open(config_path, 'rb') as f:
            config_data = tomllib.load(f)
        return config_data.get('databases', [])
    except Exception as e:
        logger.error(f"Failed to load database configurations: {str(e)}")
        return []

def _get_field_sample_values(db, database_id: str, field_name: str, limit: int = 10) -> List[Any]:
    """Get sample values for a field from the database."""
    try:
        # Use PostgreSQL query with table operations
        # This is a simplified approach - get all metadata for the database and extract in Python
        response = db.client.table('document_metadata').select('extracted_fields').eq('notion_database_id', database_id).limit(limit * 2).execute()
        
        values = set()
        for row in response.data:
            extracted_fields = row.get('extracted_fields', {})
            if field_name in extracted_fields:
                value = extracted_fields[field_name]
                if value:
                    if isinstance(value, list):
                        values.update(value)
                    elif isinstance(value, dict):
                        # Handle date fields that contain start/end dates
                        if 'start' in value and value['start']:
                            values.add(value['start'])
                        if 'end' in value and value['end']:
                            values.add(value['end'])
                    else:
                        values.add(value)
                if len(values) >= limit:
                    break
        
        return list(values)[:limit]
    except Exception as e:
        logger.warning(f"Failed to get sample values for field {field_name}: {str(e)}")
        return []

def _get_field_unique_values(db, database_id: str, field_name: str, limit: int = 100) -> List[Any]:
    """Get unique values for a field, handling arrays (multi_select) properly."""
    try:
        # Use table operations and handle arrays in Python
        response = db.client.table('document_metadata').select('extracted_fields').eq('notion_database_id', database_id).execute()
        
        values = set()
        for row in response.data:
            extracted_fields = row.get('extracted_fields', {})
            if field_name in extracted_fields:
                value = extracted_fields[field_name]
                if value:
                    if isinstance(value, list):
                        # Handle multi_select fields (arrays)
                        values.update(value)
                    elif isinstance(value, dict):
                        # Handle date fields that contain start/end dates
                        if 'start' in value and value['start']:
                            values.add(value['start'])
                        if 'end' in value and value['end']:
                            values.add(value['end'])
                    else:
                        values.add(value)
                if len(values) >= limit:
                    break
        
        return list(values)[:limit]
    except Exception as e:
        logger.warning(f"Failed to get unique values for field {field_name}: {str(e)}")
        return []

def _get_field_value_counts(db, database_id: str, field_name: str) -> Dict[str, int]:
    """Get value counts for a field."""
    try:
        # Use table operations and count in Python
        response = db.client.table('document_metadata').select('extracted_fields').eq('notion_database_id', database_id).execute()
        
        value_counts = {}
        for row in response.data:
            extracted_fields = row.get('extracted_fields', {})
            if field_name in extracted_fields:
                value = extracted_fields[field_name]
                if value:
                    if isinstance(value, list):
                        # Handle multi_select fields (arrays)
                        for v in value:
                            if v:
                                value_counts[str(v)] = value_counts.get(str(v), 0) + 1
                    elif isinstance(value, dict):
                        # Handle date fields that contain start/end dates
                        if 'start' in value and value['start']:
                            value_counts[str(value['start'])] = value_counts.get(str(value['start']), 0) + 1
                        if 'end' in value and value['end']:
                            value_counts[str(value['end'])] = value_counts.get(str(value['end']), 0) + 1
                    else:
                        value_counts[str(value)] = value_counts.get(str(value), 0) + 1
        
        # Sort by count descending and limit to 50
        sorted_counts = dict(sorted(value_counts.items(), key=lambda x: x[1], reverse=True)[:50])
        return sorted_counts
    except Exception as e:
        logger.warning(f"Failed to get value counts for field {field_name}: {str(e)}")
        return {}

# ============================================================================
# MAIN ENDPOINTS
# ============================================================================

@router.get("/databases", response_model=List[DatabaseSchema])
async def get_database_schemas(
    include_sample_values: bool = Query(False, description="Include sample values for fields"),
    db=Depends(get_db)
):
    """Get metadata schemas for all configured databases."""
    try:
        configurations = _load_database_configurations()
        schemas = []
        
        for config in configurations:
            database_id = config.get('database_id')
            if not database_id:
                continue
                
            # Get document count
            doc_count_result = db.client.table('documents').select('id', count='exact').eq('notion_database_id', database_id).execute()
            doc_count = doc_count_result.count or 0
            
            # Get field definitions from config
            field_definitions = []
            metadata_config = config.get('metadata', {})
            
            for field_name, field_config in metadata_config.items():
                field_def = FieldDefinition(
                    field_name=field_name,
                    field_type=field_config.get('type', 'text'),
                    notion_field=field_config.get('notion_field', field_name),
                    description=field_config.get('description'),
                    is_filterable=field_config.get('filterable', True)
                )
                
                # Add sample values if requested
                if include_sample_values and field_def.is_filterable:
                    field_def.sample_values = _get_field_sample_values(db, database_id, field_name)
                
                field_definitions.append(field_def)
            
            # Get last analysis time from database
            last_analyzed = None
            try:
                analysis_result = db.client.table('notion_databases').select('last_analyzed_at').eq('database_id', database_id).execute()
                if analysis_result.data:
                    last_analyzed = analysis_result.data[0].get('last_analyzed_at')
            except:
                pass
            
            schema = DatabaseSchema(
                database_id=database_id,
                database_name=config.get('name', f'Database {database_id}'),
                field_definitions=field_definitions,
                total_documents=doc_count,
                last_analyzed_at=last_analyzed,
                is_active=config.get('active', True)
            )
            schemas.append(schema)
        
        return schemas
        
    except Exception as e:
        logger.error(f"Failed to get database schemas: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve database schemas")

@router.get("/databases/{database_id}/fields", response_model=List[FieldDefinition])
async def get_database_fields(
    database_id: str,
    include_sample_values: bool = Query(True, description="Include sample values for fields"),
    db=Depends(get_db)
):
    """Get detailed field definitions for a specific database."""
    try:
        configurations = _load_database_configurations()
        
        # Find the database configuration
        db_config = None
        for config in configurations:
            if config.get('database_id') == database_id:
                db_config = config
                break
        
        if not db_config:
            raise HTTPException(status_code=404, detail=f"Database {database_id} not found")
        
        field_definitions = []
        metadata_config = db_config.get('metadata', {})
        
        for field_name, field_config in metadata_config.items():
            field_def = FieldDefinition(
                field_name=field_name,
                field_type=field_config.get('type', 'text'),
                notion_field=field_config.get('notion_field', field_name),
                description=field_config.get('description'),
                is_filterable=field_config.get('filterable', True)
            )
            
            # Add sample values if requested
            if include_sample_values and field_def.is_filterable:
                field_def.sample_values = _get_field_sample_values(db, database_id, field_name)
            
            field_definitions.append(field_def)
        
        return field_definitions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get fields for database {database_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve database fields")

@router.get("/databases/{database_id}/field-values/{field_name}")
async def get_field_values(
    database_id: str,
    field_name: str,
    include_counts: bool = Query(True, description="Include value counts"),
    limit: int = Query(100, description="Maximum number of values to return"),
    db=Depends(get_db)
):
    """Get unique values for a specific field in a database."""
    try:
        # Get unique values
        unique_values = _get_field_unique_values(db, database_id, field_name, limit)
        
        response = {
            "field_name": field_name,
            "database_id": database_id,
            "unique_values": unique_values,
            "total_unique": len(unique_values)
        }
        
        # Add counts if requested
        if include_counts:
            response["value_counts"] = _get_field_value_counts(db, database_id, field_name)
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get values for field {field_name} in database {database_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve field values")

@router.get("/aggregated-fields", response_model=List[AggregatedFieldInfo])
async def get_aggregated_fields(
    field_names: Optional[List[str]] = Query(None, description="Specific field names to aggregate"),
    db=Depends(get_db)
):
    """Get aggregated metadata fields across all databases."""
    try:
        configurations = _load_database_configurations()
        
        # Collect all field names across databases
        all_fields = {}
        for config in configurations:
            database_id = config.get('database_id')
            if not database_id:
                continue
                
            metadata_config = config.get('metadata', {})
            for field_name, field_config in metadata_config.items():
                if field_names and field_name not in field_names:
                    continue
                    
                if field_name not in all_fields:
                    all_fields[field_name] = {
                        'field_type': field_config.get('type', 'text'),
                        'databases': [],
                        'all_values': set(),
                        'all_counts': {}
                    }
                
                all_fields[field_name]['databases'].append(database_id)
        
        # Get aggregated data for each field
        aggregated_info = []
        for field_name, field_info in all_fields.items():
            # Collect unique values across all databases that have this field
            combined_values = set()
            combined_counts = {}
            
            for database_id in field_info['databases']:
                values = _get_field_unique_values(db, database_id, field_name, 50)
                combined_values.update(values)
                
                counts = _get_field_value_counts(db, database_id, field_name)
                for value, count in counts.items():
                    combined_counts[value] = combined_counts.get(value, 0) + count
            
            aggregated_info.append(AggregatedFieldInfo(
                field_name=field_name,
                field_type=field_info['field_type'],
                databases=field_info['databases'],
                unique_values=list(combined_values),
                value_counts=combined_counts,
                total_values=len(combined_values)
            ))
        
        return aggregated_info
        
    except Exception as e:
        logger.error(f"Failed to get aggregated fields: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve aggregated fields")

@router.get("/filter-options", response_model=FilterOptions)
async def get_filter_options(db=Depends(get_db)):
    """Get all available filter options for the UI."""
    try:
        # Get database list
        databases = []
        configurations = _load_database_configurations()
        for config in configurations:
            databases.append({
                "id": config.get('database_id'),
                "name": config.get('name', f"Database {config.get('database_id')}")
            })
        
        # Get aggregated field values for common filter fields
        common_fields = ['author', 'tags', 'status']
        aggregated_fields = await get_aggregated_fields(field_names=common_fields, db=db)
        
        authors = []
        tags = []
        statuses = []
        
        for field_info in aggregated_fields:
            if field_info.field_name == 'author':
                authors = field_info.unique_values[:50]  # Limit to 50 most common
            elif field_info.field_name == 'tags':
                tags = field_info.unique_values[:100]  # Limit to 100 most common
            elif field_info.field_name == 'status':
                statuses = field_info.unique_values[:20]  # Limit to 20 most common
        
        # Get content types
        content_types_result = db.client.table('documents').select('content_type').execute()
        content_types = list(set([doc['content_type'] for doc in content_types_result.data if doc.get('content_type')]))
        
        # Get date ranges using table operations
        documents_response = db.client.table('documents').select('created_time, last_edited_time').execute()
        
        date_ranges = {"earliest": None, "latest": None}
        if documents_response.data:
            dates = []
            for doc in documents_response.data:
                if doc.get('created_time'):
                    dates.append(doc['created_time'])
                if doc.get('last_edited_time'):
                    dates.append(doc['last_edited_time'])
            
            if dates:
                date_ranges = {
                    "earliest": min(dates),
                    "latest": max(dates)
                }
        
        return FilterOptions(
            authors=authors,
            tags=tags,
            statuses=statuses,
            content_types=content_types,
            databases=databases,
            date_ranges=date_ranges
        )
        
    except Exception as e:
        logger.error(f"Failed to get filter options: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve filter options")

@router.get("/stats", response_model=MetadataStatsResponse)
async def get_metadata_stats(db=Depends(get_db)):
    """Get overall metadata statistics."""
    try:
        # Get database count
        db_count_result = db.client.table('notion_databases').select('database_id', count='exact').execute()
        total_databases = db_count_result.count or 0
        
        # Get document count
        doc_count_result = db.client.table('documents').select('id', count='exact').execute()
        total_documents = doc_count_result.count or 0
        
        # Get field coverage from configurations
        configurations = _load_database_configurations()
        field_coverage = {}
        total_fields = 0
        
        for config in configurations:
            metadata_config = config.get('metadata', {})
            for field_name in metadata_config.keys():
                field_coverage[field_name] = field_coverage.get(field_name, 0) + 1
                total_fields += 1
        
        return MetadataStatsResponse(
            total_databases=total_databases,
            total_documents=total_documents,
            total_fields=len(field_coverage),
            field_coverage=field_coverage,
            last_updated=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Failed to get metadata stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metadata stats")

# ============================================================================
# CACHE REFRESH ENDPOINTS
# ============================================================================

@router.post("/cache/refresh")
async def refresh_metadata_cache(
    database_id: Optional[str] = Query(None, description="Specific database to refresh"),
    db=Depends(get_db)
):
    """Refresh metadata cache for databases."""
    try:
        if database_id:
            # Refresh specific database
            result = db.client.table('notion_databases').update({
                'last_analyzed_at': datetime.now().isoformat()
            }).eq('database_id', database_id).execute()
            
            return {"message": f"Cache refreshed for database {database_id}", "success": True}
        else:
            # Refresh all databases
            result = db.client.table('notion_databases').update({
                'last_analyzed_at': datetime.now().isoformat()
            }).execute()
            
            return {"message": "Cache refreshed for all databases", "success": True}
            
    except Exception as e:
        logger.error(f"Failed to refresh metadata cache: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to refresh metadata cache") 