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

from storage.database import get_db
from storage.database_schema_manager import get_schema_manager
from shared.logging.logging_config import get_logger

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
    content_types: List[str]
    databases: List[Dict[str, str]]  # [{"id": "db_id", "name": "DB Name"}]
    date_ranges: Dict[str, Any]  # {"earliest": "date", "latest": "date"}
    dynamic_fields: Dict[str, List[str]]  # Field name -> list of values (configuration-driven)

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

def _get_field_unique_values(
    db, 
    database_id: str, 
    field_name: str, 
    limit: int = 100,
    search: Optional[str] = None,
    sort_by: str = 'count_desc',
    offset: int = 0
) -> Dict[str, Any]:
    """Get unique values for a field with search, sorting, and pagination."""
    try:
        # Use table operations and handle arrays in Python
        response = db.client.table('document_metadata').select('extracted_fields').eq('notion_database_id', database_id).execute()
        
        values = {}  # value -> count
        for row in response.data:
            extracted_fields = row.get('extracted_fields', {})
            if field_name in extracted_fields:
                value = extracted_fields[field_name]
                if value:
                    if isinstance(value, list):
                        # Handle multi_select fields (arrays)
                        for v in value:
                            if v:
                                str_v = str(v)
                                values[str_v] = values.get(str_v, 0) + 1
                    elif isinstance(value, dict):
                        # Handle date fields that contain start/end dates
                        if 'start' in value and value['start']:
                            str_v = str(value['start'])
                            values[str_v] = values.get(str_v, 0) + 1
                        if 'end' in value and value['end']:
                            str_v = str(value['end'])
                            values[str_v] = values.get(str_v, 0) + 1
                    else:
                        str_v = str(value)
                        values[str_v] = values.get(str_v, 0) + 1

        # Filter by search term if provided
        if search:
            search_lower = search.lower()
            values = {k: v for k, v in values.items() if search_lower in k.lower()}

        # Sort values
        if sort_by == 'alpha_asc':
            sorted_items = sorted(values.items(), key=lambda x: x[0].lower())
        elif sort_by == 'alpha_desc':
            sorted_items = sorted(values.items(), key=lambda x: x[0].lower(), reverse=True)
        elif sort_by == 'count_asc':
            sorted_items = sorted(values.items(), key=lambda x: x[1])
        elif sort_by == 'value_asc':
            # Try to sort numerically for numbers, otherwise alphabetically
            try:
                sorted_items = sorted(values.items(), key=lambda x: float(x[0]))
            except ValueError:
                sorted_items = sorted(values.items(), key=lambda x: x[0])
        elif sort_by == 'value_desc':
            # Try to sort numerically for numbers, otherwise alphabetically
            try:
                sorted_items = sorted(values.items(), key=lambda x: float(x[0]), reverse=True)
            except ValueError:
                sorted_items = sorted(values.items(), key=lambda x: x[0], reverse=True)
        else:  # count_desc (default)
            sorted_items = sorted(values.items(), key=lambda x: x[1], reverse=True)

        # Apply pagination
        total_count = len(sorted_items)
        paginated_items = sorted_items[offset:offset + limit]

        # Extract unique values and counts
        unique_values = [item[0] for item in paginated_items]
        value_counts = dict(sorted_items)  # Keep all counts for reference

        return {
            'unique_values': unique_values,
            'value_counts': value_counts,
            'total_count': total_count,
            'returned_count': len(unique_values)
        }

    except Exception as e:
        logger.warning(f"Failed to get unique values for field {field_name}: {str(e)}")
        return {
            'unique_values': [],
            'value_counts': {},
            'total_count': 0,
            'returned_count': 0
        }

