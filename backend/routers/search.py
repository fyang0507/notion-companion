from fastapi import APIRouter, HTTPException
from database import get_db
from services.openai_service import get_openai_service
from services.contextual_search_engine import ContextualSearchEngine
from models import SearchRequest, SearchResponse, SearchResult
from config.model_config import get_model_config
from typing import Dict, Any, List

router = APIRouter()

def _prepare_enhanced_search_filters(request: SearchRequest) -> Dict[str, Any]:
    """Prepare filter parameters for enhanced metadata search."""
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
    
    # Custom metadata filters with range processing
    if request.metadata_filters:
        metadata_filters = {}
        for filter_item in request.metadata_filters:
            if filter_item.operator == 'equals':
                metadata_filters[filter_item.field_name] = filter_item.values[0] if filter_item.values else None
            elif filter_item.operator == 'in':
                metadata_filters[filter_item.field_name] = filter_item.values
            # Add more operators as needed
        
        if metadata_filters:
            # Process metadata filters to handle number and date ranges
            processed_filters = _process_metadata_filters(metadata_filters)
            
            # Build SQL conditions for complex filters
            query_conditions = _build_metadata_query_conditions(processed_filters)
            
            if query_conditions:
                filters['metadata_query_conditions'] = query_conditions
            
            # Also keep the processed filters for the database function
            filters['metadata_filters'] = processed_filters
    
    return filters

def _process_metadata_filters(metadata_filters: Dict[str, Any]) -> Dict[str, Any]:
    """Process metadata filters to handle special cases like date and number ranges."""
    processed_filters = {}
    
    for field_name, values in metadata_filters.items():
        if not values:
            continue
            
        # Handle single value (backward compatibility)
        if isinstance(values, str):
            values = [values]
        elif not isinstance(values, list):
            values = [str(values)]
        
        # Process each value to handle special formats
        processed_values = []
        range_conditions = {}
        
        for value in values:
            str_value = str(value)
            
            # Handle date ranges
            if str_value.startswith('from:'):
                range_conditions['date_from'] = str_value[5:]
            elif str_value.startswith('to:'):
                range_conditions['date_to'] = str_value[3:]
            # Handle number ranges
            elif str_value.startswith('min:'):
                range_conditions['number_min'] = float(str_value[4:])
            elif str_value.startswith('max:'):
                range_conditions['number_max'] = float(str_value[4:])
            else:
                processed_values.append(str_value)
        
        # Store processed values and range conditions
        if processed_values:
            processed_filters[field_name] = processed_values
        if range_conditions:
            processed_filters[f"{field_name}_range"] = range_conditions
    
    return processed_filters

def _build_metadata_query_conditions(processed_filters: Dict[str, Any]) -> List[str]:
    """Build PostgreSQL query conditions for metadata filters."""
    conditions = []
    
    for field_name, values in processed_filters.items():
        if field_name.endswith('_range'):
            # Handle range conditions
            base_field = field_name[:-6]  # Remove '_range' suffix
            range_conditions = values
            
            if 'date_from' in range_conditions:
                conditions.append(f"(dm.extracted_fields->>'{base_field}')::date >= '{range_conditions['date_from']}'")
            if 'date_to' in range_conditions:
                conditions.append(f"(dm.extracted_fields->>'{base_field}')::date <= '{range_conditions['date_to']}'")
            if 'number_min' in range_conditions:
                conditions.append(f"(dm.extracted_fields->>'{base_field}')::numeric >= {range_conditions['number_min']}")
            if 'number_max' in range_conditions:
                conditions.append(f"(dm.extracted_fields->>'{base_field}')::numeric <= {range_conditions['number_max']}")
        else:
            # Handle exact value matches
            if len(values) == 1:
                # Single value - handle both direct values and array membership
                value = values[0]
                conditions.append(f"""(
                    dm.extracted_fields->>'{field_name}' = '{value}' OR
                    dm.extracted_fields->'{field_name}' ? '{value}'
                )""")
            else:
                # Multiple values - use IN clause and array membership
                values_str = "','".join(values)
                conditions.append(f"""(
                    dm.extracted_fields->>'{field_name}' IN ('{values_str}') OR
                    dm.extracted_fields->'{field_name}' ?| ARRAY['{values_str}']
                )""")
    
    return conditions

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
            'metadata_filters', 'author_filter', 'tag_filter', 'status_filter', 'date_range_filter'
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
            'metadata_filters', 'author_filter', 'tag_filter', 'status_filter', 'date_range_filter'
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