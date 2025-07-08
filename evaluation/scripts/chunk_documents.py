#!/usr/bin/env python3
"""
Cached Document Chunking Script

Enhanced version of chunk_documents.py with sentence-level embedding caching.
Ideal for Step 2 completion and Step 3 parameter tuning preparation.

Usage:
  python scripts/chunk_documents_cached.py                    # Normal chunking with caching
  python scripts/chunk_documents_cached.py --precompute       # Precompute sentence embeddings only
  python scripts/chunk_documents_cached.py --retune          # Fast re-chunking with different params
  python scripts/chunk_documents_cached.py --cache-info      # Show cache statistics
  python scripts/chunk_documents_cached.py --clear-cache     # Clear cache
"""

import json
import logging
import asyncio
import argparse
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import tiktoken
from datetime import datetime

# Add parent directories to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from evaluation.services.multilingual_chunker import MultiLingualChunker
from utils.config_loader import ConfigLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ChunkingStats:
    """Statistics for chunking operation"""
    total_documents: int
    total_chunks: int
    total_tokens: int
    total_sentences: int
    cache_hits: int
    cache_misses: int
    processing_time_seconds: float
    average_tokens_per_chunk: float
    cache_hit_rate: float


class MockEmbeddingService:
    """Mock embedding service for development and testing"""
    
    def __init__(self, model_name: str = "text-embedding-3-small"):
        self.model_name = model_name
        logger.info(f"Initialized MockEmbeddingService with model: {model_name}")
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings (random vectors for development)"""
        import random
        
        embeddings = []
        for text in texts:
            # Generate consistent mock embeddings based on text hash
            random.seed(hash(text) % (2**32))
            embedding = [random.random() for _ in range(1536)]  # OpenAI dimension
            embeddings.append(embedding)
        
        return embeddings


class CachedDocumentChunker:
    """Enhanced document chunker with caching capabilities"""
    
    def __init__(self, config_path: str = "config/chunking_config.toml", cache_dir: str = "data/cache"):
        # Parse config path
        config_path = Path(config_path)
        if config_path.is_file():
            config_dir = config_path.parent
            config_file = config_path.name
        else:
            config_dir = config_path
            config_file = "chunking_config.toml"
        
        # Load configuration using ConfigLoader
        config_loader = ConfigLoader(config_dir)
        self.config = config_loader.load_chunking_config(config_file)
        
        # Initialize services
        self.embedding_service = MockEmbeddingService()
        
        # Initialize tokenizer
        encoding_name = self.config.get('chunking', {}).get('encoding', 'cl100k_base')
        self.tokenizer = tiktoken.get_encoding(encoding_name)
        logger.info(f"Initialized tokenizer with encoding: {encoding_name}")
        
        # Initialize chunker with caching
        self.chunker = MultiLingualChunker(
            self.embedding_service, 
            self.tokenizer, 
            self.config,
            cache_dir
        )
        
        logger.info("CachedDocumentChunker initialized successfully")
    
    def load_documents(self, json_file: Path) -> List[Dict[str, Any]]:
        """Load documents from JSON file"""
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'documents' in data:
            return data['documents']
        else:
            # Assume single document
            return [data]
    
    async def precompute_embeddings(self, data_dir: Path) -> Dict:
        """Precompute sentence embeddings for all documents in data directory"""
        logger.info("Starting sentence embedding precomputation")
        
        json_files = list(data_dir.glob("*.json"))
        logger.info(f"Found {len(json_files)} JSON files to precompute")
        
        all_documents = []
        for json_file in json_files:
            logger.info(f"Loading {json_file.name}")
            documents = self.load_documents(json_file)
            all_documents.extend(documents)
        
        # Precompute embeddings
        stats = await self.chunker.precompute_sentence_embeddings(all_documents)
        
        return stats
    
    async def process_documents(self, data_dir: Path, output_dir: Path, retune_mode: bool = False) -> ChunkingStats:
        """Process all documents with caching"""
        start_time = asyncio.get_event_loop().time()
        
        # Find all JSON files in the data directory
        json_files = list(data_dir.glob("*.json"))
        
        if not json_files:
            logger.warning(f"No JSON files found in {data_dir}")
            return ChunkingStats(0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        logger.info(f"Found {len(json_files)} JSON files to process")
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        total_chunks = 0
        total_tokens = 0
        total_sentences = 0
        total_cache_hits = 0
        total_cache_misses = 0
        
        for json_file in json_files:
            logger.info(f"Processing {json_file.name}")
            
            # Load documents
            documents = self.load_documents(json_file)
            logger.info(f"Loaded {len(documents)} documents from {json_file.name}")
            
            # Process each document
            all_chunks = []
            
            for doc in documents:
                doc_id = doc.get('id', str(hash(doc.get('content', ''))))
                title = doc.get('title', 'Untitled')
                content = doc.get('content', '')
                
                if not content.strip():
                    logger.warning(f"Skipping document {doc_id} - no content")
                    continue
                
                logger.info(f"Chunking document: {title[:50]}...")
                
                # Get cache info before processing
                cache_info_before = self.chunker.get_cache_info()
                initial_requests = cache_info_before.get('stats', {}).get('total_requests', 0)
                
                # Chunk the document
                chunks = await self.chunker.chunk_text(content, doc_id)
                
                # Get cache info after processing
                cache_info_after = self.chunker.get_cache_info()
                final_requests = cache_info_after.get('stats', {}).get('total_requests', 0)
                
                # Calculate cache stats for this document
                requests_made = final_requests - initial_requests
                hits = cache_info_after.get('stats', {}).get('total_cache_hits', 0) - cache_info_before.get('stats', {}).get('total_cache_hits', 0)
                misses = requests_made - hits if requests_made > hits else 0
                
                total_cache_hits += hits
                total_cache_misses += misses
                
                logger.info(f"Created {len(chunks)} chunks for document {doc_id}")
                
                # Convert chunks to serializable format
                for i, chunk in enumerate(chunks):
                    chunk_data = {
                        "document_id": doc_id,
                        "document_title": title,
                        "chunk_id": f"{doc_id}_chunk_{i}",
                        "content": chunk.content,
                        "start_sentence": chunk.start_sentence,
                        "end_sentence": chunk.end_sentence,
                        "embedding": chunk.embedding,
                        "context_before": chunk.context_before,
                        "context_after": chunk.context_after,
                        "token_count": len(self.tokenizer.encode(chunk.content)),
                        "created_at": datetime.now().isoformat()
                    }
                    
                    all_chunks.append(chunk_data)
                    total_chunks += 1
                    total_tokens += chunk_data["token_count"]
                
                # Count sentences for statistics
                sentences = self.chunker.sentence_splitter.split(content)
                total_sentences += len(sentences)
            
            # Save chunks to output file
            output_file = output_dir / f"{json_file.stem}_chunks.json"
            
            # Prepare output data
            output_data = {
                "metadata": {
                    "source_file": str(json_file),
                    "total_chunks": len(all_chunks),
                    "total_documents": len(documents),
                    "created_at": datetime.now().isoformat(),
                    "config": self.config,
                    "cache_info": self.chunker.get_cache_info()
                },
                "chunks": all_chunks
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved {len(all_chunks)} chunks to {output_file}")
            
            # Summary for this file
            file_tokens = sum(chunk["token_count"] for chunk in all_chunks)
            avg_tokens = file_tokens / len(all_chunks) if all_chunks else 0
            
            logger.info(f"Summary for {json_file.name}:")
            logger.info(f"  - Total chunks: {len(all_chunks)}")
            logger.info(f"  - Total tokens: {file_tokens}")
            logger.info(f"  - Average tokens per chunk: {avg_tokens:.1f}")
        
        end_time = asyncio.get_event_loop().time()
        processing_time = end_time - start_time
        
        # Calculate overall statistics
        avg_tokens_per_chunk = total_tokens / total_chunks if total_chunks > 0 else 0
        total_requests = total_cache_hits + total_cache_misses
        cache_hit_rate = total_cache_hits / total_requests if total_requests > 0 else 0
        
        stats = ChunkingStats(
            total_documents=len(json_files),
            total_chunks=total_chunks,
            total_tokens=total_tokens,
            total_sentences=total_sentences,
            cache_hits=total_cache_hits,
            cache_misses=total_cache_misses,
            processing_time_seconds=processing_time,
            average_tokens_per_chunk=avg_tokens_per_chunk,
            cache_hit_rate=cache_hit_rate
        )
        
        return stats
    
    def get_cache_info(self) -> Dict:
        """Get cache information"""
        return self.chunker.get_cache_info()
    
    def clear_cache(self):
        """Clear cache"""
        self.chunker.clear_cache()


async def main():
    """Main function with command line arguments"""
    parser = argparse.ArgumentParser(description='Cached Document Chunking Script')
    parser.add_argument('--precompute', action='store_true',
                       help='Precompute sentence embeddings only (Step 2 preparation)')
    parser.add_argument('--retune', action='store_true',
                       help='Fast re-chunking mode (assumes embeddings are cached)')
    parser.add_argument('--cache-info', action='store_true',
                       help='Show cache information and statistics')
    parser.add_argument('--clear-cache', action='store_true',
                       help='Clear embedding cache')
    parser.add_argument('--cache-dir', default='data/cache',
                       help='Cache directory (default: data/cache)')
    parser.add_argument('--data-dir', default='data',
                       help='Data directory (default: data)')
    parser.add_argument('--output-dir', default='data/processed',
                       help='Output directory (default: data/processed)')
    
    args = parser.parse_args()
    
    # Initialize chunker
    chunker = CachedDocumentChunker(cache_dir=args.cache_dir)
    
    if args.clear_cache:
        logger.info("Clearing cache...")
        chunker.clear_cache()
        logger.info("Cache cleared successfully")
        return
    
    if args.cache_info:
        logger.info("Cache Information:")
        cache_info = chunker.get_cache_info()
        print(json.dumps(cache_info, indent=2))
        return
    
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    
    if args.precompute:
        logger.info("Running sentence embedding precomputation mode")
        stats = await chunker.precompute_embeddings(data_dir)
        logger.info("Precomputation complete!")
        logger.info(f"Statistics: {json.dumps(stats, indent=2)}")
        return
    
    # Normal processing mode
    if args.retune:
        logger.info("Running fast retune mode (using cached embeddings)")
    else:
        logger.info("Running normal chunking mode with caching")
    
    stats = await chunker.process_documents(data_dir, output_dir, retune_mode=args.retune)
    
    # Print final statistics
    logger.info("\n=== FINAL STATISTICS ===")
    logger.info(f"Total documents processed: {stats.total_documents}")
    logger.info(f"Total chunks created: {stats.total_chunks}")
    logger.info(f"Total sentences processed: {stats.total_sentences}")
    logger.info(f"Total tokens: {stats.total_tokens}")
    logger.info(f"Average tokens per chunk: {stats.average_tokens_per_chunk:.1f}")
    logger.info(f"Processing time: {stats.processing_time_seconds:.2f} seconds")
    logger.info(f"Cache performance: {stats.cache_hits} hits, {stats.cache_misses} misses")
    logger.info(f"Cache hit rate: {stats.cache_hit_rate:.1%}")
    
    # Show cache info
    cache_info = chunker.get_cache_info()
    logger.info(f"Final cache size: {cache_info['cached_sentences']} sentences")
    logger.info(f"Cache file size: {cache_info['cache_file_size_mb']:.2f} MB")


if __name__ == "__main__":
    asyncio.run(main()) 