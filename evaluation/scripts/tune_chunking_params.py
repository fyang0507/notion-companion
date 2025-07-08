#!/usr/bin/env python3
"""
Chunking Parameter Tuning Script

This script demonstrates Step 3 of the evaluation workflow: experimenting with different
chunk merging parameters using cached sentence-level embeddings for fast iteration.

Usage:
  python scripts/tune_chunking_params.py                    # Run parameter sweep
  python scripts/tune_chunking_params.py --single-test     # Test single parameter set
  python scripts/tune_chunking_params.py --compare         # Compare different configs
"""

import json
import logging
import asyncio
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
import copy
import time
from datetime import datetime

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluation.services.multilingual_chunker import MultiLingualChunker
from utils.config_loader import ConfigLoader
import tiktoken

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockEmbeddingService:
    """Mock embedding service for testing"""
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        import random
        embeddings = []
        for text in texts:
            random.seed(hash(text) % (2**32))
            embedding = [random.random() for _ in range(1536)]
            embeddings.append(embedding)
        return embeddings


class ChunkingParameterTuner:
    """Parameter tuning system for chunking parameters"""
    
    def __init__(self, base_config_path: str = "config/chunking_config.toml", cache_dir: str = "data/cache"):
        # Load base configuration
        config_path = Path(base_config_path)
        if config_path.is_file():
            config_dir = config_path.parent
            config_file = config_path.name
        else:
            config_dir = config_path
            config_file = "chunking_config.toml"
        
        config_loader = ConfigLoader(config_dir)
        self.base_config = config_loader.load_chunking_config(config_file)
        
        # Initialize services
        self.embedding_service = MockEmbeddingService()
        encoding_name = self.base_config.get('chunking', {}).get('encoding', 'cl100k_base')
        self.tokenizer = tiktoken.get_encoding(encoding_name)
        
        self.cache_dir = cache_dir
        
        logger.info("ChunkingParameterTuner initialized")
    
    def create_config_variant(self, 
                            similarity_threshold: float = None,
                            max_merge_distance: int = None,
                            max_chunk_size: int = None) -> Dict:
        """Create a configuration variant with specified parameters"""
        config = copy.deepcopy(self.base_config)
        
        if similarity_threshold is not None:
            config['semantic_merging']['similarity_threshold'] = similarity_threshold
        if max_merge_distance is not None:
            config['semantic_merging']['max_merge_distance'] = max_merge_distance
        if max_chunk_size is not None:
            config['semantic_merging']['max_chunk_size'] = max_chunk_size
        
        return config
    
    async def test_parameter_set(self, config: Dict, test_documents: List[Dict], 
                               test_name: str = "Test") -> Dict:
        """Test a specific parameter configuration"""
        logger.info(f"Testing configuration: {test_name}")
        
        start_time = time.time()
        
        # Create chunker with this config
        chunker = MultiLingualChunker(
            self.embedding_service,
            self.tokenizer,
            config,
            self.cache_dir
        )
        
        # Track metrics
        total_chunks = 0
        total_tokens = 0
        total_sentences = 0
        chunk_sizes = []
        merge_ratios = []
        cache_hits = 0
        cache_misses = 0
        
        # Process each test document
        for i, doc in enumerate(test_documents):
            content = doc.get('content', '')
            if not content.strip():
                continue
            
            # Get cache stats before
            cache_info_before = chunker.get_cache_info()
            
            # Chunk the document
            chunks = await chunker.chunk_text(content)
            
            # Get cache stats after
            cache_info_after = chunker.get_cache_info()
            
            # Calculate cache performance
            stats_before = cache_info_before.get('stats', {})
            stats_after = cache_info_after.get('stats', {})
            
            doc_hits = stats_after.get('total_cache_hits', 0) - stats_before.get('total_cache_hits', 0)
            doc_misses = stats_after.get('total_cache_misses', 0) - stats_before.get('total_cache_misses', 0)
            
            cache_hits += doc_hits
            cache_misses += doc_misses
            
            # Calculate metrics
            total_chunks += len(chunks)
            
            # Count sentences for merge ratio
            sentences = chunker.sentence_splitter.split(content)
            total_sentences += len(sentences)
            
            if len(sentences) > 0:
                merge_ratios.append(len(chunks) / len(sentences))
            
            # Calculate token counts
            for chunk in chunks:
                token_count = len(self.tokenizer.encode(chunk.content))
                total_tokens += token_count
                chunk_sizes.append(token_count)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Calculate summary statistics
        avg_chunk_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0
        avg_merge_ratio = sum(merge_ratios) / len(merge_ratios) if merge_ratios else 0
        total_requests = cache_hits + cache_misses
        cache_hit_rate = cache_hits / total_requests if total_requests > 0 else 0
        
        # Extract configuration parameters
        semantic_config = config.get('semantic_merging', {})
        
        results = {
            'test_name': test_name,
            'parameters': {
                'similarity_threshold': semantic_config.get('similarity_threshold'),
                'max_merge_distance': semantic_config.get('max_merge_distance'),
                'max_chunk_size': semantic_config.get('max_chunk_size')
            },
            'metrics': {
                'total_documents': len(test_documents),
                'total_sentences': total_sentences,
                'total_chunks': total_chunks,
                'total_tokens': total_tokens,
                'avg_chunk_size_tokens': avg_chunk_size,
                'avg_merge_ratio': avg_merge_ratio,  # chunks/sentences (lower = more merging)
                'chunks_per_document': total_chunks / len(test_documents) if test_documents else 0,
                'sentences_per_chunk': total_sentences / total_chunks if total_chunks > 0 else 0
            },
            'performance': {
                'processing_time_seconds': processing_time,
                'cache_hits': cache_hits,
                'cache_misses': cache_misses,
                'cache_hit_rate': cache_hit_rate,
                'chunks_per_second': total_chunks / processing_time if processing_time > 0 else 0
            },
            'chunk_size_distribution': {
                'min': min(chunk_sizes) if chunk_sizes else 0,
                'max': max(chunk_sizes) if chunk_sizes else 0,
                'median': sorted(chunk_sizes)[len(chunk_sizes)//2] if chunk_sizes else 0
            }
        }
        
        return results
    
    async def parameter_sweep(self, test_documents: List[Dict]) -> List[Dict]:
        """Run a parameter sweep across different configurations"""
        logger.info("Starting parameter sweep")
        
        # Define parameter ranges to test
        similarity_thresholds = [0.3, 0.5, 0.7, 0.8]
        max_merge_distances = [1, 2, 3, 5]
        max_chunk_sizes = [128, 256, 512]
        
        results = []
        total_tests = len(similarity_thresholds) * len(max_merge_distances) * len(max_chunk_sizes)
        test_count = 0
        
        for similarity in similarity_thresholds:
            for merge_distance in max_merge_distances:
                for chunk_size in max_chunk_sizes:
                    test_count += 1
                    test_name = f"sim{similarity}_dist{merge_distance}_size{chunk_size}"
                    
                    logger.info(f"Running test {test_count}/{total_tests}: {test_name}")
                    
                    # Create configuration
                    config = self.create_config_variant(
                        similarity_threshold=similarity,
                        max_merge_distance=merge_distance,
                        max_chunk_size=chunk_size
                    )
                    
                    # Test this configuration
                    result = await self.test_parameter_set(config, test_documents, test_name)
                    results.append(result)
                    
                    # Log quick summary
                    metrics = result['metrics']
                    perf = result['performance']
                    logger.info(f"  Result: {metrics['total_chunks']} chunks, "
                              f"avg {metrics['avg_chunk_size_tokens']:.1f} tokens, "
                              f"merge ratio {metrics['avg_merge_ratio']:.2f}, "
                              f"cache hit rate {perf['cache_hit_rate']:.1%}")
        
        return results
    
    def analyze_results(self, results: List[Dict]) -> Dict:
        """Analyze parameter sweep results"""
        logger.info("Analyzing parameter sweep results")
        
        # Find best configurations for different objectives
        best_merge_ratio = min(results, key=lambda r: r['metrics']['avg_merge_ratio'])
        best_chunk_size = max(results, key=lambda r: r['metrics']['avg_chunk_size_tokens'])
        best_performance = max(results, key=lambda r: r['performance']['chunks_per_second'])
        best_cache_hit = max(results, key=lambda r: r['performance']['cache_hit_rate'])
        
        # Parameter impact analysis
        param_impacts = {
            'similarity_threshold': {},
            'max_merge_distance': {},
            'max_chunk_size': {}
        }
        
        for result in results:
            params = result['parameters']
            metrics = result['metrics']
            
            for param_name, param_value in params.items():
                if param_value not in param_impacts[param_name]:
                    param_impacts[param_name][param_value] = []
                param_impacts[param_name][param_value].append(metrics['avg_merge_ratio'])
        
        # Calculate average impact for each parameter value
        for param_name in param_impacts:
            for param_value in param_impacts[param_name]:
                values = param_impacts[param_name][param_value]
                param_impacts[param_name][param_value] = sum(values) / len(values)
        
        analysis = {
            'summary': {
                'total_configurations_tested': len(results),
                'best_merge_ratio': best_merge_ratio['metrics']['avg_merge_ratio'],
                'best_chunk_size': best_chunk_size['metrics']['avg_chunk_size_tokens'],
                'avg_cache_hit_rate': sum(r['performance']['cache_hit_rate'] for r in results) / len(results)
            },
            'best_configurations': {
                'most_merging': best_merge_ratio,
                'largest_chunks': best_chunk_size,
                'fastest_processing': best_performance,
                'best_cache_utilization': best_cache_hit
            },
            'parameter_impacts': param_impacts
        }
        
        return analysis


def load_test_documents(data_dir: str) -> List[Dict]:
    """Load test documents from data directory"""
    data_path = Path(data_dir)
    json_files = list(data_path.glob("*.json"))
    
    all_documents = []
    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            all_documents.extend(data)
        elif isinstance(data, dict) and 'documents' in data:
            all_documents.extend(data['documents'])
        else:
            all_documents.append(data)
    
    logger.info(f"Loaded {len(all_documents)} test documents")
    return all_documents


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Chunking Parameter Tuning Script')
    parser.add_argument('--single-test', action='store_true',
                       help='Run single test with current configuration')
    parser.add_argument('--compare', action='store_true',
                       help='Compare a few select configurations')
    parser.add_argument('--cache-dir', default='data/cache',
                       help='Cache directory (default: data/cache)')
    parser.add_argument('--data-dir', default='data',
                       help='Data directory (default: data)')
    parser.add_argument('--output-file', default='data/tuning_results.json',
                       help='Output file for results (default: data/tuning_results.json)')
    
    args = parser.parse_args()
    
    # Load test documents
    test_documents = load_test_documents(args.data_dir)
    if not test_documents:
        logger.error("No test documents found!")
        return
    
    # Initialize tuner
    tuner = ChunkingParameterTuner(cache_dir=args.cache_dir)
    
    if args.single_test:
        logger.info("Running single configuration test")
        result = await tuner.test_parameter_set(tuner.base_config, test_documents, "BaseConfig")
        print(json.dumps(result, indent=2))
        return
    
    if args.compare:
        logger.info("Running configuration comparison")
        
        # Define a few configurations to compare
        configs_to_test = [
            {"name": "Conservative", "similarity": 0.8, "distance": 2, "size": 256},
            {"name": "Moderate", "similarity": 0.6, "distance": 3, "size": 384},
            {"name": "Aggressive", "similarity": 0.4, "distance": 5, "size": 512},
            {"name": "Base", "similarity": None, "distance": None, "size": None}  # Use base config
        ]
        
        results = []
        for config_def in configs_to_test:
            if config_def["similarity"] is None:
                config = tuner.base_config
            else:
                config = tuner.create_config_variant(
                    similarity_threshold=config_def["similarity"],
                    max_merge_distance=config_def["distance"],
                    max_chunk_size=config_def["size"]
                )
            
            result = await tuner.test_parameter_set(config, test_documents, config_def["name"])
            results.append(result)
        
        # Save results
        output_data = {
            'test_type': 'comparison',
            'timestamp': datetime.now().isoformat(),
            'results': results
        }
        
        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Comparison results saved to {args.output_file}")
        
        # Print summary
        print("\n=== CONFIGURATION COMPARISON ===")
        for result in results:
            metrics = result['metrics']
            perf = result['performance']
            print(f"{result['test_name']:12} | "
                  f"Chunks: {metrics['total_chunks']:3d} | "
                  f"Avg Size: {metrics['avg_chunk_size_tokens']:5.1f} | "
                  f"Merge Ratio: {metrics['avg_merge_ratio']:.2f} | "
                  f"Cache Hit: {perf['cache_hit_rate']:5.1%}")
        
        return
    
    # Default: Run full parameter sweep
    logger.info("Running full parameter sweep")
    results = await tuner.parameter_sweep(test_documents)
    
    # Analyze results
    analysis = tuner.analyze_results(results)
    
    # Save results
    output_data = {
        'test_type': 'parameter_sweep',
        'timestamp': datetime.now().isoformat(),
        'results': results,
        'analysis': analysis
    }
    
    with open(args.output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Parameter sweep results saved to {args.output_file}")
    
    # Print summary
    print("\n=== PARAMETER SWEEP SUMMARY ===")
    print(f"Total configurations tested: {analysis['summary']['total_configurations_tested']}")
    print(f"Best merge ratio: {analysis['summary']['best_merge_ratio']:.3f}")
    print(f"Best chunk size: {analysis['summary']['best_chunk_size']:.1f} tokens")
    print(f"Average cache hit rate: {analysis['summary']['avg_cache_hit_rate']:.1%}")
    
    print("\n=== BEST CONFIGURATIONS ===")
    for category, config in analysis['best_configurations'].items():
        params = config['parameters']
        metrics = config['metrics']
        print(f"{category:20} | {config['test_name']:15} | "
              f"Similarity: {params['similarity_threshold']:.1f} | "
              f"Distance: {params['max_merge_distance']} | "
              f"Size: {params['max_chunk_size']} | "
              f"Merge Ratio: {metrics['avg_merge_ratio']:.3f}")


if __name__ == "__main__":
    asyncio.run(main()) 