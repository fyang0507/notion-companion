from fastapi import APIRouter, HTTPException
from database import get_db
from services.openai_service import get_openai_service
from services.contextual_search_engine import ContextualSearchEngine
from models import SearchRequest, SearchResponse, SearchResult

router = APIRouter()

@router.post("/search", response_model=SearchResponse)
async def enhanced_search_endpoint(request: SearchRequest):
    """Enhanced search endpoint with contextual retrieval and context enrichment."""
    try:
        db = get_db()
        openai_service = get_openai_service()
        
        # Initialize contextual search engine
        contextual_engine = ContextualSearchEngine(db, openai_service)
        
        # Use enhanced contextual search
        results = await contextual_engine.contextual_search(
            query=request.query,
            database_filters=request.database_filters,
            include_context=True,  # Enable context enrichment
            match_threshold=0.7,
            match_count=request.limit
        )
        
        # Format results for client
        search_results = []
        for result in results:
            # Use enriched content if available, otherwise fall back to regular content
            display_content = result.get('enriched_content', result.get('content', ''))
            
            # Truncate very long content for display
            if len(display_content) > 500:
                display_content = display_content[:500] + '...'
            
            search_results.append(SearchResult(
                id=result['chunk_id'],
                title=result['title'],
                content=display_content,
                similarity=result.get('final_score', result.get('combined_score', 0.0)),
                metadata={
                    'chunk_context': result.get('chunk_context', ''),
                    'chunk_summary': result.get('chunk_summary', ''),
                    'document_section': result.get('document_section', ''),
                    'context_type': result.get('context_type', 'standard'),
                    'has_context_enrichment': result.get('has_context_enrichment', False),
                    'chunk_index': result.get('chunk_index', 0),
                    'contextual_similarity': result.get('contextual_similarity', 0.0),
                    'content_similarity': result.get('content_similarity', 0.0),
                    'type': 'contextual_chunk'
                },
                notion_page_id=result['notion_page_id']
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
    """Hybrid search endpoint combining documents and contextual chunks."""
    try:
        db = get_db()
        openai_service = get_openai_service()
        
        # Initialize contextual search engine
        contextual_engine = ContextualSearchEngine(db, openai_service)
        
        # Use hybrid contextual search
        results = await contextual_engine.hybrid_contextual_search(
            query=request.query,
            database_filters=request.database_filters,
            content_type_filter=None,  # Could be added to SearchRequest in future
            match_threshold=0.7,
            match_count=request.limit
        )
        
        # Format results for client
        search_results = []
        for result in results:
            # Handle both document and chunk results
            result_id = result.get('id')
            content = result.get('content', '')
            
            # Truncate content for display
            if len(content) > 500:
                content = content[:500] + '...'
            
            search_results.append(SearchResult(
                id=result_id,
                title=result['title'],
                content=content,
                similarity=result.get('similarity', 0.0),
                metadata={
                    'result_type': result.get('result_type', 'unknown'),
                    'chunk_context': result.get('chunk_context', ''),
                    'chunk_summary': result.get('chunk_summary', ''),
                    'has_adjacent_context': result.get('has_adjacent_context', False),
                    'type': 'hybrid_result'
                },
                notion_page_id=result['notion_page_id']
            ))
        
        return SearchResponse(
            results=search_results,
            query=request.query,
            total=len(search_results)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hybrid search failed: {str(e)}")