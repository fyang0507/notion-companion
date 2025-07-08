#!/usr/bin/env python3
"""
Orchestration script for evaluation dataset chunking workflow.

This script coordinates the 4-step chunking process:
1. Read collected Notion documents from data_collector.py output
2. Split documents into sentences using sentence_splitter.py
3. Generate embeddings for sentences using sentence_embedding.py (with caching)
4. Merge semantically similar sentences using semantic_merger.py

All parameters are controlled via the configuration file (chunking_config.toml).
No configuration overrides are accepted via CLI to ensure consistency.

Usage:
    python orchestrate_chunking.py --input-file data/collected_documents.json
    python orchestrate_chunking.py --input-file data/collected_documents.json --experiment-name "experiment_1"
    python orchestrate_chunking.py --input-file data/collected_documents.json --config custom_config.toml
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import tiktoken
import numpy as np

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))

# Load environment variables from root folder
from dotenv import load_dotenv
root_dir = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=root_dir / ".env")

from services.sentence_splitter import RobustSentenceSplitter
from services.sentence_embedding import SentenceEmbeddingCache
from services.semantic_merger import SemanticMerger
from utils.config_loader import ConfigLoader
from backend.services.openai_service import OpenAIService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('evaluation/logs/orchestration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ChunkingOrchestrator:
    """Orchestrates the 4-step chunking workflow for evaluation dataset preparation."""
    
    def __init__(self, config_path: str = "chunking_config.toml"):
        """Initialize orchestrator with configuration."""
        self.config_loader = ConfigLoader()
        self.config = self.config_loader.load_chunking_config(config_path)
        
        # Initialize components
        self.sentence_splitter = RobustSentenceSplitter(self.config)
        self.embedding_cache = SentenceEmbeddingCache(self.config)
        self.openai_service = OpenAIService()
        
        # Initialize tokenizer for semantic merger
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.semantic_merger = SemanticMerger(self.tokenizer, self.config)
        
        # Create output directories
        self.data_dir = Path("evaluation/data")
        self.processed_dir = self.data_dir / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("ChunkingOrchestrator initialized successfully")
    
    def load_collected_documents(self, input_file: str) -> List[Dict[str, Any]]:
        """
        Step 1: Load documents from data_collector.py output.
        
        Args:
            input_file: Path to JSON file containing collected documents
            
        Returns:
            List of document dictionaries
        """
        logger.info(f"📖 Step 1: Loading collected documents from {input_file}")
        
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        documents = data.get('documents', [])
        logger.info(f"✅ Loaded {len(documents)} documents")
        
        return documents
    
    def split_documents_into_sentences(self, documents: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Step 2: Split documents into sentences using sentence_splitter.py.
        
        Args:
            documents: List of document dictionaries
            
        Returns:
            Dictionary mapping document_id to list of sentences
        """
        logger.info("✂️ Step 2: Splitting documents into sentences")
        
        doc_sentences = {}
        total_sentences = 0
        
        for doc in documents:
            doc_id = doc['id']
            content = doc['content']
            
            if not content or not content.strip():
                logger.warning(f"Skipping empty document: {doc_id}")
                continue
            
            sentences = self.sentence_splitter.split(content)
            doc_sentences[doc_id] = sentences
            total_sentences += len(sentences)
            
            logger.debug(f"Document {doc_id}: {len(sentences)} sentences")
        
        logger.info(f"✅ Split {len(doc_sentences)} documents into {total_sentences} sentences")
        return doc_sentences
    
    async def generate_sentence_embeddings(self, doc_sentences: Dict[str, List[str]]) -> Dict[str, List[List[float]]]:
        """
        Step 3: Generate embeddings for sentences using sentence_embedding.py with caching.
        
        Args:
            doc_sentences: Dictionary mapping document_id to list of sentences
            
        Returns:
            Dictionary mapping document_id to list of embeddings
        """
        logger.info("🔢 Step 3: Generating sentence embeddings (with caching)")
        
        doc_embeddings = {}
        total_cache_hits = 0
        total_cache_misses = 0
        
        for doc_id, sentences in doc_sentences.items():
            if not sentences:
                logger.warning(f"Skipping document with no sentences: {doc_id}")
                continue
            
            logger.info(f"Processing embeddings for document {doc_id} ({len(sentences)} sentences)")
            
            # Generate embeddings with caching
            embeddings, cache_hits, cache_misses = await self.embedding_cache.get_embeddings(
                sentences, self.openai_service
            )
            
            doc_embeddings[doc_id] = embeddings
            total_cache_hits += cache_hits
            total_cache_misses += cache_misses
            
            logger.debug(f"Document {doc_id}: {cache_hits} cache hits, {cache_misses} cache misses")
        
        logger.info(f"✅ Generated embeddings for {len(doc_embeddings)} documents")
        logger.info(f"📊 Cache performance: {total_cache_hits} hits, {total_cache_misses} misses")
        
        return doc_embeddings
    
    def analyze_similarity_distribution(self, doc_sentences: Dict[str, List[str]], 
                                      doc_embeddings: Dict[str, List[List[float]]]) -> Dict[str, Any]:
        """
        Analyze similarity distribution of adjacent sentences to inform threshold tuning.
        
        Args:
            doc_sentences: Dictionary mapping document_id to list of sentences
            doc_embeddings: Dictionary mapping document_id to list of embeddings
            
        Returns:
            Dictionary containing similarity statistics and distribution
        """
        logger.info("📊 Analyzing similarity distribution of adjacent sentences")
        
        all_similarities = []
        doc_stats = {}
        
        for doc_id in doc_sentences.keys():
            if doc_id not in doc_embeddings:
                continue
                
            sentences = doc_sentences[doc_id]
            embeddings = doc_embeddings[doc_id]
            
            if len(sentences) < 2 or len(embeddings) < 2:
                continue
            
            # Calculate cosine similarity for adjacent sentences
            doc_similarities = []
            embeddings_array = np.array(embeddings)
            
            # Normalize embeddings
            norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
            normalized_embeddings = embeddings_array / (norms + 1e-8)
            
            # Calculate similarities for adjacent pairs
            for i in range(len(normalized_embeddings) - 1):
                similarity = np.dot(normalized_embeddings[i], normalized_embeddings[i + 1])
                doc_similarities.append(similarity)
                all_similarities.append(similarity)
            
            # Document-level statistics
            doc_stats[doc_id] = {
                'sentence_count': len(sentences),
                'adjacent_pairs': len(doc_similarities),
                'mean_similarity': np.mean(doc_similarities),
                'std_similarity': np.std(doc_similarities),
                'min_similarity': np.min(doc_similarities),
                'max_similarity': np.max(doc_similarities),
                'median_similarity': np.median(doc_similarities)
            }
        
        # Overall statistics
        if all_similarities:
            all_similarities = np.array(all_similarities)
            
            # Calculate percentiles for threshold guidance
            percentiles = [10, 25, 50, 75, 90, 95, 99]
            percentile_values = np.percentile(all_similarities, percentiles)
            
            # Count how many pairs would be merged at different thresholds
            threshold_analysis = {}
            test_thresholds = [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]
            
            for threshold in test_thresholds:
                above_threshold = np.sum(all_similarities >= threshold)
                merge_rate = above_threshold / len(all_similarities)
                threshold_analysis[threshold] = {
                    'pairs_above_threshold': int(above_threshold),
                    'merge_rate': merge_rate,
                    'potential_reduction': f"{merge_rate:.1%}"
                }
            
            overall_stats = {
                'total_adjacent_pairs': len(all_similarities),
                'mean_similarity': np.mean(all_similarities),
                'std_similarity': np.std(all_similarities),
                'min_similarity': np.min(all_similarities),
                'max_similarity': np.max(all_similarities),
                'median_similarity': np.median(all_similarities),
                'percentiles': dict(zip(percentiles, percentile_values)),
                'threshold_analysis': threshold_analysis
            }
            
            # Log key insights
            logger.info(f"📈 Similarity Analysis Results:")
            logger.info(f"  Total adjacent pairs: {len(all_similarities)}")
            logger.info(f"  Mean similarity: {np.mean(all_similarities):.3f}")
            logger.info(f"  Median similarity: {np.median(all_similarities):.3f}")
            logger.info(f"  90th percentile: {percentile_values[percentiles.index(90)]:.3f}")
            logger.info(f"  95th percentile: {percentile_values[percentiles.index(95)]:.3f}")
            
            logger.info(f"🎯 Threshold Recommendations:")
            logger.info(f"  Conservative (1% merge): {percentile_values[percentiles.index(99)]:.3f}")
            logger.info(f"  Moderate (5% merge): {percentile_values[percentiles.index(95)]:.3f}")
            logger.info(f"  Aggressive (10% merge): {percentile_values[percentiles.index(90)]:.3f}")
            
            return {
                'overall_stats': overall_stats,
                'document_stats': doc_stats,
                'recommendations': {
                    'conservative': float(percentile_values[percentiles.index(99)]),
                    'moderate': float(percentile_values[percentiles.index(95)]),
                    'aggressive': float(percentile_values[percentiles.index(90)])
                }
            }
        else:
            logger.warning("No adjacent sentence pairs found for similarity analysis")
            return {
                'overall_stats': {},
                'document_stats': doc_stats,
                'recommendations': {}
            }
    
    def merge_semantic_sentences(self, doc_sentences: Dict[str, List[str]], 
                               doc_embeddings: Dict[str, List[List[float]]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Step 4: Merge semantically similar sentences using semantic_merger.py.
        
        Uses configuration values from chunking_config.toml. No parameter overrides allowed.
        
        Args:
            doc_sentences: Dictionary mapping document_id to list of sentences
            doc_embeddings: Dictionary mapping document_id to list of embeddings
            
        Returns:
            Dictionary mapping document_id to list of chunk dictionaries
        """
        logger.info("🔄 Step 4: Merging semantically similar sentences")
        
        # Use configuration values directly (no overrides)
        active_params = self.config['semantic_merging']
        logger.info(f"Configuration parameters: threshold={active_params['similarity_threshold']}, "
                   f"max_distance={active_params['max_merge_distance']}, "
                   f"max_size={active_params['max_chunk_size']}")
        
        doc_chunks = {}
        total_chunks = 0
        
        for doc_id in doc_sentences.keys():
            if doc_id not in doc_embeddings:
                logger.warning(f"Skipping document without embeddings: {doc_id}")
                continue
            
            sentences = doc_sentences[doc_id]
            embeddings = doc_embeddings[doc_id]
            
            if len(sentences) != len(embeddings):
                logger.error(f"Mismatch in document {doc_id}: {len(sentences)} sentences vs {len(embeddings)} embeddings")
                continue
            
            # Merge sentences into chunks
            chunk_results = self.semantic_merger.merge_sentences(sentences, embeddings)
            
            # Convert to dictionary format for JSON serialization
            chunks = []
            for chunk_result in chunk_results:
                chunk_dict = {
                    'content': chunk_result.content,
                    'start_sentence': chunk_result.start_sentence,
                    'end_sentence': chunk_result.end_sentence,
                    'token_count': len(self.tokenizer.encode(chunk_result.content)),
                    'sentence_count': chunk_result.end_sentence - chunk_result.start_sentence + 1
                }
                chunks.append(chunk_dict)
            
            doc_chunks[doc_id] = chunks
            total_chunks += len(chunks)
            
            logger.debug(f"Document {doc_id}: {len(sentences)} sentences → {len(chunks)} chunks")
        
        logger.info(f"✅ Merged {len(doc_chunks)} documents into {total_chunks} chunks")
        return doc_chunks
    
    def save_artifacts(self, doc_sentences: Dict[str, List[str]], 
                      doc_embeddings: Dict[str, List[List[float]]],
                      doc_chunks: Dict[str, List[Dict[str, Any]]],
                      similarity_stats: Dict[str, Any],
                      input_file: str,
                      experiment_name: str = None) -> Dict[str, str]:
        """
        Save all intermediate artifacts for debugging and reuse.
        
        Args:
            doc_sentences: Document sentences from step 2
            doc_embeddings: Document embeddings from step 3
            doc_chunks: Document chunks from step 4
            similarity_stats: Similarity analysis results
            input_file: Original input file path
            experiment_name: Optional experiment name for file naming
            
        Returns:
            Dictionary of saved file paths
        """
        logger.info("💾 Saving artifacts")
        
        # Generate base filename from input file
        input_path = Path(input_file)
        base_name = input_path.stem
        
        # Add experiment name if provided
        if experiment_name:
            base_name = f"{base_name}_{experiment_name}"
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{base_name}_{timestamp}"
        
        saved_files = {}
        
        # Save sentences
        sentences_file = self.processed_dir / f"{base_name}_sentences.json"
        sentences_data = {
            'metadata': {
                'input_file': input_file,
                'experiment_name': experiment_name,
                'generated_at': datetime.now().isoformat(),
                'total_documents': len(doc_sentences),
                'total_sentences': sum(len(sentences) for sentences in doc_sentences.values())
            },
            'sentences': doc_sentences
        }
        
        with open(sentences_file, 'w', encoding='utf-8') as f:
            json.dump(sentences_data, f, indent=2, ensure_ascii=False)
        saved_files['sentences'] = str(sentences_file)
        
        # Save chunks (main output)
        chunks_file = self.processed_dir / f"{base_name}_chunks.json"
        chunks_data = {
            'metadata': {
                'input_file': input_file,
                'experiment_name': experiment_name,
                'config_params': self.config,
                'generated_at': datetime.now().isoformat(),
                'total_documents': len(doc_chunks),
                'total_chunks': sum(len(chunks) for chunks in doc_chunks.values())
            },
            'chunks': doc_chunks
        }
        
        with open(chunks_file, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)
        saved_files['chunks'] = str(chunks_file)
        
        # Save similarity analysis
        similarity_file = self.processed_dir / f"{base_name}_similarity_analysis.json"
        similarity_data = {
            'metadata': {
                'input_file': input_file,
                'experiment_name': experiment_name,
                'generated_at': datetime.now().isoformat(),
                'analysis_type': 'adjacent_sentence_similarity'
            },
            'similarity_stats': similarity_stats
        }
        
        with open(similarity_file, 'w', encoding='utf-8') as f:
            json.dump(similarity_data, f, indent=2, ensure_ascii=False)
        saved_files['similarity_analysis'] = str(similarity_file)
        
        # Save experiment log
        log_file = self.processed_dir / f"{base_name}_experiment_log.json"
        log_data = {
            'experiment_name': experiment_name,
            'input_file': input_file,
            'config_file': 'chunking_config.toml',
            'config_params': self.config,
            'results': {
                'total_documents': len(doc_chunks),
                'total_chunks': sum(len(chunks) for chunks in doc_chunks.values()),
                'avg_chunks_per_doc': sum(len(chunks) for chunks in doc_chunks.values()) / len(doc_chunks) if doc_chunks else 0
            },
            'artifacts': saved_files,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        saved_files['experiment_log'] = str(log_file)
        
        logger.info(f"✅ Saved {len(saved_files)} artifact files")
        for artifact_type, file_path in saved_files.items():
            logger.info(f"  {artifact_type}: {file_path}")
        
        return saved_files
    
    async def run_full_pipeline(self, input_file: str, experiment_name: Optional[str] = None) -> Dict[str, str]:
        """
        Run the complete 4-step chunking pipeline.
        
        All chunking parameters are read from the configuration file.
        
        Args:
            input_file: Path to collected documents JSON file
            experiment_name: Optional experiment name for file naming
            
        Returns:
            Dictionary of saved artifact file paths
        """
        start_time = time.time()
        logger.info(f"🚀 Starting full chunking pipeline for {input_file}")
        logger.info(f"📋 Using configuration: {self.config_loader.config_dir}/chunking_config.toml")
        
        # Log active configuration parameters
        config_params = self.config['semantic_merging']
        logger.info(f"🔧 Active parameters:")
        logger.info(f"  similarity_threshold: {config_params['similarity_threshold']}")
        logger.info(f"  max_merge_distance: {config_params['max_merge_distance']}")
        logger.info(f"  max_chunk_size: {config_params['max_chunk_size']}")
        
        try:
            # Step 1: Load documents
            documents = self.load_collected_documents(input_file)
            
            # Step 2: Split into sentences
            doc_sentences = self.split_documents_into_sentences(documents)
            
            # Step 3: Generate embeddings
            doc_embeddings = await self.generate_sentence_embeddings(doc_sentences)
            
            # Step 3.5: Analyze similarity distribution
            similarity_stats = self.analyze_similarity_distribution(doc_sentences, doc_embeddings)
            
            # Step 4: Merge sentences using config parameters
            doc_chunks = self.merge_semantic_sentences(doc_sentences, doc_embeddings)
            
            # Save artifacts
            saved_files = self.save_artifacts(
                doc_sentences, doc_embeddings, doc_chunks, similarity_stats,
                input_file, experiment_name
            )
            
            elapsed_time = time.time() - start_time
            logger.info(f"✅ Pipeline completed successfully in {elapsed_time:.2f} seconds")
            
            return saved_files
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {str(e)}")
            raise


async def main():
    """Main entry point for the orchestration script."""
    parser = argparse.ArgumentParser(
        description='Orchestrate the 4-step chunking workflow for evaluation dataset preparation. '
                   'All chunking parameters are controlled via the configuration file.'
    )
    parser.add_argument(
        '--input-file', 
        required=True,
        help='Path to JSON file containing collected documents from data_collector.py'
    )
    parser.add_argument(
        '--experiment-name', 
        help='Optional experiment name for file naming and organization'
    )
    parser.add_argument(
        '--config', 
        default='chunking_config.toml',
        help='Path to chunking configuration file (default: chunking_config.toml)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize orchestrator with config file
        orchestrator = ChunkingOrchestrator(args.config)
        
        # Log configuration being used
        print(f"📋 Using configuration file: {args.config}")
        print(f"📁 Processing input file: {args.input_file}")
        if args.experiment_name:
            print(f"🏷️  Experiment name: {args.experiment_name}")
        
        # Run pipeline
        saved_files = await orchestrator.run_full_pipeline(
            input_file=args.input_file,
            experiment_name=args.experiment_name
        )
        
        # Print results
        print("\n" + "="*60)
        print("📊 CHUNKING PIPELINE RESULTS")
        print("="*60)
        print(f"✅ Pipeline completed successfully!")
        print(f"📁 Saved artifacts:")
        for artifact_type, file_path in saved_files.items():
            print(f"  • {artifact_type}: {file_path}")
        print("="*60)
        
        # Show cache info
        cache_info = orchestrator.embedding_cache.get_cache_info()
        print(f"📊 Embedding cache: {cache_info['cached_sentences']} sentences cached")
        if 'stats' in cache_info and cache_info['stats']:
            hit_rate = cache_info['stats'].get('hit_rate', 0)
            print(f"🎯 Cache hit rate: {hit_rate:.2%}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        logger.error(f"Main execution failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())