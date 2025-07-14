"""
Unified Search API - Rebuilt for Agentic RAG Pipeline

Single clean search endpoint that orchestrates the complete RAG pipeline (steps 1-5):
1. Query embedding generation
2. Metadata filtering preparation  
3. Blended filter + embedding search (70/30 contextual weighting)
4. Adjacent chunk enrichment
5. Reranking

Eliminates all redundant endpoints and consolidates search logic.
"""

from fastapi import APIRouter, HTTPException
from database import get_db
from services.openai_service import get_openai_service
from services.rag_search_service import RAGSearchService, FilterProcessor
from models import SearchRequest, SearchResponse, SearchResult
from config.model_config import get_model_config
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/search", response_model=SearchResponse)
async def unified_search_endpoint(request: SearchRequest):
    """
    Unified search endpoint implementing complete RAG pipeline (steps 1-5).
    
    Supports:
    - Basic database filtering
    - Complex metadata filtering
    - 70/30 contextual weighting (existing match_contextual_chunks)
    - Adjacent chunk enrichment
    - Context-aware reranking
    
    Replaces previous redundant /search and /search/hybrid endpoints.
    """
    try:
        # Initialize services
        db = get_db()
        openai_service = get_openai_service()
        model_config = get_model_config()
        search_config = model_config.get_vector_search_config()
        
        # Initialize unified RAG search service
        rag_service = RAGSearchService(db, openai_service, search_config)
        
        # Step 2: Prepare filters using consolidated logic
        filters = FilterProcessor.prepare_filters(request)
        
        # Execute complete RAG pipeline (steps 1-5)
        rag_results = await rag_service.search_and_retrieve(
            query=request.query,
            filters=filters,
            match_threshold=search_config.match_threshold,
            match_count=min(request.limit, search_config.match_count_max)
        )
        
        # Format results for client
        search_results = []
        for result in rag_results['chunks']:
            # Use enriched content if available, otherwise fall back to regular content
            display_content = result.get('enriched_content', result.get('content', ''))
            
            # Truncate very long content for display
            if len(display_content) > 500:
                display_content = display_content[:500] + '...'
            
            # Handle different result ID formats
            result_id = result.get('chunk_id', result.get('id', ''))
            
            search_results.append(SearchResult(
                id=result_id,
                title=result.get('title', ''),
                content=display_content,
                similarity=result.get('final_score', result.get('combined_score', result.get('similarity', 0.0))),
                metadata=result.get('metadata', {}),
                notion_page_id=result.get('notion_page_id', ''),
                
                # Enhanced metadata fields
                result_type=result.get('result_type', 'chunk'),
                chunk_context=result.get('chunk_context'),
                chunk_summary=result.get('chunk_summary'),
                document_metadata=result.get('document_metadata'),
                page_url=result.get('page_url'),
                has_adjacent_context=result.get('has_adjacent_context', False),
                database_id=result.get('database_id'),
                author=result.get('author'),
                tags=result.get('tags'),
                status=result.get('status'),
                created_date=result.get('created_date'),
                modified_date=result.get('modified_date')
            ))
        
        # Add search metadata to response
        response = SearchResponse(
            results=search_results,
            query=request.query,
            total=len(search_results)
        )
        
        # Log search execution details
        search_metadata = rag_results['search_metadata']
        logger.info(f"Unified search completed", extra={
            'query': request.query,
            'results_count': len(search_results),
            'execution_time_ms': search_metadata['execution_time_ms'],
            'search_strategy': search_metadata['search_strategy'],
            'total_found': search_metadata['total_found'],
            'has_filters': bool(filters)
        })
        
        return response
        
    except Exception as e:
        logger.error(f"Unified search failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

# TODO: Add evaluation endpoint for <question, answer> datasets
# @router.post("/search/evaluate", response_model=EvaluationResponse)
# async def evaluation_search_endpoint(request: EvaluationRequest):
#     """
#     Evaluation-specific search endpoint for testing with <question, answer> pairs.
#     
#     Features:
#     - Returns raw chunks without UI formatting
#     - Includes detailed search metadata for evaluation
#     - Supports batch evaluation requests
#     """
#     pass