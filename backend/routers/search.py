from fastapi import APIRouter, HTTPException
from database import get_db
from services.openai_service import get_openai_service
from services.contextual_search_engine import ContextualSearchEngine
from models import SearchRequest, SearchResponse, SearchResult
from config.model_config import get_model_config
from typing import Dict, Any, List, Optional
import asyncio
import logging
from pathlib import Path
import tomllib

router = APIRouter()
logger = logging.getLogger(__name__)

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

def _get_field_type_mapping() -> Dict[str, str]:
    """Create a mapping of field names to their configured types."""
    field_type_mapping = {}
    
    configurations = _load_database_configurations()
    for config in configurations:
        metadata_config = config.get('metadata', {})
        for field_name, field_config in metadata_config.items():
            field_type = field_config.get('type', 'text')
            field_type_mapping[field_name] = field_type
    
    return field_type_mapping

def _prepare_enhanced_search_filters(request: SearchRequest) -> Dict[str, Any]:
    """Prepare filter parameters for enhanced search with configuration-based field types."""
    filters = {}
    
    # Basic filters
    if request.database_filters:
        filters['database_filter'] = request.database_filters
    if request.content_type_filters:
        filters['content_type_filter'] = request.content_type_filters
    if request.author_filters:
        filters['author_filter'] = request.author_filters
    if request.tag_filters:
        filters['tag_filter'] = request.tag_filters
    if request.status_filters:
        filters['status_filter'] = request.status_filters
    
    # Date range filter
    if request.date_range_filter:
        date_range = {}
        if request.date_range_filter.from_date:
            date_range['from'] = request.date_range_filter.from_date.isoformat()
        if request.date_range_filter.to_date:
            date_range['to'] = request.date_range_filter.to_date.isoformat()
        if date_range:
            filters['date_range_filter'] = date_range
    
    # Metadata filters based on configuration
    if request.metadata_filters:
        # Get field type mappings from configuration
        field_type_mapping = _get_field_type_mapping()
        
        # Separate filters by configured field type
        text_filters = {}
        number_filters = {}
        select_filters = {}
        checkbox_filters = {}
        
        for filter_item in request.metadata_filters:
            field_name = filter_item.field_name
            operator = filter_item.operator
            values = filter_item.values
            
            # Get field type from configuration
            field_type = field_type_mapping.get(field_name)
            
            if not field_type:
                logger.warning(f"Field '{field_name}' not found in configuration, skipping filter")
                continue
            
            # Route to appropriate filter type based on configuration
            if field_type in ['text', 'rich_text']:
                if operator == 'equals':
                    text_filters[field_name] = values[0] if values else ""
                elif operator == 'in':
                    text_filters[field_name] = values
                elif operator == 'contains':
                    text_filters[field_name] = values
                    
            elif field_type in ['select', 'status']:
                if operator == 'equals':
                    select_filters[field_name] = values[0] if values else ""
                elif operator == 'in':
                    select_filters[field_name] = values
                    
            elif field_type == 'multi_select':
                # Multi-select maps to tag_filter
                if operator == 'equals':
                    if field_name not in filters:
                        filters['tag_filter'] = {field_name: [values[0]] if values else []}
                    else:
                        filters['tag_filter'][field_name] = [values[0]] if values else []
                elif operator == 'in':
                    if field_name not in filters:
                        filters['tag_filter'] = {field_name: values}
                    else:
                        filters['tag_filter'][field_name] = values
                        
            elif field_type == 'number':
                if operator == 'range' and values:
                    range_filter = {}
                    for value in values:
                        str_value = str(value)
                        if str_value.startswith('min:'):
                            range_filter['min'] = float(str_value[4:])
                        elif str_value.startswith('max:'):
                            range_filter['max'] = float(str_value[4:])
                    
                    if range_filter:
                        number_filters[field_name] = range_filter
                elif operator == 'equals':
                    number_filters[field_name] = {'equals': float(values[0]) if values else 0}
                    
            elif field_type == 'checkbox':
                if operator == 'equals' and values:
                    bool_value = str(values[0]).lower() in ['true', '1', 'yes']
                    checkbox_filters[field_name] = bool_value
                    
            elif field_type == 'date':
                # Date fields map to date_range_filter
                if operator == 'range' and values:
                    date_range = {}
                    for value in values:
                        str_value = str(value)
                        if str_value.startswith('from:'):
                            date_range['from'] = str_value[5:]
                        elif str_value.startswith('to:'):
                            date_range['to'] = str_value[3:]
                    
                    if date_range:
                        if 'date_range_filter' not in filters:
                            filters['date_range_filter'] = {}
                        filters['date_range_filter'].update(date_range)
        
        # Add type-specific filters to the main filters dict
        if text_filters:
            filters['text_filter'] = text_filters
        if number_filters:
            filters['number_filter'] = number_filters
        if select_filters:
            filters['select_filter'] = select_filters
        if checkbox_filters:
            filters['checkbox_filter'] = checkbox_filters
    
    return filters

