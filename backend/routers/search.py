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
    
    # Custom metadata filters
    if request.metadata_filters:
        metadata_filters = {}
        for filter_item in request.metadata_filters:
            if filter_item.operator == 'equals':
                metadata_filters[filter_item.field_name] = filter_item.values[0] if filter_item.values else None
            elif filter_item.operator == 'in':
                metadata_filters[filter_item.field_name] = filter_item.values
            # Add more operators as needed
        if metadata_filters:
            filters['metadata_filters'] = metadata_filters
    
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