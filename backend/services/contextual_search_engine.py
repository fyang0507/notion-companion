"""
Contextual Search Engine - Enhanced RAG search with context enrichment

Implements enhanced search functionality that leverages contextual embeddings
and adjacent chunk retrieval for richer, more relevant search results.
"""

import asyncio
from typing import List, Dict, Any, Optional
import logging
from services.openai_service import OpenAIService
from database import Database
from config.model_config import VectorSearchConfig

class ContextualSearchEngine:
    """Enhanced search engine with contextual retrieval and adjacent chunk context."""
    
    def __init__(self, db: Database, openai_service: OpenAIService, search_config: Optional[VectorSearchConfig] = None):
        self.db = db
        self.openai_service = openai_service
        self.logger = logging.getLogger(__name__)
        
        # Use provided config or create default
        if search_config is None:
            from config.model_config import get_model_config
            search_config = get_model_config().get_vector_search_config()
        self.config = search_config
    
    async def contextual_search(self, 
                              query: str, 
                              database_filters: Optional[List[str]] = None, 
                              include_context: Optional[bool] = None,
                              match_threshold: Optional[float] = None,
                              match_count: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Enhanced search with contextual retrieval and adjacent chunk context.
        
        Args:
            query: Search query
            database_filters: List of database IDs to filter by
            include_context: Whether to include adjacent chunk context (uses config default if None)
            match_threshold: Similarity threshold for matches (uses config default if None)
            match_count: Maximum number of results to return (uses config default if None)
            
        Returns:
            List of enhanced search results with contextual information
        """
        try:
            # Apply config defaults for None parameters
            if include_context is None:
                include_context = self.config.enable_context_enrichment
            if match_threshold is None:
                match_threshold = self.config.match_threshold
            if match_count is None:
                match_count = self.config.match_count_default
            # 1. Generate query embedding
            embedding_response = await self.openai_service.generate_embedding(query)
            
            # 2. Search using contextual embeddings (prefer contextual over plain content)
            chunk_results = await self._search_contextual_chunks(
                embedding_response.embedding, 
                database_filters,
                match_threshold,
                match_count * 2  # Get more results for enrichment
            )
            
            # 3. Enrich results with adjacent chunks if requested
            if include_context:
                try:
                    enriched_results = await self._enrich_with_adjacent_chunks(chunk_results)
                except Exception as e:
                    self.logger.warning(f"Context enrichment failed, using basic results: {e}")
                    # Fallback to basic results with minimal enrichment structure
                    enriched_results = []
                    for result in chunk_results:
                        enriched_results.append({
                            **result,
                            'enriched_content': result.get('content', ''),
                            'context_type': 'basic',
                            'has_context_enrichment': False
                        })
            else:
                enriched_results = chunk_results
            
            # 4. Re-rank based on contextual relevance
            reranked_results = await self._rerank_with_context(query, enriched_results)
            
            # 5. Limit to requested count
            final_results = reranked_results[:match_count]
            
            self.logger.info(f"Contextual search for '{query}' returned {len(final_results)} results")
            return final_results
            
        except Exception as e:
            self.logger.error(f"Error in contextual search for '{query}': {str(e)}")
            # Fallback to basic search
            return await self._fallback_basic_search(query, database_filters, match_threshold, match_count)
    
    async def _search_contextual_chunks(self, 
                                      query_embedding: List[float], 
                                      database_filters: Optional[List[str]] = None,
                                      match_threshold: Optional[float] = None,
                                      match_count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search using contextual embeddings with enhanced SQL function."""
        try:
            # Apply config defaults
            if match_threshold is None:
                match_threshold = self.config.match_threshold
            if match_count is None:
                match_count = self.config.match_count_default * 2  # Get more for enrichment
            
            # Use the enhanced match_contextual_chunks function
            response = self.db.client.rpc('match_contextual_chunks', {
                'query_embedding': query_embedding,
                'database_filter': database_filters,
                'match_threshold': match_threshold,
                'match_count': match_count
            }).execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            self.logger.error(f"Error in contextual chunk search: {str(e)}")
            # Fallback to basic chunk search
            return await self._fallback_chunk_search(query_embedding, database_filters, match_threshold, match_count)
    
    async def _enrich_with_adjacent_chunks(self, chunk_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Retrieve adjacent chunks for context enrichment."""
        enriched_results = []
        
        for result in chunk_results:
            try:
                chunk_id = result['chunk_id']
                
                # Get chunk with adjacent context using the SQL function
                enriched_response = self.db.client.rpc('get_chunk_with_context', {
                    'chunk_id_param': chunk_id,
                    'include_adjacent': True
                }).execute()
                
                if enriched_response.data and len(enriched_response.data) > 0:
                    context_data = enriched_response.data[0]
                    
                    # Combine main chunk with adjacent context
                    enriched_content = self._combine_chunk_context(context_data)
                    
                    enriched_results.append({
                        **result,
                        'enriched_content': enriched_content,
                        'context_type': 'adjacent_enriched',
                        'adjacent_chunks': {
                            'prev': context_data.get('prev_chunk'),
                            'next': context_data.get('next_chunk')
                        },
                        'has_context_enrichment': True
                    })
                else:
                    # No adjacent context available
                    enriched_results.append({
                        **result,
                        'enriched_content': result.get('content', ''),
                        'context_type': 'standalone',
                        'has_context_enrichment': False
                    })
                    
            except Exception as e:
                self.logger.warning(f"Failed to enrich chunk {result.get('chunk_id')}: {str(e)}")
                # Include result without enrichment
                enriched_results.append({
                    **result,
                    'enriched_content': result.get('content', ''),
                    'context_type': 'error',
                    'has_context_enrichment': False
                })
        
        return enriched_results
    
    def _combine_chunk_context(self, context_data: Dict[str, Any]) -> str:
        """Combine main chunk with adjacent chunks for richer context."""
        try:
            main_chunk = context_data['main_chunk']
            prev_chunk = context_data.get('prev_chunk')
            next_chunk = context_data.get('next_chunk')
            
            # Build contextual content
            context_parts = []
            
            # Add previous context if available
            if prev_chunk and prev_chunk.get('chunk_summary'):
                context_parts.append(f"[Previous: {prev_chunk['chunk_summary']}]")
            
            # Add the main chunk with its contextual information
            if main_chunk.get('chunk_context'):
                context_parts.append(f"[Context: {main_chunk['chunk_context']}]")
            
            # Add the main chunk content
            context_parts.append(main_chunk['content'])
            
            # Add next context if available
            if next_chunk and next_chunk.get('chunk_summary'):
                context_parts.append(f"[Following: {next_chunk['chunk_summary']}]")
            
            return '\n\n'.join(context_parts)
            
        except Exception as e:
            self.logger.warning(f"Error combining chunk context: {str(e)}")
            # Fallback to main chunk content only
            main_chunk = context_data.get('main_chunk', {})
            return main_chunk.get('content', '')
    
    async def _rerank_with_context(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Re-rank results based on contextual relevance."""
        try:
            # For now, use a simple scoring approach
            # In the future, this could use a cross-encoder model for better reranking
            
            scored_results = []
            for result in results:
                base_score = result.get('combined_score', result.get('contextual_similarity', 0.0))
                
                # Boost score for results with contextual information (using config)
                context_boost = 0.0
                if result.get('chunk_context'):
                    context_boost += self.config.context_boost_factor
                if result.get('chunk_summary'):
                    context_boost += self.config.summary_boost_factor
                if result.get('has_context_enrichment'):
                    context_boost += self.config.context_boost_factor / 2  # Half boost for enrichment
                
                # Boost score for results with section information
                if result.get('document_section'):
                    context_boost += self.config.section_boost_factor
                
                final_score = base_score + context_boost
                
                scored_results.append({
                    **result,
                    'final_score': final_score,
                    'context_boost': context_boost
                })
            
            # Sort by final score
            scored_results.sort(key=lambda x: x['final_score'], reverse=True)
            return scored_results
            
        except Exception as e:
            self.logger.warning(f"Error in reranking: {str(e)}")
            return results
    
    async def _fallback_basic_search(self, 
                                   query: str, 
                                   database_filters: Optional[List[str]] = None,
                                   match_threshold: Optional[float] = None,
                                   match_count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fallback to basic search if contextual search fails."""
        try:
            # Apply config defaults
            if match_threshold is None:
                match_threshold = self.config.match_threshold
            if match_count is None:
                match_count = self.config.match_count_default
            
            # Generate embedding for basic search
            embedding_response = await self.openai_service.generate_embedding(query)
            
            # Use basic chunk search
            results = await self._fallback_chunk_search(
                embedding_response.embedding, 
                database_filters, 
                match_threshold, 
                match_count
            )
            
            # Convert to expected format
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'chunk_id': result.get('chunk_id'),
                    'content': result.get('content', ''),
                    'chunk_context': '',
                    'chunk_summary': '',
                    'document_section': '',
                    'contextual_similarity': 0.0,
                    'content_similarity': result.get('similarity', 0.0),
                    'combined_score': result.get('similarity', 0.0),
                    'document_id': result.get('document_id'),
                    'title': result.get('title', ''),
                    'notion_page_id': result.get('notion_page_id', ''),
                    'page_url': result.get('page_url', ''),
                    'chunk_index': result.get('chunk_order', 0),
                    'enriched_content': result.get('content', ''),
                    'context_type': 'fallback',
                    'has_context_enrichment': False
                })
            
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"Fallback search also failed: {str(e)}")
            return []
    
    async def _fallback_chunk_search(self, 
                                   query_embedding: List[float], 
                                   database_filters: Optional[List[str]] = None,
                                   match_threshold: Optional[float] = None,
                                   match_count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fallback chunk search using basic match_chunks function."""
        try:
            # Apply config defaults
            if match_threshold is None:
                match_threshold = self.config.match_threshold
            if match_count is None:
                match_count = self.config.match_count_default
            
            response = self.db.client.rpc('match_chunks', {
                'query_embedding': query_embedding,
                'database_filter': database_filters,
                'match_threshold': match_threshold,
                'match_count': match_count
            }).execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            self.logger.error(f"Basic chunk search failed: {str(e)}")
            return []
    
    async def hybrid_contextual_search(self, 
                                     query: str,
                                     database_filters: Optional[List[str]] = None,
                                     content_type_filter: Optional[List[str]] = None,
                                     match_threshold: Optional[float] = None,
                                     match_count: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining documents and contextual chunks.
        
        Args:
            query: Search query
            database_filters: Database IDs to filter by
            content_type_filter: Content types to filter by
            match_threshold: Similarity threshold (uses config default if None)
            match_count: Maximum results to return (uses config default if None)
            
        Returns:
            Combined results from documents and contextual chunks
        """
        try:
            # Apply config defaults
            if match_threshold is None:
                match_threshold = self.config.match_threshold
            if match_count is None:
                match_count = self.config.match_count_default
            # Generate query embedding
            embedding_response = await self.openai_service.generate_embedding(query)
            
            # Use the enhanced hybrid_contextual_search function
            response = self.db.client.rpc('hybrid_contextual_search', {
                'query_embedding': embedding_response.embedding,
                'database_filter': database_filters,
                'content_type_filter': content_type_filter,
                'match_threshold': match_threshold,
                'match_count': match_count,
                'include_context': True
            }).execute()
            
            results = response.data if response.data else []
            
            self.logger.info(f"Hybrid contextual search for '{query}' returned {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in hybrid contextual search: {str(e)}")
            # Fallback to regular contextual search
            return await self.contextual_search(query, database_filters, True, match_threshold, match_count)
    
    async def enhanced_metadata_search(self, 
                                     query: str,
                                     filters: Dict[str, Any],
                                     match_threshold: Optional[float] = None,
                                     match_count: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Enhanced search with comprehensive metadata filtering support.
        
        Args:
            query: Search query
            filters: Dictionary containing all filter parameters
            match_threshold: Similarity threshold (uses config default if None)
            match_count: Maximum results to return (uses config default if None)
            
        Returns:
            Search results with enhanced metadata filtering
        """
        try:
            # Apply config defaults
            if match_threshold is None:
                match_threshold = self.config.match_threshold
            if match_count is None:
                match_count = self.config.match_count_default
                
            # Generate query embedding
            embedding_response = await self.openai_service.generate_embedding(query)
            
            # Prepare parameters for the enhanced_metadata_search function
            search_params = {
                'query_embedding': embedding_response.embedding,
                'match_threshold': match_threshold,
                'match_count': match_count
            }
            
            # Add filter parameters
            search_params.update(filters)
            
            # Use the enhanced metadata search function
            response = self.db.client.rpc('enhanced_metadata_search', search_params).execute()
            
            results = response.data if response.data else []
            
            self.logger.info(f"Enhanced metadata search for '{query}' with filters returned {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in enhanced metadata search: {str(e)}")
            # Fallback to basic contextual search
            database_filters = filters.get('database_filter')
            return await self.contextual_search(query, database_filters, True, match_threshold, match_count)