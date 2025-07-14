"""
Unified RAG Search Service - Steps 1-5 of Agentic RAG Pipeline

Orchestrates the complete search and retrieval pipeline:
1. Query embedding generation
2. Metadata filtering preparation  
3. Blended filter + embedding search (70/30 contextual weighting)
4. Adjacent chunk enrichment (placeholder for advanced features)
5. Reranking (placeholder for advanced techniques)
"""

import asyncio
from typing import List, Dict, Any, Optional, Union
import logging
import time
from pathlib import Path
import tomllib

from database import Database
from services.openai_service import OpenAIService
from config.model_config import VectorSearchConfig
from models import SearchRequest, ChatRequest

class RAGSearchService:
    """Unified search service implementing steps 1-5 of agentic RAG pipeline."""
    
    def __init__(self, db: Database, openai_service: OpenAIService, search_config: VectorSearchConfig):
        self.db = db
        self.openai_service = openai_service
        self.config = search_config
        self.logger = logging.getLogger(__name__)
    
    async def search_and_retrieve(self, 
                                 query: str,
                                 filters: Dict[str, Any],
                                 match_threshold: Optional[float] = None,
                                 match_count: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute complete RAG search pipeline (steps 1-5).
        
        Args:
            query: User query string
            filters: Processed filter dictionary
            match_threshold: Similarity threshold (uses config default if None)
            match_count: Maximum results to return (uses config default if None)
            
        Returns:
            {
                'chunks': List[Dict] - Final ranked chunks
                'query_embedding': List[float] - Query embedding for potential reuse
                'search_metadata': Dict - Search execution metadata
            }
        """
        start_time = time.time()
        
        # Apply config defaults
        if match_threshold is None:
            match_threshold = self.config.match_threshold
        if match_count is None:
            match_count = self.config.match_count_default
        
        try:
            # Step 1: Generate query embedding
            self.logger.info(f"Step 1: Generating query embedding")
            embedding_response = await self.openai_service.generate_embedding(query)
            
            # Step 2: Metadata filtering (already prepared in filters)
            self.logger.info(f"Step 2: Applying metadata filters")
            # Filters are already processed by FilterProcessor
            
            # Step 3: Blended filter + embedding search (70/30 contextual weighting)
            self.logger.info(f"Step 3: Executing blended search with 70/30 contextual weighting")
            chunks = await self._execute_contextual_search(
                embedding_response.embedding,
                filters,
                match_threshold,
                match_count * 2  # Get more results for enrichment
            )
            
            # Step 4: Adjacent chunk enrichment
            self.logger.info(f"Step 4: Enriching with adjacent chunks")
            enriched_chunks = await self._enrich_with_adjacent_chunks(chunks)
            
            # Step 5: Reranking
            self.logger.info(f"Step 5: Reranking chunks")
            final_chunks = await self._rerank_chunks(query, enriched_chunks)
            
            # Limit to requested count
            final_chunks = final_chunks[:match_count]
            
            execution_time = (time.time() - start_time) * 1000
            
            return {
                'chunks': final_chunks,
                'query_embedding': embedding_response.embedding,
                'search_metadata': {
                    'execution_time_ms': execution_time,
                    'total_found': len(chunks),
                    'after_enrichment': len(enriched_chunks),
                    'final_returned': len(final_chunks),
                    'match_threshold': match_threshold,
                    'search_strategy': 'contextual_70_30_weighting'
                }
            }
            
        except Exception as e:
            self.logger.error(f"RAG search pipeline failed: {str(e)}")
            raise
    
    async def _execute_contextual_search(self, 
                                       query_embedding: List[float],
                                       filters: Dict[str, Any],
                                       match_threshold: float,
                                       match_count: int) -> List[Dict[str, Any]]:
        """
        Step 3: Execute blended filter + embedding search using 70/30 contextual weighting.
        
        Uses existing match_contextual_chunks SQL function which implements:
        - 70% weight on contextual_embedding (document summary + chunk content)
        - 30% weight on embedding (raw chunk content)
        """
        try:
            # Determine if we need enhanced metadata search or basic contextual search
            has_advanced_filters = self._has_advanced_filters(filters)
            
            if has_advanced_filters:
                # Use enhanced_metadata_search for complex filtering with typed filters
                search_params = {
                    'query_embedding': query_embedding,
                    'database_filter': filters.get('database_filter'),
                    'match_threshold': match_threshold,
                    'match_count': match_count
                }
                
                # Add typed filters directly as parameters
                for filter_key in ['content_type_filter', 'date_range_filter', 'text_filter', 
                                   'select_filter', 'tag_filter', 'number_filter', 'checkbox_filter']:
                    if filter_key in filters and filters[filter_key]:
                        search_params[filter_key] = filters[filter_key]
                
                response = self.db.client.rpc('enhanced_metadata_search', search_params).execute()
                self.logger.info(f"Used enhanced_metadata_search with typed filters")
            else:
                # Use basic match_contextual_chunks for simple database filtering
                response = self.db.client.rpc('match_contextual_chunks', {
                    'query_embedding': query_embedding,
                    'database_filter': filters.get('database_filter'),
                    'match_threshold': match_threshold,
                    'match_count': match_count
                }).execute()
                self.logger.info(f"Used match_contextual_chunks with basic filtering")
            
            return response.data if response.data else []
            
        except Exception as e:
            self.logger.error(f"Error in contextual search: {str(e)}")
            raise
    
    def _has_advanced_filters(self, filters: Dict[str, Any]) -> bool:
        """Check if advanced metadata filters are present."""
        advanced_filter_keys = [
            'text_filter', 'number_filter', 'select_filter', 'checkbox_filter',
            'tag_filter', 'date_range_filter'
        ]
        return any(key in filters for key in advanced_filter_keys)
    
    async def _enrich_with_adjacent_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Step 4: Adjacent chunk enrichment using existing get_chunk_with_context.
        
        TODO: Future enhancements:
        - Configurable context window size
        - Semantic similarity-based context selection
        - Cross-document context retrieval
        - Dynamic context length based on query complexity
        """
        if not self.config.enable_context_enrichment:
            self.logger.info("Context enrichment disabled by configuration")
            return chunks
        
        enriched_chunks = []
        
        for chunk in chunks:
            try:
                chunk_id = chunk.get('chunk_id', chunk.get('id'))
                if not chunk_id:
                    enriched_chunks.append(chunk)
                    continue
                
                # Use existing get_chunk_with_context SQL function
                context_response = self.db.client.rpc('get_chunk_with_context', {
                    'chunk_id_param': chunk_id,
                    'include_adjacent': True
                }).execute()
                
                if context_response.data and len(context_response.data) > 0:
                    context_data = context_response.data[0]
                    
                    # Combine contexts using existing logic
                    enriched_content = self._combine_chunk_contexts(context_data)
                    
                    enriched_chunks.append({
                        **chunk,
                        'enriched_content': enriched_content,
                        'context_type': 'adjacent_enriched',
                        'has_adjacent_context': True,
                        'adjacent_chunks': {
                            'prev': context_data.get('prev_chunk'),
                            'next': context_data.get('next_chunk')
                        }
                    })
                else:
                    enriched_chunks.append({
                        **chunk,
                        'enriched_content': chunk.get('content', ''),
                        'context_type': 'standalone',
                        'has_adjacent_context': False
                    })
                    
            except Exception as e:
                self.logger.warning(f"Failed to enrich chunk {chunk.get('chunk_id', 'unknown')}: {str(e)}")
                enriched_chunks.append({
                    **chunk,
                    'enriched_content': chunk.get('content', ''),
                    'context_type': 'error',
                    'has_adjacent_context': False
                })
        
        return enriched_chunks
    
    def _combine_chunk_contexts(self, context_data: Dict[str, Any]) -> str:
        """Combine main chunk with adjacent chunks for richer context."""
        try:
            main_chunk = context_data['main_chunk']
            prev_chunk = context_data.get('prev_chunk')
            next_chunk = context_data.get('next_chunk')
            
            context_parts = []
            
            # Add previous context summary
            if prev_chunk and prev_chunk.get('chunk_summary'):
                context_parts.append(f"[Previous: {prev_chunk['chunk_summary']}]")
            
            # Add main chunk context
            if main_chunk.get('chunk_context'):
                context_parts.append(f"[Context: {main_chunk['chunk_context']}]")
            
            # Add main chunk content
            context_parts.append(main_chunk['content'])
            
            # Add next context summary
            if next_chunk and next_chunk.get('chunk_summary'):
                context_parts.append(f"[Following: {next_chunk['chunk_summary']}]")
            
            return '\n\n'.join(context_parts)
            
        except Exception as e:
            self.logger.warning(f"Error combining contexts: {str(e)}")
            main_chunk = context_data.get('main_chunk', {})
            return main_chunk.get('content', '')
    
    async def _rerank_chunks(self, query: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Step 5: Reranking placeholder - returns chunks as-is for now.
        
        TODO: Future advanced reranking techniques:
        - Cross-encoder reranking models
        - Query-specific relevance scoring
        - Diversity-aware reranking (MMR)
        - User preference learning
        - Temporal relevance boosting
        - Domain-specific relevance models
        """
        # For now, return chunks as-is (already sorted by 70/30 contextual weighting from SQL)
        # Advanced reranking will be implemented in future iterations
        self.logger.info(f"Returning {len(chunks)} chunks without additional reranking")
        return chunks


class FilterProcessor:
    """Shared filter preparation logic consolidated from search.py and chat.py."""
    
    @staticmethod
    def _load_database_configurations() -> List[Dict[str, Any]]:
        """Load all database configurations from databases.toml."""
        config_path = Path(__file__).parent.parent / 'config' / 'databases.toml'
        
        try:
            with open(config_path, 'rb') as f:
                config_data = tomllib.load(f)
            return config_data.get('databases', [])
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to load database configurations: {str(e)}")
            return []

    @staticmethod
    def _get_field_type_mapping() -> Dict[str, str]:
        """Create a mapping of field names to their configured types."""
        field_type_mapping = {}
        
        configurations = FilterProcessor._load_database_configurations()
        for config in configurations:
            metadata_config = config.get('metadata', {})
            for field_name, field_config in metadata_config.items():
                field_type = field_config.get('type', 'text')
                field_type_mapping[field_name] = field_type
        
        return field_type_mapping

    @staticmethod
    def prepare_filters(request: Union[SearchRequest, ChatRequest]) -> Dict[str, Any]:
        """
        Unified filter preparation logic (Step 2 of RAG pipeline).
        
        Maps configured field types to SQL function parameters:
        - text, rich_text → text_filter jsonb
        - number → number_filter jsonb  
        - select, status → select_filter jsonb
        - multi_select → tag_filter text[] (legacy compatibility)
        - date → date_range_filter jsonb
        - checkbox → checkbox_filter jsonb
        """
        filters = {}
        
        # Basic database filter
        if getattr(request, 'database_filters', None):
            filters['database_filter'] = request.database_filters
        
        # Content type filter (if supported)
        if getattr(request, 'content_type_filters', None):
            filters['content_type_filter'] = request.content_type_filters
        
        # Date range filter (global date filtering)
        if getattr(request, 'date_range_filter', None):
            date_range = {}
            if request.date_range_filter.from_date:
                date_range['from'] = request.date_range_filter.from_date.isoformat()
            if request.date_range_filter.to_date:
                date_range['to'] = request.date_range_filter.to_date.isoformat()
            if date_range:
                filters['date_range_filter'] = date_range
        
        # Metadata filters based on configured field types
        if getattr(request, 'metadata_filters', None):
            field_type_mapping = FilterProcessor._get_field_type_mapping()
            
            # Group filters for SQL function parameters (mix of old and new style)
            text_filters = {}        # text, rich_text fields → text_filter jsonb
            number_filters = {}      # number fields → number_filter jsonb
            select_filters = {}      # select, status fields → select_filter jsonb
            checkbox_filters = {}    # checkbox fields → checkbox_filter jsonb
            
            # Special handling for multi_select fields that map to old-style tag_filter
            tag_filters = []         # multi_select fields → tag_filter text[]
            
            # Date range handling
            date_range_filter = {}   # date fields → date_range_filter jsonb
            
            for filter_item in request.metadata_filters:
                field_name = filter_item.field_name
                operator = filter_item.operator
                values = filter_item.values
                
                field_type = field_type_mapping.get(field_name)
                if not field_type:
                    # Skip unknown fields
                    continue
                
                # Route to appropriate filter group based on configured field type
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
                    # Map multi_select to tag_filter for existing SQL compatibility
                    if operator in ['equals', 'in'] and values:
                        tag_filters.extend(values if operator == 'in' else [values[0]])
                        
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
                    # Map date fields to date_range_filter
                    if operator == 'range' and values:
                        for value in values:
                            str_value = str(value)
                            if str_value.startswith('from:'):
                                date_range_filter['from'] = str_value[5:]
                            elif str_value.startswith('to:'):
                                date_range_filter['to'] = str_value[3:]
                    elif operator == 'equals' and values:
                        # Single date becomes a range for that day
                        date_str = str(values[0])
                        date_range_filter['from'] = date_str
                        date_range_filter['to'] = date_str
            
            # Add non-empty filter groups to main filters (matching SQL function parameters)
            if text_filters:
                filters['text_filter'] = text_filters
            if number_filters:
                filters['number_filter'] = number_filters
            if select_filters:
                filters['select_filter'] = select_filters
            if checkbox_filters:
                filters['checkbox_filter'] = checkbox_filters
            if tag_filters:
                filters['tag_filter'] = tag_filters
            if date_range_filter:
                filters['date_range_filter'] = date_range_filter
        
        return filters 