"""
Sentence Embedding Cache Service

Provides caching for sentence-level embeddings to speed up parameter tuning
for chunk merging without recomputing expensive embeddings.
"""

import json
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict
import asyncio

logger = logging.getLogger(__name__)


@dataclass 
class CachedSentence:
    """Cached sentence with its embedding"""
    content: str
    embedding: List[float]
    content_hash: str
    created_at: str


class SentenceEmbeddingCache:
    """File-based cache for sentence embeddings"""
    
    def __init__(self, config: Dict):
        """
        Initialize cache with required configuration.
        
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
            self.cache_dir = Path(embeddings_config['cache_dir'])
            self.embedding_model = embeddings_config['model']
            self.batch_size = embeddings_config['batch_size']
        except KeyError as e:
            raise KeyError(f"Missing required configuration key in embeddings section: {e}")
        
        # Validate configuration values
        if not isinstance(self.batch_size, int) or self.batch_size <= 0:
            raise ValueError(f"batch_size must be a positive integer, got {self.batch_size}")
        
        if not isinstance(self.embedding_model, str) or not self.embedding_model.strip():
            raise ValueError(f"model must be a non-empty string, got {self.embedding_model}")
        
        # Setup cache directories and files
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "sentence_embeddings.json"
        self.stats_file = self.cache_dir / "cache_stats.json"
        
        # In-memory cache for performance
        self._memory_cache: Dict[str, List[float]] = {}
        
        self._load_cache()
        
        logger.info(f"SentenceEmbeddingCache initialized with {len(self._memory_cache)} cached embeddings")
        logger.info(f"Configuration: model={self.embedding_model}, batch_size={self.batch_size}")
        logger.info(f"Cache directory: {self.cache_dir}")
    
    def _load_cache(self):
        """Load cache from disk into memory"""
        if not self.cache_file.exists():
            return
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            cache_data = data.get('cache', {})
            for content_hash, cached_item in cache_data.items():
                self._memory_cache[content_hash] = cached_item['embedding']
            
            logger.info(f"Loaded {len(self._memory_cache)} sentence embeddings from cache")
            
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            self._memory_cache = {}
    
    def _save_cache(self):
        """Save cache from memory to disk"""
        try:
            # Load existing data to preserve metadata
            existing_data = {}
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            
            # Update cache data
            cache_data = {}
            for content_hash, embedding in self._memory_cache.items():
                cache_data[content_hash] = {
                    'embedding': embedding,
                    'content_hash': content_hash
                }
            
            # Save with metadata
            save_data = {
                'metadata': {
                    'total_cached_sentences': len(cache_data),
                    'last_updated': self._get_timestamp()
                },
                'cache': cache_data
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Saved {len(cache_data)} sentence embeddings to cache")
            
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def _get_content_hash(self, content: str) -> str:
        """Generate hash for sentence content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    def _get_timestamp(self) -> str:
        """Get current timestamp string"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    async def generate_single_embedding(self, content: str, embedding_service) -> List[float]:
        """Generate embedding for a single text content with caching"""
        try:
            embeddings, _, _ = await self.get_embeddings([content], embedding_service)
            return embeddings[0] if embeddings else []
        except Exception as e:
            logger.warning(f"Failed to generate embedding for content: {str(e)}")
            return []
    
    async def get_embeddings(self, sentences: List[str], embedding_service) -> Tuple[List[List[float]], int, int]:
        """
        Get embeddings for sentences, using cache when available.
        
        Returns:
            Tuple of (embeddings, cache_hits, cache_misses)
        """
        embeddings = []
        cache_hits = 0
        cache_misses = 0
        uncached_sentences = []
        uncached_indices = []
        
        # Check cache for each sentence (if caching is enabled)
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
            new_embeddings = await self._batch_generate_embeddings(uncached_sentences, embedding_service)
            
            # Cache new embeddings and fill placeholders
            for idx, sentence, embedding in zip(uncached_indices, uncached_sentences, new_embeddings):
                content_hash = self._get_content_hash(sentence)
                self._memory_cache[content_hash] = embedding
                embeddings[idx] = embedding
        
        # Save cache if we added new embeddings
        if uncached_sentences:
            self._save_cache()
        
        # Update stats
        self._update_stats(cache_hits, cache_misses)
        
        logger.info(f"Embedding cache: {cache_hits} hits, {cache_misses} misses")
        
        return embeddings, cache_hits, cache_misses
    
    def _update_stats(self, cache_hits: int, cache_misses: int):
        """Update cache statistics"""
        try:
            stats = {}
            if self.stats_file.exists():
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
            
            stats.update({
                'total_requests': stats.get('total_requests', 0) + cache_hits + cache_misses,
                'total_cache_hits': stats.get('total_cache_hits', 0) + cache_hits,
                'total_cache_misses': stats.get('total_cache_misses', 0) + cache_misses,
                'hit_rate': (stats.get('total_cache_hits', 0) + cache_hits) / (stats.get('total_requests', 0) + cache_hits + cache_misses),
                'last_updated': self._get_timestamp()
            })
            
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to update cache stats: {e}")
    
    def get_cache_info(self) -> Dict:
        """Get cache information and statistics"""
        stats = {}
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
            except Exception:
                pass
        
        return {
            'cached_sentences': len(self._memory_cache),
            'cache_file': str(self.cache_file),
            'cache_file_exists': self.cache_file.exists(),
            'cache_file_size_mb': self.cache_file.stat().st_size / (1024*1024) if self.cache_file.exists() else 0,
            'stats': stats
        }
    
    def clear_cache(self):
        """Clear all cached data"""
        self._memory_cache.clear()
        
        if self.cache_file.exists():
            self.cache_file.unlink()
        
        if self.stats_file.exists():
            self.stats_file.unlink()
            
        logger.info("Cache cleared")
    
    async def _batch_generate_embeddings(self, sentences: List[str], embedding_service) -> List[List[float]]:
        """Generate embeddings in batches for better performance."""
        # Use direct OpenAI API for batch processing to avoid individual delays
        from openai import AsyncOpenAI
        import asyncio
        
        client = AsyncOpenAI()
        all_embeddings = []
        
        for i in range(0, len(sentences), self.batch_size):
            batch = sentences[i:i + self.batch_size]
            logger.info(f"Processing batch {i//self.batch_size + 1}/{(len(sentences) + self.batch_size - 1)//self.batch_size}: {len(batch)} sentences")
            
            try:
                response = await client.embeddings.create(
                    model=self.embedding_model,
                    input=batch,
                    dimensions=1536
                )
                
                # Extract embeddings from response
                batch_embeddings = [data.embedding for data in response.data]
                all_embeddings.extend(batch_embeddings)
                
                # Add small delay between batches to avoid rate limiting
                if i + self.batch_size < len(sentences):
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Error generating embeddings for batch: {e}")
                # Fallback to individual generation for this batch
                batch_embeddings = []                
                all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
