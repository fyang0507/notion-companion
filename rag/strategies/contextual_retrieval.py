"""
Contextual Retrieval Strategy

This strategy implements contextual retrieval with enhanced context enrichment.
It corresponds to the existing contextual search functionality in the RAG service.
"""

from typing import Dict, Any, List, Optional
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from .base_strategy import BaseRetrievalStrategy, RetrievalResult
from storage.database import Database
from ingestion.services.openai_service import OpenAIService
import logging

logger = logging.getLogger(__name__)

class ContextualRetrievalStrategy(BaseRetrievalStrategy):
    """
    Contextual retrieval strategy with enhanced context enrichment.
    
    This strategy implements:
    1. Vector similarity search using embeddings
    2. Adjacent chunk enrichment for better context
    3. Contextual re-ranking based on enhanced content
    """
    
    def __init__(self, name: str = "contextual", description: str = ""):
        if not description:
            description = "Contextual retrieval with enhanced context enrichment and adjacent chunk support"
        super().__init__(name, description)
        
        self.similarity_threshold = 0.1
        self.context_enrichment = True
        self.contextual_weight = 0.7
        self.context_boost_factor = 0.05
        
        # Services (will be injected)
        self.db: Optional[Database] = None
        self.openai_service: Optional[OpenAIService] = None
    
    def set_services(self, db: Database, openai_service: OpenAIService):
        """Set the required services."""
        self.db = db
        self.openai_service = openai_service
    
    async def retrieve(
        self, 
        query: str, 
        filters: Dict[str, Any], 
        limit: int = 10,
        **kwargs
    ) -> List[RetrievalResult]:
        """
        Retrieve using contextual strategy with query string.
        
        Args:
            query: Search query string
            filters: Dictionary of filters to apply
            limit: Maximum number of results to return
            **kwargs: Additional parameters
            
        Returns:
            List of RetrievalResult objects
        """
        if not self.openai_service:
            raise RuntimeError("OpenAI service not set. Call set_services() first.")
        
        # Generate embedding for query
        query_embedding = await self.openai_service.generate_embedding(query)
        
        # Delegate to embedding-based retrieval
        return await self.retrieve_with_embedding(
            query_embedding, filters, limit, **kwargs
        )
    
    async def retrieve_with_embedding(
        self, 
        query_embedding: List[float], 
        filters: Dict[str, Any], 
        limit: int = 10,
        **kwargs
    ) -> List[RetrievalResult]:
        """
        Retrieve using contextual strategy with pre-computed embedding.
        
        Args:
            query_embedding: Pre-computed query embedding vector
            filters: Dictionary of filters to apply
            limit: Maximum number of results to return
            **kwargs: Additional parameters
            
        Returns:
            List of RetrievalResult objects
        """
        if not self.db:
            raise RuntimeError("Database not set. Call set_services() first.")
        
        try:
            # Step 1: Basic vector similarity search
            raw_results = await self._vector_search(query_embedding, filters, limit * 2)
            
            # Step 2: Context enrichment (if enabled)
            if self.context_enrichment:
                enriched_results = await self._enrich_with_context(raw_results)
            else:
                enriched_results = raw_results
            
            # Step 3: Contextual re-ranking
            reranked_results = await self._contextual_rerank(
                enriched_results, query_embedding, limit
            )
            
            # Step 4: Convert to RetrievalResult format
            return self._format_results(reranked_results)
            
        except Exception as e:
            logger.error(f"Contextual retrieval failed: {e}")
            raise
    
    async def _vector_search(
        self, 
        query_embedding: List[float], 
        filters: Dict[str, Any], 
        limit: int
    ) -> List[Dict[str, Any]]:
        """Perform basic vector similarity search."""
        # Use the database's vector search functionality
        # This would typically call the existing match_contextual_chunks method
        
        # For now, return a mock implementation
        # In real implementation, this would call:
        # return await self.db.match_contextual_chunks(query_embedding, filters, limit, self.similarity_threshold)
        
        return []  # Mock implementation
    
    async def _enrich_with_context(
        self, 
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Enrich results with adjacent chunk context."""
        enriched_results = []
        
        for result in results:
            # Get adjacent chunks for context
            adjacent_chunks = await self._get_adjacent_chunks(result)
            
            # Combine with adjacent context
            enriched_content = self._combine_with_context(result, adjacent_chunks)
            
            # Update result with enriched content
            enriched_result = result.copy()
            enriched_result['enriched_content'] = enriched_content
            enriched_result['has_adjacent_context'] = len(adjacent_chunks) > 0
            
            enriched_results.append(enriched_result)
        
        return enriched_results
    
    async def _get_adjacent_chunks(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get adjacent chunks for context enrichment."""
        # This would implement the logic to find adjacent chunks
        # For now, return empty list
        return []
    
    def _combine_with_context(
        self, 
        result: Dict[str, Any], 
        adjacent_chunks: List[Dict[str, Any]]
    ) -> str:
        """Combine chunk with adjacent context."""
        content = result.get('content', '')
        
        # Add context from adjacent chunks
        if adjacent_chunks:
            context_parts = [chunk.get('content', '') for chunk in adjacent_chunks]
            context = ' '.join(context_parts)
            content = f"{context}\n\n{content}"
        
        return content
    
    async def _contextual_rerank(
        self, 
        results: List[Dict[str, Any]], 
        query_embedding: List[float], 
        limit: int
    ) -> List[Dict[str, Any]]:
        """Re-rank results based on contextual information."""
        for result in results:
            # Calculate contextual score boost
            base_score = result.get('similarity', 0.0)
            
            # Boost score if has adjacent context
            if result.get('has_adjacent_context', False):
                base_score += self.context_boost_factor
            
            # Apply contextual weighting
            final_score = base_score * self.contextual_weight
            result['final_score'] = final_score
        
        # Sort by final score and limit
        results.sort(key=lambda x: x.get('final_score', 0), reverse=True)
        return results[:limit]
    
    def _format_results(self, results: List[Dict[str, Any]]) -> List[RetrievalResult]:
        """Convert raw results to RetrievalResult format."""
        formatted_results = []
        
        for result in results:
            formatted_result = RetrievalResult(
                id=result.get('id', result.get('chunk_id', '')),
                title=result.get('title', ''),
                content=result.get('enriched_content', result.get('content', '')),
                score=result.get('final_score', result.get('similarity', 0.0)),
                metadata=result.get('metadata', {}),
                chunk_id=result.get('chunk_id'),
                document_id=result.get('document_id'),
                similarity=result.get('similarity')
            )
            formatted_results.append(formatted_result)
        
        return formatted_results
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters."""
        return {
            'similarity_threshold': self.similarity_threshold,
            'context_enrichment': self.context_enrichment,
            'contextual_weight': self.contextual_weight,
            'context_boost_factor': self.context_boost_factor
        }
    
    def set_parameters(self, params: Dict[str, Any]):
        """Set strategy parameters."""
        if 'similarity_threshold' in params:
            self.similarity_threshold = params['similarity_threshold']
        if 'context_enrichment' in params:
            self.context_enrichment = params['context_enrichment']
        if 'contextual_weight' in params:
            self.contextual_weight = params['contextual_weight']
        if 'context_boost_factor' in params:
            self.context_boost_factor = params['context_boost_factor'] 