@router.post("/search", response_model=SearchResponse)
async def enhanced_search_endpoint(request: SearchRequest):
    """Enhanced search endpoint with contextual retrieval and metadata filtering."""
    try:
        db = get_db()
        openai_service = get_openai_service()
        model_config = get_model_config()
        search_config = model_config.get_vector_search_config()
        
        # Initialize contextual search engine
        contextual_engine = ContextualSearchEngine(db, openai_service, search_config)
        
        # Check if advanced metadata filters are provided
        filters = _prepare_enhanced_search_filters(request)
        has_advanced_filters = any(key in filters for key in [
            'metadata_filters', 'author_filter', 'tag_filter', 'status_filter', 'date_range_filter',
            'text_filter', 'number_filter', 'select_filter', 'checkbox_filter'
        ])
        
        if has_advanced_filters:
            # Use enhanced metadata search for advanced filtering
            results = await contextual_engine.enhanced_metadata_search(
                query=request.query,
                filters=filters,
                match_threshold=search_config.match_threshold,
                match_count=min(request.limit, search_config.match_count_max)
            )
        else:
            # Use standard contextual search for basic database filtering
            results = await contextual_engine.contextual_search(
                query=request.query,
                database_filters=request.database_filters,
                include_context=search_config.enable_context_enrichment,
                match_threshold=search_config.match_threshold,
                match_count=min(request.limit, search_config.match_count_max)
            )
        
        # Format results for client
        search_results = []
        for result in results:
            # Use enriched content if available, otherwise fall back to regular content
            display_content = result.get('enriched_content', result.get('content', ''))
            
            # Truncate very long content for display
            if len(display_content) > 500:
                display_content = display_content[:500] + '...'
            
            # Handle both enhanced metadata search results and regular contextual search results
            result_id = result.get('chunk_id', result.get('id', ''))
            
            search_results.append(SearchResult(
                id=result_id,
                title=result.get('title', ''),
                content=display_content,
                similarity=result.get('final_score', result.get('combined_score', result.get('similarity', 0.0))),
                metadata=result.get('metadata', {}),
                notion_page_id=result.get('notion_page_id', ''),
                
                # Enhanced metadata fields
                result_type=result.get('result_type'),
                chunk_context=result.get('chunk_context'),
                chunk_summary=result.get('chunk_summary'),
                document_metadata=result.get('document_metadata'),
                page_url=result.get('page_url'),
                has_adjacent_context=result.get('has_adjacent_context'),
                database_id=result.get('database_id'),
                author=result.get('author'),
                tags=result.get('tags'),
                status=result.get('status'),
                created_date=result.get('created_date'),
                modified_date=result.get('modified_date')
            ))
        
        return SearchResponse(
            results=search_results,
            query=request.query,
            total=len(search_results)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enhanced search failed: {str(e)}")

@router.post("/search/hybrid", response_model=SearchResponse)
async def hybrid_search_endpoint(request: SearchRequest):
    """Hybrid search endpoint combining documents and contextual chunks with metadata filtering."""
    try:
        db = get_db()
        openai_service = get_openai_service()
        model_config = get_model_config()
        search_config = model_config.get_vector_search_config()
        
        # Initialize contextual search engine
        contextual_engine = ContextualSearchEngine(db, openai_service, search_config)
        
        # Check if advanced metadata filters are provided
        filters = _prepare_enhanced_search_filters(request)
        has_advanced_filters = any(key in filters for key in [
            'metadata_filters', 'author_filter', 'tag_filter', 'status_filter', 'date_range_filter',
            'text_filter', 'number_filter', 'select_filter', 'checkbox_filter'
        ])
        
        if has_advanced_filters:
            # Use enhanced metadata search for advanced filtering
            results = await contextual_engine.enhanced_metadata_search(
                query=request.query,
                filters=filters,
                match_threshold=search_config.match_threshold,
                match_count=min(request.limit, search_config.match_count_max)
            )
        else:
            # Use standard hybrid contextual search for basic database filtering
            results = await contextual_engine.hybrid_contextual_search(
                query=request.query,
                database_filters=request.database_filters,
                content_type_filter=request.content_type_filters,
                match_threshold=search_config.match_threshold,
                match_count=min(request.limit, search_config.match_count_max)
            )
        
        # Format results for client
        search_results = []
        for result in results:
            # Handle both document and chunk results
            result_id = result.get('id', result.get('chunk_id', ''))
            content = result.get('content', '')
            
            # Truncate content for display
            if len(content) > 500:
                content = content[:500] + '...'
            
            search_results.append(SearchResult(
                id=result_id,
                title=result.get('title', ''),
                content=content,
                similarity=result.get('similarity', 0.0),
                metadata=result.get('metadata', {}),
                notion_page_id=result.get('notion_page_id', ''),
                
                # Enhanced metadata fields
                result_type=result.get('result_type'),
                chunk_context=result.get('chunk_context'),
                chunk_summary=result.get('chunk_summary'),
                document_metadata=result.get('document_metadata'),
                page_url=result.get('page_url'),
                has_adjacent_context=result.get('has_adjacent_context'),
                database_id=result.get('database_id'),
                author=result.get('author'),
                tags=result.get('tags'),
                status=result.get('status'),
                created_date=result.get('created_date'),
                modified_date=result.get('modified_date')
            ))
        
        return SearchResponse(
            results=search_results,
            query=request.query,
            total=len(search_results)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hybrid search failed: {str(e)}")