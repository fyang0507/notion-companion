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
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from storage.database import get_db
from ingestion.services.openai_service import get_openai_service
from rag.services.rag_search_service import RAGSearchService, FilterProcessor
from api.models.models import SearchRequest, SearchResponse, SearchResult
from shared.config.model_config import get_model_config
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
        
        # Steps 1-5: Execute complete search pipeline
        search_result = await rag_service.search_and_retrieve(
            query=request.query,
            filters=filters,
            match_count=request.limit
        )
        
        # Extract chunks from search result
        chunks = search_result.get('chunks', [])
        
        # Convert chunks to SearchResult format
        results = []
        for chunk in chunks:
            results.append(SearchResult(
                id=chunk.get('id', chunk.get('chunk_id', '')),
                title=chunk.get('title', ''),
                content=chunk.get('enriched_content', chunk.get('content', '')),
                similarity=chunk.get('similarity', 0.0),
                metadata=chunk.get('metadata', {}),
                notion_page_id=chunk.get('notion_page_id', ''),
                result_type='chunk',
                chunk_context=chunk.get('chunk_context'),
                chunk_summary=chunk.get('chunk_summary'),
                document_metadata=chunk.get('document_metadata'),
                page_url=chunk.get('page_url'),
                has_adjacent_context=chunk.get('has_adjacent_context', False),
                database_id=chunk.get('database_id')
            ))
        
        return SearchResponse(
            results=results,
            query=request.query,
            total=len(results)
        )
        
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.post("/search/hybrid", response_model=SearchResponse)
async def hybrid_search_endpoint(request: SearchRequest):
    """
    Hybrid search endpoint for backward compatibility.
    
    This endpoint combines document and chunk search results.
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
        
        # Execute complete search pipeline
        search_result = await rag_service.search_and_retrieve(
            query=request.query,
            filters=filters,
            match_count=request.limit
        )
        
        # Extract chunks from search result
        chunks = search_result.get('chunks', [])
        
        # Convert chunks to SearchResult format
        results = []
        for chunk in chunks:
            results.append(SearchResult(
                id=chunk.get('id', chunk.get('chunk_id', '')),
                title=chunk.get('title', ''),
                content=chunk.get('enriched_content', chunk.get('content', '')),
                similarity=chunk.get('similarity', 0.0),
                metadata=chunk.get('metadata', {}),
                notion_page_id=chunk.get('notion_page_id', ''),
                result_type='chunk',
                chunk_context=chunk.get('chunk_context'),
                chunk_summary=chunk.get('chunk_summary'),
                document_metadata=chunk.get('document_metadata'),
                page_url=chunk.get('page_url'),
                has_adjacent_context=chunk.get('has_adjacent_context', False),
                database_id=chunk.get('database_id')
            ))
        
        return SearchResponse(
            results=results,
            query=request.query,
            total=len(results)
        )
        
    except Exception as e:
        logger.error(f"Hybrid search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Hybrid search failed: {str(e)}")