def _get_field_value_counts(db, database_id: str, field_name: str, limit: int = 50) -> Dict[str, int]:
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
        
        # Sort by count descending and limit
        sorted_counts = dict(sorted(value_counts.items(), key=lambda x: x[1], reverse=True)[:limit])
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
    search: Optional[str] = Query(None, description="Search within field values"),
    sort_by: str = Query('count_desc', description="Sort order: alpha_asc, alpha_desc, count_asc, count_desc, value_asc, value_desc"),
    offset: int = Query(0, description="Pagination offset"),
    db=Depends(get_db)
):
    """Get unique values for a specific field in a database with search and pagination."""
    try:
        # Get unique values with enhanced filtering
        result = _get_field_unique_values(
            db=db, 
            database_id=database_id, 
            field_name=field_name,
            limit=limit,
            search=search,
            sort_by=sort_by,
            offset=offset
        )
        
        response = {
            "field_name": field_name,
            "database_id": database_id,
            "unique_values": result['unique_values'],
            "total_unique": result['total_count'],
            "returned_count": result['returned_count'],
            "search_term": search,
            "sort_by": sort_by,
            "offset": offset,
            "limit": limit
        }
        
        # Add counts if requested
        if include_counts:
            response["value_counts"] = result['value_counts']
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get values for field {field_name} in database {database_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve field values")

@router.get("/aggregated-fields", response_model=List[AggregatedFieldInfo])
async def get_aggregated_fields(
    field_names: Optional[List[str]] = Query(None, description="Specific field names to aggregate"),
    search: Optional[str] = Query(None, description="Search within field values"),
    limit_per_field: int = Query(100, description="Maximum values per field"),
    db=Depends(get_db)
):
    """Get aggregated metadata fields across all databases with search support."""
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
                        'all_values': {},
                        'all_counts': {}
                    }
                
                all_fields[field_name]['databases'].append(database_id)
        
        # Get aggregated data for each field
        aggregated_info = []
        for field_name, field_info in all_fields.items():
            # Collect unique values across all databases that have this field
            combined_values = {}
            combined_counts = {}
            
            for database_id in field_info['databases']:
                # Get values with search support
                result = _get_field_unique_values(
                    db=db, 
                    database_id=database_id, 
                    field_name=field_name,
                    limit=limit_per_field,
                    search=search,
                    sort_by='count_desc'
                )
                
                # Merge values and counts
                for value in result['unique_values']:
                    combined_values[value] = True
                
                for value, count in result['value_counts'].items():
                    combined_counts[value] = combined_counts.get(value, 0) + count
            
            # Sort by count and limit
            sorted_values = sorted(combined_counts.items(), key=lambda x: x[1], reverse=True)[:limit_per_field]
            final_unique_values = [item[0] for item in sorted_values]
            final_counts = dict(sorted_values)
            
            aggregated_info.append(AggregatedFieldInfo(
                field_name=field_name,
                field_type=field_info['field_type'],
                databases=field_info['databases'],
                unique_values=final_unique_values,
                value_counts=final_counts,
                total_values=len(final_unique_values)
            ))
        
        return aggregated_info
        
    except Exception as e:
        logger.error(f"Failed to get aggregated fields: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve aggregated fields")

@router.get("/filter-options", response_model=FilterOptions)
async def get_filter_options(
    search: Optional[str] = Query(None, description="Search within filter values"),
    limit_per_field: int = Query(50, description="Maximum values per field"),
    db=Depends(get_db)
):
    """Get all available filter options for the UI with configuration-driven field discovery."""
    try:
        # Get database list
        databases = []
        configurations = _load_database_configurations()
        for config in configurations:
            databases.append({
                "id": config.get('database_id'),
                "name": config.get('name', f"Database {config.get('database_id')}")
            })
        
        # Discover all filterable fields from configurations
        filterable_fields = set()
        for config in configurations:
            metadata_config = config.get('metadata', {})
            for field_name, field_config in metadata_config.items():
                if field_config.get('filterable', True):
                    # Only include select, multi_select, and text fields for filtering
                    field_type = field_config.get('type', 'text')
                    if field_type in ['text', 'select', 'multi_select', 'status']:
                        filterable_fields.add(field_name)
        
        # Get aggregated field values for all filterable fields
        aggregated_fields = await get_aggregated_fields(
            field_names=list(filterable_fields), 
            search=search,
            limit_per_field=limit_per_field,
            db=db
        )
        
        # Build dynamic fields dictionary
        dynamic_fields = {}
        for field_info in aggregated_fields:
            if field_info.unique_values:  # Only include fields that have values
                dynamic_fields[field_info.field_name] = field_info.unique_values
        
        # Get content types
        content_types_result = db.client.table('documents').select('content_type').execute()
        content_types = list(set([doc['content_type'] for doc in content_types_result.data if doc.get('content_type')]))
        
        # Filter content types by search if provided
        if search:
            search_lower = search.lower()
            content_types = [ct for ct in content_types if search_lower in ct.lower()]
        
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
            content_types=content_types,
            databases=databases,
            date_ranges=date_ranges,
            dynamic_fields=dynamic_fields
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