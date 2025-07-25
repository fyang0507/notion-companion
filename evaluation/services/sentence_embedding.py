"""
Sentence Embedding Service

Provides batch embedding generation with in-memory caching for performance.
Storage and persistent caching is handled by the orchestrator's UnifiedCacheManager.
Uses the centralized OpenAIService for all OpenAI API interactions.
"""

import hashlib
import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


class SentenceEmbeddingCache:
    """Sentence embedding service with in-memory caching for performance during a single run"""
    
    def __init__(self, config: Dict):
        """
        Initialize embedding service with required configuration.
        
        Args:
            config: Configuration dictionary containing embeddings settings
            
        Raises:
            ValueError: If config is missing or invalid
            KeyError: If required configuration keys are missing
        """
        if not config:
            raise ValueError("Configuration is required for SentenceEmbeddingCache")
        
        if 'embeddings' not in config:
            raise ValueError("Configuration must contain 'embeddings' section")
        
        embeddings_config = config['embeddings']
        
        # Extract required configuration values (fail hard if missing)
        try:
            self.batch_size = embeddings_config['batch_size']
            # Validate that we have openai section for the service
            if 'openai' not in embeddings_config:
                raise KeyError("Missing 'openai' section in embeddings configuration")
            self.embedding_model = embeddings_config['openai']['model']
        except KeyError as e:
            raise KeyError(f"Missing required configuration key in embeddings section: {e}")
        
        # Validate configuration values
        if not isinstance(self.batch_size, int) or self.batch_size <= 0:
            raise ValueError(f"batch_size must be a positive integer, got {self.batch_size}")
        
        if not isinstance(self.embedding_model, str) or not self.embedding_model.strip():
            raise ValueError(f"model must be a non-empty string, got {self.embedding_model}")
        
        # Store the full embeddings config for passing to OpenAIService
        self.embeddings_config = embeddings_config
        
        # In-memory cache for performance during single run
        self._memory_cache: Dict[str, List[float]] = {}
        
        logger.info(f"SentenceEmbeddingCache initialized with model={self.embedding_model}, batch_size={self.batch_size}")
    
    def _get_content_hash(self, content: str) -> str:
        """Generate hash for sentence content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    async def generate_single_embedding(self, content: str, openai_service) -> List[float]:
        """Generate embedding for a single text content with caching"""
        try:
            embeddings, _, _ = await self.get_embeddings([content], openai_service)
            return embeddings[0] if embeddings else []
        except Exception as e:
            logger.warning(f"Failed to generate embedding for content: {str(e)}")
            return []
    
    async def get_embeddings(self, sentences: List[str], openai_service) -> Tuple[List[List[float]], int, int]:
        """
        Get embeddings for sentences, using in-memory cache when available.
        
        Args:
            sentences: List of sentences to embed
            openai_service: OpenAIService instance for generating embeddings
            
        Returns:
            Tuple of (embeddings, cache_hits, cache_misses)
        """
        embeddings = []
        cache_hits = 0
        cache_misses = 0
        uncached_sentences = []
        uncached_indices = []
        
        # Check in-memory cache for each sentence
        for i, sentence in enumerate(sentences):
            content_hash = self._get_content_hash(sentence)
            
            if content_hash in self._memory_cache:
                embeddings.append(self._memory_cache[content_hash])
                cache_hits += 1
            else:
                embeddings.append(None)  # Placeholder
                uncached_sentences.append(sentence)
                uncached_indices.append(i)
                cache_misses += 1
        
        # Generate embeddings for uncached sentences
        if uncached_sentences:
            logger.info(f"Generating embeddings for {len(uncached_sentences)} uncached sentences")
            new_embeddings = await self._batch_generate_embeddings(uncached_sentences, openai_service)
            
            # Cache new embeddings in memory and fill placeholders
            for idx, sentence, embedding in zip(uncached_indices, uncached_sentences, new_embeddings):
                content_hash = self._get_content_hash(sentence)
                self._memory_cache[content_hash] = embedding
                embeddings[idx] = embedding
        
        logger.info(f"Embedding generation: {cache_hits} hits, {cache_misses} misses")
        
        return embeddings, cache_hits, cache_misses
    
    def get_cache_info(self) -> Dict:
        """Get in-memory cache information and statistics"""
        return {
            'cached_sentences': len(self._memory_cache),
            'model': self.embedding_model,
            'batch_size': self.batch_size,
            'stats': {
                'total_cached': len(self._memory_cache),
                'hit_rate': 0.0  # This would need to be tracked across calls for accurate stats
            }
        }
    
    def clear_cache(self):
        """Clear in-memory cache"""
        self._memory_cache.clear()
        logger.info("In-memory cache cleared")
    
    async def _batch_generate_embeddings(self, sentences: List[str], openai_service) -> List[List[float]]:
        """Generate embeddings in batches using the centralized OpenAIService."""
        all_embeddings = []
        
        for i in range(0, len(sentences), self.batch_size):
            batch = sentences[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (len(sentences) + self.batch_size - 1) // self.batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches}: {len(batch)} sentences")
            
            try:
                # Use the centralized OpenAIService for batch embedding generation
                embedding_responses = await openai_service.generate_embeddings_batch(batch, self.embeddings_config)
                
                # Extract just the embedding vectors from the response objects
                batch_embeddings = [response.embedding for response in embedding_responses]
                all_embeddings.extend(batch_embeddings)
                
                logger.debug(f"Successfully generated {len(batch_embeddings)} embeddings for batch {batch_num}")
                    
            except Exception as e:
                logger.error(f"Error generating embeddings for batch {batch_num}: {e}")
                # Add empty embeddings for failed batch
                batch_embeddings = [[] for _ in batch]
                all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
