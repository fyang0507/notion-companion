"""
Basic Similarity Strategy

Simple vector similarity search strategy for benchmark experiments.
Uses basic embedding similarity without any sophisticated retrieval techniques.
"""

import logging
from typing import List, Dict, Any
from ..strategies.base_strategy import BaseRetrievalStrategy
from storage.database import Database

logger = logging.getLogger(__name__)


class BasicSimilarityStrategy(BaseRetrievalStrategy):
    """
    Basic vector similarity retrieval strategy.
    
    This strategy:
    1. Embeds the query using OpenAI
    2. Performs vector similarity search using Supabase's match_chunks function
    3. Returns top-k results based on cosine similarity
    4. No contextual enrichment or advanced filtering
    """
    
    def __init__(self, database: Database, openai_service, embedding_config: Dict[str, Any]):
        super().__init__("basic_similarity", "Basic vector similarity search using cosine distance")
        self.database = database
        self.openai_service = openai_service
        self.embedding_config = embedding_config
        logger.info(f"BasicSimilarityStrategy initialized with model: {embedding_config.get('openai', {}).get('model', 'unknown')}")
    
    async def retrieve(self, query: str, filters: Dict[str, Any], limit: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents/chunks for a query.
        This is the main retrieval interface that handles the complete flow:
        1. Generate query embedding
        2. Call retrieve_with_embedding for the actual search
        """
        logger.info(f"Performing basic similarity search for query: {query[:50]}...")
        
        # Generate query embedding using experiment-specific config
        query_embedding_response = await self.openai_service.generate_embedding(
            text=query,
            config=self.embedding_config  # Pass entire nested config dict to API
        )
        query_embedding = query_embedding_response.embedding
        
        logger.debug(f"Generated embedding for query (dimensions: {len(query_embedding)})")
        
        # Call retrieve_with_embedding with the generated embedding
        results = await self.retrieve_with_embedding(
            query_embedding=query_embedding,
            filters=filters,
            limit=limit,
            **kwargs
        )
        
        # Add search query to metadata for each result
        for result in results:
            if 'metadata' in result:
                result['metadata']['search_query'] = query
        
        return results
    
    async def retrieve_with_embedding(self, query_embedding: List[float], filters: Dict[str, Any], 
                                    limit: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents/chunks using a pre-computed embedding.
        This is a substep within retrieve() that performs the actual vector similarity search.
        """
        logger.info(f"Performing basic similarity search with pre-computed embedding (dimensions: {len(query_embedding)})")
        
        client = self.database.get_client()
        
        try:
            result = client.rpc(
                'match_chunks',
                {
                    'query_embedding': query_embedding,
                    'database_filter': filters.get('database_ids'),
                    'match_threshold': filters.get('similarity_threshold', 0.1),
                    'match_count': limit
                }
            ).execute()
            
            raw_results = result.data if result.data else []
            logger.info(f"Retrieved {len(raw_results)} results from similarity search")
            
            # Format results for consistency
            formatted_results = []
            for i, result in enumerate(raw_results):
                formatted_result = {
                    'rank': i + 1,
                    'chunk_id': result.get('chunk_id'),
                    'content': result.get('content', ''),
                    'similarity_score': result.get('similarity', 0.0),
                    'document_id': result.get('document_id'),
                    'document_title': result.get('title', ''),
                    'notion_page_id': result.get('notion_page_id'),
                    'page_url': result.get('page_url'),
                    'strategy': 'basic_similarity',
                    'metadata': {
                        'embedding_dimensions': len(query_embedding),
                        'similarity_threshold': filters.get('similarity_threshold', 0.1),
                        'database_filters': filters.get('database_ids')
                    }
                }
                formatted_results.append(formatted_result)
            
            logger.info(f"Formatted {len(formatted_results)} search results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error performing similarity search with embedding: {e}")
            raise Exception(f"Basic similarity search failed: {str(e)}")
    
    
    
    def get_strategy_name(self) -> str:
        """Return the strategy name."""
        return "basic_similarity"
    
    def get_strategy_description(self) -> str:
        """Return a description of this strategy."""
        return "Basic vector similarity search using cosine distance without contextual enrichment"


def get_basic_similarity_strategy(database: Database, openai_service, embedding_config: Dict[str, Any]) -> BasicSimilarityStrategy:
    """Factory function to create a basic similarity strategy with embedding config."""
    return BasicSimilarityStrategy(database, openai_service, embedding_config)