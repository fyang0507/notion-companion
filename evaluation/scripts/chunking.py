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
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
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
from services.newline_splitter import NewlineSplitter
from services.sentence_embedding import SentenceEmbeddingCache
from services.semantic_merger import SemanticMerger
from utils.config_loader import ConfigLoader
from ingestion.services.openai_service import OpenAIService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UnifiedCacheManager:
    """Unified caching system for all pipeline steps with consistent naming and hashing."""
    
    def __init__(self, base_dir: Path, config: Dict[str, Any] = None):
        self.base_dir = base_dir
        self.cached_dir = base_dir
        self.config = config or {}
        
        # Create directories
        self.cached_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate experiment ID for this run
        self.experiment_id = datetime.now().strftime("%Y%m%d_%H%M")
        
    def _generate_content_hash(self, content: Any) -> str:
        """Generate consistent hash for any content."""
        if isinstance(content, str):
            content_str = content
        elif isinstance(content, (dict, list)):
            content_str = json.dumps(content, sort_keys=True, ensure_ascii=False)
        else:
            content_str = str(content)
        
        return hashlib.sha256(content_str.encode('utf-8')).hexdigest()[:16]
    
    def _sort_config(self, config_dict):
        """Sort config dictionary for consistent comparison."""
        sorted_dict = {}
        for key, value in config_dict.items():
            if isinstance(value, list):
                # Handle nested lists (like quote_pairs which is list of lists)
                if all(isinstance(item, list) for item in value):
                    sorted_dict[key] = sorted([sorted(item) for item in value])
                else:
                    sorted_dict[key] = sorted(value)
            else:
                sorted_dict[key] = value
        return sorted_dict
    
    def _generate_step_filename(self, step_num: int, step_name: str, experiment_name: str = None) -> str:
        """Generate consistent filename for pipeline steps."""
        base = f"{self.experiment_id}_step{step_num}_{step_name}"
        if experiment_name:
            base = f"{base}_{experiment_name}"
        return f"{base}.json"
    
    def save_step_data(self, step_num: int, step_name: str, data: Dict[str, Any], 
                      experiment_name: str = None, include_hashes: bool = True, input_file: str = None) -> str:
        """
        Save step data with consistent format and optional content hashing.
        
        Args:
            step_num: Pipeline step number (1-4)
            step_name: Human-readable step name
            data: Data to save
            experiment_name: Optional experiment name
            include_hashes: Whether to generate content hashes for traceability
            input_file: Input file path for configuration hash generation
            
        Returns:
            Path to saved file
        """
        filename = self._generate_step_filename(step_num, step_name, experiment_name)
        filepath = self.cached_dir / filename
        
        # Create configuration snapshot for cache reuse (include full config for unified cache detection)
        if step_num in [2, 3, 4]:  # Steps that participate in unified caching
            config_snapshot = {
                'step_number': step_num,
                'input_file': input_file,
                'timestamp': datetime.now().isoformat(),
                'chunking_config': self._sort_config(self.config.get('chunking', {})),
                'embeddings_config': self._sort_config(self.config.get('embeddings', {}))
                # Note: semantic_merging config excluded - only affects Step 5 which always runs
            }
        else:
            config_snapshot = {
                'step_number': step_num,
                'input_file': input_file,
                'timestamp': datetime.now().isoformat()
            }
        
        # Create unified metadata structure
        metadata = {
            'step_number': step_num,
            'step_name': step_name,
            'experiment_id': self.experiment_id,
            'experiment_name': experiment_name,
            'generated_at': datetime.now().isoformat(),
            'config_snapshot': config_snapshot,
            'content_hash': self._generate_content_hash(data) if include_hashes else None,
            'data_keys': list(data.keys()) if isinstance(data, dict) else None
        }
        
        # Add content hashes for individual items if requested
        if include_hashes and isinstance(data, dict):
            content_hashes = {}
            for key, value in data.items():
                if isinstance(value, (list, dict)):
                    content_hashes[key] = self._generate_content_hash(value)
            metadata['item_hashes'] = content_hashes
        
        # Save with unified structure
        save_data = {
            'metadata': metadata,
            'data': data
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Saved Step {step_num} ({step_name}): {filepath}")
        return str(filepath)
    
    def load_step_data(self, step_num: int, step_name: str, experiment_name: str = None) -> Dict[str, Any]:
        """Load step data with error handling."""
        filename = self._generate_step_filename(step_num, step_name, experiment_name)
        filepath = self.cached_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Step {step_num} data not found: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
        
        return loaded_data['data']
    
    
    def get_cache_summary(self) -> Dict[str, Any]:
        """Get summary of all cached data for this experiment."""
        cache_files = list(self.cached_dir.glob(f"{self.experiment_id}_step*.json"))
        
        summary = {
            'experiment_id': self.experiment_id,
            'total_step_files': len(cache_files),
            'steps_cached': [],
            'cached_dir': str(self.cached_dir)
        }
        
        for file_path in sorted(cache_files):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    metadata = data.get('metadata', {})
                    summary['steps_cached'].append({
                        'step_number': metadata.get('step_number'),
                        'step_name': metadata.get('step_name'),
                        'file_path': str(file_path),
                        'file_size_mb': file_path.stat().st_size / (1024*1024),
                        'generated_at': metadata.get('generated_at')
                    })
            except Exception as e:
                logger.warning(f"Could not read cache file {file_path}: {e}")
        
        return summary


class ChunkingOrchestrator:
    """Orchestrates the 4-step chunking workflow for evaluation dataset preparation."""
    
    def __init__(self, config_path: str = "chunking_config.toml"):
        """Initialize orchestrator with configuration."""
        self.config_loader = ConfigLoader()
        self.config = self.config_loader.load_chunking_config(config_path)
        
        # Initialize unified cache manager with config
        self.data_dir = Path(__file__).parent.parent / "data"
        self.cache_manager = UnifiedCacheManager(self.data_dir, self.config)
        
        # Initialize components
        self._initialize_splitter()
        self.embedding_cache = SentenceEmbeddingCache(self.config)
        self.openai_service = OpenAIService()
        
        # Initialize tokenizer for semantic merger
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.semantic_merger = SemanticMerger(self.tokenizer, self.config)
        
        logger.info(f"ChunkingOrchestrator initialized successfully (Experiment ID: {self.cache_manager.experiment_id})")
    
    def _initialize_splitter(self):
        """Initialize the text splitter based on configuration."""
        splitter_method = self.config.get('chunking', {}).get('splitter_method', 'sentence')
        
        if splitter_method == 'sentence':
            self.text_splitter = RobustSentenceSplitter(self.config)
            logger.info("Using RobustSentenceSplitter for text splitting")
        elif splitter_method == 'newline':
            self.text_splitter = NewlineSplitter(self.config)
            logger.info("Using NewlineSplitter for text splitting")
        else:
            raise ValueError(f"Unknown splitter method: {splitter_method}. Must be 'sentence' or 'newline'")
        
        self.splitter_method = splitter_method
    
    def _create_config_fingerprint(self, input_file: str = None) -> Dict[str, Any]:
        """Create a configuration fingerprint for Steps 2-4 cache matching."""
        # Sort lists deterministically to ensure consistent comparison
        def sort_config(config_dict):
            sorted_dict = {}
            for key, value in config_dict.items():
                if isinstance(value, list):
                    # Handle nested lists (like quote_pairs which is list of lists)
                    if all(isinstance(item, list) for item in value):
                        sorted_dict[key] = sorted([sorted(item) for item in value])
                    else:
                        sorted_dict[key] = sorted(value)
                else:
                    sorted_dict[key] = value
            return sorted_dict
        
        fingerprint = {
            'input_file': input_file,
            'chunking_config': sort_config(self.config.get('chunking', {})),
            'embeddings_config': sort_config(self.config.get('embeddings', {}))
            # Note: semantic_merging config is excluded as it only affects Step 5 (always runs)
        }
        
        return fingerprint
    
    def _check_cached_pipeline_stage(self, experiment_name: str = None, input_file: str = None) -> Tuple[bool, Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        """
        Check if Steps 2-4 can be loaded from cache with matching configuration.
        
        Returns:
            Tuple of (cache_matches, step2_data, step3_data, step4_data)
        """
        current_fingerprint = self._create_config_fingerprint(input_file)
        
        # Look for Step 3 cache file (the expensive one that determines if we can reuse)
        pattern = f"*_step3_embedding_generation_*.json"
        if experiment_name:
            pattern = f"*_step3_embedding_generation_{experiment_name}.json"
        
        cache_files = list(self.cache_manager.cached_dir.glob(pattern))
        
        if not cache_files:
            logger.info("🔍 No Step 3 cache found - will run full pipeline from Step 2")
            return False, {}, {}, {}
        
        # Get the most recent cache file
        latest_cache = max(cache_files, key=lambda f: f.stat().st_mtime)
        
        try:
            with open(latest_cache, 'r', encoding='utf-8') as f:
                step3_data = json.load(f)
            
            # Compare config fingerprints (excluding timestamp)
            cached_config = step3_data.get('metadata', {}).get('config_snapshot', {})
            cached_fingerprint = {
                'input_file': cached_config.get('input_file'),
                'chunking_config': cached_config.get('chunking_config', {}),
                'embeddings_config': cached_config.get('embeddings_config', {})
            }
            
            if current_fingerprint == cached_fingerprint:
                logger.info(f"✅ Found matching cache for Steps 2-4: {latest_cache.name}")
                
                # Load corresponding Step 2 and Step 4 data  
                # Extract experiment ID (e.g., "20250708_1521" from "20250708_1521_step3_embedding_generation_test.json")
                exp_id = '_'.join(latest_cache.name.split('_')[:2])
                step2_pattern = f"{exp_id}_step2_*_splitting_*.json"
                step4_pattern = f"{exp_id}_step4_similarity_analysis_*.json"
                
                step2_files = list(self.cache_manager.cached_dir.glob(step2_pattern))
                step4_files = list(self.cache_manager.cached_dir.glob(step4_pattern))
                
                logger.info(f"🔍 Looking for Step 2: {step2_pattern}, found {len(step2_files)} files")
                logger.info(f"🔍 Looking for Step 4: {step4_pattern}, found {len(step4_files)} files")
                
                step2_data = {}
                step4_data = {}
                
                if step2_files:
                    with open(step2_files[0], 'r', encoding='utf-8') as f:
                        step2_full = json.load(f)
                        step2_data = step2_full.get('data', {})
                    logger.info(f"  ✅ Step 2: {step2_files[0].name}")
                
                if step4_files:
                    with open(step4_files[0], 'r', encoding='utf-8') as f:
                        step4_full = json.load(f)
                        step4_data = step4_full.get('data', {})
                    logger.info(f"  ✅ Step 4: {step4_files[0].name}")
                
                # Extract data from step3 as well
                step3_data = step3_data.get('data', {})
                
                return True, step2_data, step3_data, step4_data
            else:
                logger.info(f"❌ Step 3 cache found but config doesn't match - will regenerate from Step 2")
                logger.info(f"🔍 Current fingerprint: {current_fingerprint}")
                logger.info(f"🔍 Cached fingerprint: {cached_fingerprint}")
                return False, {}, {}, {}
                
        except Exception as e:
            logger.warning(f"⚠️  Error reading Step 3 cache {latest_cache}: {e}")
            return False, {}, {}, {}

    def load_collected_documents(self, input_file: str) -> Tuple[List[Dict[str, Any]], str, Dict[str, Dict[str, Any]]]:
        """
        Step 1: Load documents from data_collector.py output.
        
        Args:
            input_file: Path to JSON file containing collected documents
            
        Returns:
            Tuple of (List of document dictionaries, database_id, document_metadata_map)
        """
        logger.info(f"📖 Step 1: Loading collected documents from {input_file}")
        
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        documents = data.get('documents', [])
        database_id = data.get('database_id', 'unknown')
        
        # Create document metadata map for easy lookup
        document_metadata_map = {}
        for doc in documents:
            doc_id = doc['id']
            document_metadata_map[doc_id] = {
                'title': doc.get('title', 'Untitled'),
                'url': doc.get('url'),
                'created_time': doc.get('created_time'),
                'last_edited_time': doc.get('last_edited_time'),
                'extracted_metadata': doc.get('extracted_metadata', {}),
                'content_length': doc.get('content_length'),
                'has_multimedia': doc.get('has_multimedia', False),
                'multimedia_refs': doc.get('multimedia_refs', []),
                'database_id': doc.get('database_id', database_id)
            }
        
        logger.info(f"✅ Loaded {len(documents)} documents from database {database_id}")
        logger.info(f"📋 Document metadata preserved for {len(document_metadata_map)} documents")
        
        return documents, database_id, document_metadata_map
    
    def split_documents_into_text_units(self, documents: List[Dict[str, Any]], document_metadata_map: Dict[str, Dict[str, Any]], experiment_name: str = None, input_file: str = None) -> Dict[str, List[str]]:
        """
        Step 2: Split documents into text chunks using configured splitter.
        
        Args:
            documents: List of document dictionaries
            document_metadata_map: Mapping of document_id to metadata
            experiment_name: Optional experiment name for saving
            input_file: Input file path for metadata
            
        Returns:
            Dictionary mapping document_id to list of text chunks
        """
        logger.info(f"✂️ Step 2: Splitting documents using {self.splitter_method} splitter")
        
        doc_text_units = {}
        total_text_units = 0
        
        for doc in documents:
            doc_id = doc['id']
            content = doc['content']
            
            if not content or not content.strip():
                logger.warning(f"Skipping empty document: {doc_id}")
                continue
            
            text_units = self.text_splitter.split(content)
            doc_text_units[doc_id] = text_units
            total_text_units += len(text_units)
            
            logger.debug(f"Document {doc_id}: {len(text_units)} text chunks")
        
        # Create indexed text unit data with hashes for cross-step linking
        indexed_text_units = {}
        text_unit_lookup = {}  # For easy manual analysis
        
        for doc_id, text_units in doc_text_units.items():
            doc_indexed_text_units = {}
            for i, text_unit in enumerate(text_units):
                text_unit_hash = self.cache_manager._generate_content_hash(text_unit)
                text_unit_info = {
                    'index': i,
                    'content': text_unit,
                    'hash': text_unit_hash,
                    'char_length': len(text_unit),
                    'word_count': len(text_unit.split()),
                    'document_metadata': document_metadata_map.get(doc_id, {})  # Include document metadata
                }
                doc_indexed_text_units[i] = text_unit_info
                
                # Add to global lookup for easy access
                text_unit_lookup[text_unit_hash] = {
                    'document_id': doc_id,
                    'text_unit_index': i,
                    'content': text_unit,
                    'document_metadata': document_metadata_map.get(doc_id, {})
                }
            
            indexed_text_units[doc_id] = doc_indexed_text_units
        
        # Save step data with enhanced indexing and document metadata
        step_data = {
            'document_sentences': indexed_text_units,
            'sentence_lookup': text_unit_lookup,  # Global hash -> text unit mapping
            'input_documents': {doc['id']: {'title': doc.get('title', 'Untitled'), 'content_length': len(doc['content'])} for doc in documents},
            'document_metadata_map': document_metadata_map,  # Preserve full metadata
            'statistics': {
                'total_documents': len(doc_text_units),
                'total_text_units': total_text_units,
                'avg_text_units_per_doc': total_text_units / len(doc_text_units) if doc_text_units else 0
            }
        }
        
        step_name = f"{self.splitter_method}_splitting"
        self.cache_manager.save_step_data(2, step_name, step_data, experiment_name, input_file=input_file)
        
        logger.info(f"✅ Split {len(doc_text_units)} documents into {total_text_units} text chunks")
        return doc_text_units
    
    async def generate_text_unit_embeddings(self, doc_text_units: Dict[str, List[str]], document_metadata_map: Dict[str, Dict[str, Any]], experiment_name: str = None, input_file: str = None) -> Dict[str, List[List[float]]]:
        """
        Step 3: Generate embeddings for text units using sentence_embedding.py.
        
        Args:
            doc_text_units: Dictionary mapping document_id to list of text units
            document_metadata_map: Mapping of document_id to metadata
            experiment_name: Optional experiment name for saving
            input_file: Input file path for metadata
            
        Returns:
            Dictionary mapping document_id to list of embeddings
        """
        logger.info("🔢 Step 3: Generating sentence embeddings")
        
        doc_embeddings = {}
        total_cache_hits = 0
        total_cache_misses = 0
        text_unit_hashes = {}
        
        for doc_id, text_units in doc_text_units.items():
            if not text_units:
                logger.warning(f"Skipping document with no text units: {doc_id}")
                continue
            
            logger.info(f"Processing embeddings for document {doc_id} ({len(text_units)} text units)")
            
            # Generate embeddings with caching
            embeddings, cache_hits, cache_misses = await self.embedding_cache.get_embeddings(
                text_units, self.openai_service
            )
            
            doc_embeddings[doc_id] = embeddings
            total_cache_hits += cache_hits
            total_cache_misses += cache_misses
            
            # Generate enhanced text unit metadata with embeddings
            doc_text_unit_metadata = {}
            for i, text_unit in enumerate(text_units):
                text_unit_hash = self.cache_manager._generate_content_hash(text_unit)
                embedding = embeddings[i] if i < len(embeddings) else None
                doc_text_unit_metadata[i] = {
                    'index': i,
                    'content': text_unit,
                    'hash': text_unit_hash,
                    'embedding': embedding,
                    'embedding_dimensions': len(embedding) if embedding else 0,
                    'char_length': len(text_unit),
                    'word_count': len(text_unit.split()),
                    'document_metadata': document_metadata_map.get(doc_id, {})  # Include document metadata
                }
            text_unit_hashes[doc_id] = doc_text_unit_metadata
            
            logger.debug(f"Document {doc_id}: {cache_hits} cache hits, {cache_misses} cache misses")
        
        # Create global text unit lookup with embeddings for manual analysis
        global_text_unit_lookup = {}
        for doc_id, doc_metadata in text_unit_hashes.items():
            for text_unit_idx, text_unit_info in doc_metadata.items():
                hash_key = text_unit_info['hash']
                global_text_unit_lookup[hash_key] = {
                    'document_id': doc_id,
                    'text_unit_index': text_unit_idx,
                    'content': text_unit_info['content'],
                    'embedding': text_unit_info['embedding'],
                    'char_length': text_unit_info['char_length'],
                    'word_count': text_unit_info['word_count'],
                    'document_metadata': text_unit_info['document_metadata']
                }
        
        # Save step data with unified caching including text unit hashes
        step_data = {
            'document_embeddings': doc_embeddings,
            'sentence_metadata': text_unit_hashes,
            'global_sentence_lookup': global_text_unit_lookup,  # Easy hash-based lookup
            'document_metadata_map': document_metadata_map,  # Preserve metadata
            'embedding_statistics': {
                'total_documents': len(doc_embeddings),
                'total_embeddings': sum(len(embs) for embs in doc_embeddings.values()),
                'cache_hits': total_cache_hits,
                'cache_misses': total_cache_misses,
                'cache_hit_rate': total_cache_hits / (total_cache_hits + total_cache_misses) if (total_cache_hits + total_cache_misses) > 0 else 0,
                'embedding_model': self.config['embeddings']['model'],
                'embedding_dimensions': len(next(iter(doc_embeddings.values()))[0]) if doc_embeddings and next(iter(doc_embeddings.values())) else 0
            }
        }
        
        self.cache_manager.save_step_data(3, "embedding_generation", step_data, experiment_name, input_file=input_file)
        
        logger.info(f"✅ Generated embeddings for {len(doc_embeddings)} documents")
        logger.info(f"📊 Cache performance: {total_cache_hits} hits, {total_cache_misses} misses")
        
        return doc_embeddings
    
    def analyze_similarity_distribution(self, doc_text_units: Dict[str, List[str]], 
                                      doc_embeddings: Dict[str, List[List[float]]], 
                                      experiment_name: str = None, document_metadata_map: Dict[str, Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze similarity distribution of adjacent text units to inform threshold tuning.
        
        Args:
            doc_text_units: Dictionary mapping document_id to list of text units
            doc_embeddings: Dictionary mapping document_id to list of embeddings
            
        Returns:
            Dictionary containing similarity statistics and distribution
        """
        logger.info("📊 Analyzing similarity distribution of adjacent sentences")
        
        all_similarities = []
        doc_stats = {}
        
        for doc_id in doc_text_units.keys():
            if doc_id not in doc_embeddings:
                continue
                
            text_units = doc_text_units[doc_id]
            embeddings = doc_embeddings[doc_id]
            
            if len(text_units) < 2 or len(embeddings) < 2:
                continue
            
            # Calculate cosine similarity for adjacent text units
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
                'text_unit_count': len(text_units),
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
            test_thresholds = [0.25, 0.5, 0.75, 0.8, 0.9]
            
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
                'percentiles': dict(zip([str(p) for p in percentiles], percentile_values)),
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
            logger.info(f"  Conservative (25% merge): {percentile_values[percentiles.index(75)]:.3f}")
            logger.info(f"  Moderate (50% merge): {percentile_values[percentiles.index(50)]:.3f}")
            logger.info(f"  Aggressive (75% merge): {percentile_values[percentiles.index(25)]:.3f}")
            
            result = {
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
            result = {
                'overall_stats': {},
                'document_stats': doc_stats,
                'recommendations': {}
            }
        
        # Save step data with unified caching (Step 3.5)
        step_data = {
            'similarity_analysis': result,
            'analysis_metadata': {
                'total_documents_analyzed': len(doc_stats),
                'analysis_type': 'adjacent_sentence_similarity',
                'similarity_metric': 'cosine_similarity',
                'percentiles_calculated': [10, 25, 50, 75, 90, 95, 99],
                'test_thresholds': [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]
            }
        }
        
        self.cache_manager.save_step_data(4, "similarity_analysis", step_data, experiment_name)
        
        return result
    
    def merge_semantic_text_units(self, doc_text_units: Dict[str, List[str]], 
                               doc_embeddings: Dict[str, List[List[float]]], 
                               document_metadata_map: Dict[str, Dict[str, Any]],
                               experiment_name: str = None, database_id: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Step 4: Merge semantically similar text units using semantic_merger.py.
        
        Uses configuration values from chunking_config.toml. No parameter overrides allowed.
        
        Args:
            doc_text_units: Dictionary mapping document_id to list of text units
            doc_embeddings: Dictionary mapping document_id to list of embeddings
            document_metadata_map: Mapping of document_id to metadata
            
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
        aggregate_stats = {'total_chunks': 0, 'single_text_unit_chunks': 0, 'stopped_by_similarity': 0, 'stopped_by_token_limit': 0, 'stopped_by_distance_limit': 0, 'stopped_by_end_of_text_units': 0}
        
        for doc_id in doc_text_units.keys():
            if doc_id not in doc_embeddings:
                logger.warning(f"Skipping document without embeddings: {doc_id}")
                continue
            
            text_units = doc_text_units[doc_id]
            embeddings = doc_embeddings[doc_id]
            
            if len(text_units) != len(embeddings):
                logger.error(f"Mismatch in document {doc_id}: {len(text_units)} text units vs {len(embeddings)} embeddings")
                continue
            
            # Merge text units into chunks
            chunk_results, doc_stats = self.semantic_merger.merge_sentences(text_units, embeddings)
            
            # Aggregate statistics across all documents
            aggregate_stats['total_chunks'] += doc_stats.total_chunks
            aggregate_stats['single_text_unit_chunks'] += doc_stats.single_sentence_chunks
            aggregate_stats['stopped_by_similarity'] += doc_stats.stopped_by_similarity
            aggregate_stats['stopped_by_token_limit'] += doc_stats.stopped_by_token_limit
            aggregate_stats['stopped_by_distance_limit'] += doc_stats.stopped_by_distance_limit
            aggregate_stats['stopped_by_end_of_text_units'] += doc_stats.stopped_by_end_of_sentences
            
            # Convert to dictionary format for JSON serialization WITH METADATA
            chunks = []
            for chunk_result in chunk_results:
                chunk_dict = {
                    'content': chunk_result.content,
                    'start_sentence': chunk_result.start_sentence,
                    'end_sentence': chunk_result.end_sentence,
                    'token_count': len(self.tokenizer.encode(chunk_result.content)),
                    'text_unit_count': chunk_result.end_sentence - chunk_result.start_sentence + 1,
                    'document_metadata': document_metadata_map.get(doc_id, {}),  # Include document metadata
                    'document_id': doc_id  # Add document ID for reference
                }
                chunks.append(chunk_dict)
            
            doc_chunks[doc_id] = chunks
            total_chunks += len(chunks)
            
            logger.debug(f"Document {doc_id}: {len(text_units)} text units → {len(chunks)} chunks")
        
        # Save step data with unified caching
        chunk_hashes = {}
        for doc_id, chunks in doc_chunks.items():
            doc_chunk_hashes = {}
            for i, chunk in enumerate(chunks):
                chunk_hash = self.cache_manager._generate_content_hash(chunk['content'])
                doc_chunk_hashes[i] = {
                    'chunk_hash': chunk_hash,
                    'token_count': chunk['token_count'],
                    'text_unit_count': chunk['text_unit_count'],
                    'start_sentence': chunk['start_sentence'],
                    'end_sentence': chunk['end_sentence'],
                    'document_metadata': chunk['document_metadata']
                }
            chunk_hashes[doc_id] = doc_chunk_hashes
        
        # Calculate merge stopping percentages
        stopping_percentages = {}
        if aggregate_stats['total_chunks'] > 0:
            stopping_percentages = {
                'single_text_unit': (aggregate_stats['single_text_unit_chunks'] / aggregate_stats['total_chunks']) * 100,
                'similarity_threshold': (aggregate_stats['stopped_by_similarity'] / aggregate_stats['total_chunks']) * 100,
                'token_limit': (aggregate_stats['stopped_by_token_limit'] / aggregate_stats['total_chunks']) * 100,
                'distance_limit': (aggregate_stats['stopped_by_distance_limit'] / aggregate_stats['total_chunks']) * 100,
                'end_of_text_units': (aggregate_stats['stopped_by_end_of_text_units'] / aggregate_stats['total_chunks']) * 100
            }
        
        # Calculate detailed distribution statistics for chunk analysis
        all_chunk_tokens = []
        all_chunk_text_unit_counts = []
        for chunks in doc_chunks.values():
            for chunk in chunks:
                all_chunk_tokens.append(chunk['token_count'])
                all_chunk_text_unit_counts.append(chunk['text_unit_count'])
        
        def calculate_distribution_stats(values, name):
            if not values:
                return {}
            
            values_array = np.array(values)
            percentiles = [10, 25, 50, 75, 90, 95, 99]
            percentile_values = np.percentile(values_array, percentiles)
            
            return {
                f'{name}_count': len(values),
                f'{name}_min': int(np.min(values_array)),
                f'{name}_max': int(np.max(values_array)),
                f'{name}_mean': float(np.mean(values_array)),
                f'{name}_median': float(np.median(values_array)),
                f'{name}_std': float(np.std(values_array)),
                f'{name}_percentiles': {
                    str(p): float(v) for p, v in zip(percentiles, percentile_values)
                },
                f'{name}_quartiles': {
                    'q1': float(np.percentile(values_array, 25)),
                    'q2': float(np.percentile(values_array, 50)),
                    'q3': float(np.percentile(values_array, 75)),
                    'iqr': float(np.percentile(values_array, 75) - np.percentile(values_array, 25))
                }
            }
        
        token_distribution = calculate_distribution_stats(all_chunk_tokens, 'tokens')
        text_unit_distribution = calculate_distribution_stats(all_chunk_text_unit_counts, 'text_units')
        
        step_data = {
            'document_chunks': doc_chunks,
            'chunk_metadata': chunk_hashes,
            'database_id': database_id,
            'document_metadata_map': document_metadata_map,  # Preserve metadata
            'merging_statistics': {
                'total_documents': len(doc_chunks),
                'total_chunks': total_chunks,
                'avg_chunks_per_doc': total_chunks / len(doc_chunks) if doc_chunks else 0,
                'total_input_text_units': sum(len(text_units) for text_units in doc_text_units.values()),
                'merge_reduction_rate': 1 - (total_chunks / sum(len(text_units) for text_units in doc_text_units.values())) if doc_text_units else 0,
                'merge_stopping_statistics': aggregate_stats,
                'merge_stopping_percentages': stopping_percentages,
                # Detailed distribution statistics
                'chunk_size_distribution': token_distribution,
                'text_unit_distribution': text_unit_distribution,
                'config_used': {
                    'similarity_threshold': self.config['semantic_merging']['similarity_threshold'],
                    'max_merge_distance': self.config['semantic_merging']['max_merge_distance'],
                    'max_chunk_size': self.config['semantic_merging']['max_chunk_size']
                }
            }
        }
        
        self.cache_manager.save_step_data(5, "semantic_merging", step_data, experiment_name)
        
        # Log merge stopping statistics
        if aggregate_stats['total_chunks'] > 0:
            logger.info(f"📊 Chunk stopping reasons (out of {aggregate_stats['total_chunks']} chunks):")
            logger.info(f"   • Single text unit: {stopping_percentages['single_text_unit']:.1f}% ({aggregate_stats['single_text_unit_chunks']} chunks)")
            logger.info(f"   • Similarity threshold: {stopping_percentages['similarity_threshold']:.1f}% ({aggregate_stats['stopped_by_similarity']} chunks)")
            logger.info(f"   • Token limit: {stopping_percentages['token_limit']:.1f}% ({aggregate_stats['stopped_by_token_limit']} chunks)")
            logger.info(f"   • Distance limit: {stopping_percentages['distance_limit']:.1f}% ({aggregate_stats['stopped_by_distance_limit']} chunks)")
            logger.info(f"   • End of text units: {stopping_percentages['end_of_text_units']:.1f}% ({aggregate_stats['stopped_by_end_of_text_units']} chunks)")
        
        logger.info(f"✅ Merged {len(doc_chunks)} documents into {total_chunks} chunks")
        return doc_chunks
    
    
    async def run_full_pipeline(self, input_file: str, experiment_name: Optional[str] = None, config_file: str = "config/chunking_config.toml") -> Dict[str, Any]:
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
        logger.info(f"📋 Using configuration: {config_file}")
        
        # Log active configuration parameters
        config_params = self.config['semantic_merging']
        logger.info(f"🔧 Active parameters:")
        logger.info(f"  similarity_threshold: {config_params['similarity_threshold']}")
        logger.info(f"  max_merge_distance: {config_params['max_merge_distance']}")
        logger.info(f"  max_chunk_size: {config_params['max_chunk_size']}")
        
        try:
            # Step 1: Load documents
            documents, database_id, document_metadata_map = self.load_collected_documents(input_file)
            
            # Check for Step 3 cache with matching config (simplified two-stage approach)
            cache_matched, step2_data, step3_data, step4_data = self._check_cached_pipeline_stage(experiment_name, input_file)
            
            if cache_matched:
                # Use cached data for Steps 2-4
                logger.info("♻️ Using cached data for Steps 2-4 (config matched)")
                
                # Extract data from cached steps
                doc_text_units = {}
                if 'document_sentences' in step2_data:
                    # Convert indexed text units back to simple lists
                    for doc_id, indexed_text_units in step2_data['document_sentences'].items():
                        doc_text_units[doc_id] = [unit_info['content'] for unit_info in indexed_text_units.values()]
                
                doc_embeddings = step3_data.get('document_embeddings', {})
                similarity_stats = step4_data.get('similarity_analysis', {})
                
                # Get metadata from cached data if available
                cached_metadata = step2_data.get('document_metadata_map', {})
                if cached_metadata:
                    document_metadata_map = cached_metadata
                
                logger.info(f"♻️ Loaded: {len(doc_text_units)} documents, {sum(len(s) for s in doc_text_units.values())} text units, {len(doc_embeddings)} embedding sets")
                
            else:
                # Run Steps 2-4 from scratch (bypassing individual step caching)
                logger.info("🔄 Running Steps 2-4 from scratch (no matching cache)")
                
                # Step 2: Split into sentences
                doc_text_units = self.split_documents_into_text_units(documents, document_metadata_map, experiment_name, input_file)
                
                # Step 3: Generate embeddings
                doc_embeddings = await self.generate_text_unit_embeddings(doc_text_units, document_metadata_map, experiment_name, input_file)
                
                # Step 4: Analyze similarity distribution
                similarity_stats = self.analyze_similarity_distribution(doc_text_units, doc_embeddings, experiment_name, document_metadata_map)
            
            # Step 5: Always run semantic merging (fast and shows current results)
            logger.info("🔄 Running Step 5: Semantic merging (always executed)")
            doc_chunks = self.merge_semantic_text_units(doc_text_units, doc_embeddings, document_metadata_map, experiment_name, database_id)
            
            # Load step 5 data to get merge stopping statistics
            try:
                step5_data = self.cache_manager.load_step_data(5, "semantic_merging", experiment_name)
                logger.info(f"✅ Successfully loaded step 5 data for merge stopping statistics")
            except FileNotFoundError as e:
                logger.warning(f"Step 5 data not found for merge stopping statistics: {e}")
                step5_data = None
            
            # Get cache summary and add merging statistics
            cache_summary = self.cache_manager.get_cache_summary()
            
            # Calculate overall merging statistics
            total_input_text_units = sum(len(text_units) for text_units in doc_text_units.values())
            total_output_chunks = sum(len(chunks) for chunks in doc_chunks.values())
            reduction_rate = 1 - (total_output_chunks / total_input_text_units) if total_input_text_units > 0 else 0
            
            # Calculate chunk size statistics
            all_chunk_tokens = []
            all_chunk_text_unit_counts = []
            for chunks in doc_chunks.values():
                for chunk in chunks:
                    all_chunk_tokens.append(chunk['token_count'])
                    all_chunk_text_unit_counts.append(chunk['text_unit_count'])
            
            # Calculate detailed distribution statistics
            def calculate_distribution_stats(values, name):
                if not values:
                    return {}
                
                values_array = np.array(values)
                percentiles = [10, 25, 50, 75, 90, 95, 99]
                percentile_values = np.percentile(values_array, percentiles)
                
                return {
                    f'{name}_count': len(values),
                    f'{name}_min': int(np.min(values_array)),
                    f'{name}_max': int(np.max(values_array)),
                    f'{name}_mean': float(np.mean(values_array)),
                    f'{name}_median': float(np.median(values_array)),
                    f'{name}_std': float(np.std(values_array)),
                    f'{name}_percentiles': {
                        str(p): float(v) for p, v in zip(percentiles, percentile_values)
                    },
                    f'{name}_quartiles': {
                        'q1': float(np.percentile(values_array, 25)),
                        'q2': float(np.percentile(values_array, 50)),
                        'q3': float(np.percentile(values_array, 75)),
                        'iqr': float(np.percentile(values_array, 75) - np.percentile(values_array, 25))
                    }
                }
            
            # Calculate distribution stats for both metrics
            token_distribution = calculate_distribution_stats(all_chunk_tokens, 'tokens')
            text_unit_distribution = calculate_distribution_stats(all_chunk_text_unit_counts, 'text_units')
            
            # Add merging statistics to cache summary
            cache_summary['merging_statistics'] = {
                'total_input_text_units': total_input_text_units,
                'total_output_chunks': total_output_chunks,
                'reduction_rate': reduction_rate,
                'reduction_percentage': reduction_rate * 100,
                # Legacy simple stats (for backward compatibility)
                'avg_chunk_tokens': sum(all_chunk_tokens) / len(all_chunk_tokens) if all_chunk_tokens else 0,
                'max_chunk_tokens': max(all_chunk_tokens) if all_chunk_tokens else 0,
                'min_chunk_tokens': min(all_chunk_tokens) if all_chunk_tokens else 0,
                'avg_text_units_per_chunk': sum(all_chunk_text_unit_counts) / len(all_chunk_text_unit_counts) if all_chunk_text_unit_counts else 0,
                'max_text_units_per_chunk': max(all_chunk_text_unit_counts) if all_chunk_text_unit_counts else 0,
                'min_text_units_per_chunk': min(all_chunk_text_unit_counts) if all_chunk_text_unit_counts else 0,
                # Detailed distribution statistics
                'chunk_size_distribution': token_distribution,
                'text_unit_distribution': text_unit_distribution,
                'merge_stopping_statistics': step5_data['merging_statistics']['merge_stopping_statistics'] if step5_data else {},
                'merge_stopping_percentages': step5_data['merging_statistics']['merge_stopping_percentages'] if step5_data else {},
                'config_used': {
                    'similarity_threshold': self.config['semantic_merging']['similarity_threshold'],
                    'max_merge_distance': self.config['semantic_merging']['max_merge_distance'],
                    'max_chunk_size': self.config['semantic_merging']['max_chunk_size']
                }
            }
            
            # Add similarity analysis to cache summary (whether from cache or freshly generated)
            cache_summary['similarity_analysis'] = similarity_stats
            
            # Add information about cache usage
            cache_summary['cache_usage'] = {
                'steps_2_4_cached': cache_matched,
                'step_5_always_fresh': True,
                'cache_reason': 'semantic_merging_config_only_changed' if cache_matched else 'no_matching_cache_found'
            }
            
            elapsed_time = time.time() - start_time
            cache_summary['pipeline_execution_time'] = elapsed_time
            logger.info(f"✅ Pipeline completed successfully in {elapsed_time:.2f} seconds")
            
            return cache_summary
            
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
        cache_summary = await orchestrator.run_full_pipeline(
            input_file=args.input_file,
            experiment_name=args.experiment_name,
            config_file=args.config
        )
        
        # Print results
        print("\n" + "="*60)
        print("📊 CHUNKING PIPELINE RESULTS")
        print("="*60)
        print(f"✅ Pipeline completed successfully!")
        
        try:
            print(f"🆔 Experiment ID: {cache_summary['experiment_id']}")
            print(f"📁 Step files created: {cache_summary['total_step_files']}")
            print(f"📂 Cache directory: {cache_summary['cached_dir']}")
            
            # Show cache usage information
            if 'cache_usage' in cache_summary:
                cache_usage = cache_summary['cache_usage']
                if cache_usage['steps_2_4_cached']:
                    print(f"♻️ Cache usage: Steps 2-4 loaded from cache, Step 5 regenerated")
                else:
                    print(f"🔄 Cache usage: All steps executed from scratch")
            
            print("\n📋 Step-by-step artifacts:")
            for step in cache_summary['steps_cached']:
                print(f"  • Step {step['step_number']} ({step['step_name']}): {step['file_size_mb']:.2f} MB")
        except Exception as e:
            logger.error(f"Error displaying basic pipeline info: {e}")
            print(f"❌ Error displaying basic pipeline info: {e}")
            print(f"Cache summary keys: {list(cache_summary.keys()) if cache_summary else 'None'}")
        
        # Show similarity analysis statistics
        try:
            if 'similarity_analysis' in cache_summary and cache_summary['similarity_analysis']:
                similarity_data = cache_summary['similarity_analysis']
                if 'overall_stats' in similarity_data:
                    similarity_stats = similarity_data['overall_stats']
                    print(f"\n📈 Similarity Analysis Results:")
                    print(f"  📊 Total adjacent pairs: {similarity_stats['total_adjacent_pairs']}")
                    print(f"  📊 Mean similarity: {similarity_stats['mean_similarity']:.3f}")
                    print(f"  📊 Median similarity: {similarity_stats['median_similarity']:.3f}")
                    print(f"  📊 90th percentile: {similarity_stats['percentiles']['90']:.3f}")
                    print(f"  📊 95th percentile: {similarity_stats['percentiles']['95']:.3f}")
                    print(f"  🎯 Threshold recommendations:")
                    print(f"     Conservative (25% merge): {similarity_stats['percentiles']['75']:.3f}")
                    print(f"     Moderate (50% merge): {similarity_stats['percentiles']['50']:.3f}")
                    print(f"     Aggressive (75% merge): {similarity_stats['percentiles']['25']:.3f}")
                else:
                    print(f"  ❌ Similarity analysis data format issue")
            else:
                print(f"  ❌ Similarity analysis data unavailable")
        except Exception as e:
            logger.warning(f"Could not load similarity analysis data: {e}")
            print(f"  ❌ Similarity analysis data unavailable")

        # Show merging statistics
        if 'merging_statistics' in cache_summary:
            merging_stats = cache_summary['merging_statistics']
            try:
                print(f"\n🔄 Semantic Merging Results:")
                print(f"  📊 Reduction: {merging_stats['total_input_text_units']} text units → {merging_stats['total_output_chunks']} chunks ({merging_stats['reduction_percentage']:.1f}% reduction)")
                print(f"  📏 Chunk sizes: {merging_stats['min_chunk_tokens']}-{merging_stats['max_chunk_tokens']} tokens (avg: {merging_stats['avg_chunk_tokens']:.1f})")
                print(f"  📝 Text units per chunk: {merging_stats['min_text_units_per_chunk']}-{merging_stats['max_text_units_per_chunk']} (avg: {merging_stats['avg_text_units_per_chunk']:.1f})")
                print(f"  ⚙️  Config: threshold={merging_stats['config_used']['similarity_threshold']}, max_distance={merging_stats['config_used']['max_merge_distance']}, max_size={merging_stats['config_used']['max_chunk_size']}")
                
                # Show detailed distribution statistics if available
                if 'chunk_size_distribution' in merging_stats and merging_stats['chunk_size_distribution']:
                    token_dist = merging_stats['chunk_size_distribution']
                    print(f"\n📏 Token Count Distribution:")
                    print(f"  📊 Quartiles: Q1={token_dist['tokens_quartiles']['q1']:.0f}, Median={token_dist['tokens_median']:.0f}, Q3={token_dist['tokens_quartiles']['q3']:.0f} (IQR={token_dist['tokens_quartiles']['iqr']:.0f})")
                    print(f"  📊 Percentiles: 10th={token_dist['tokens_percentiles']['10']:.0f}, 90th={token_dist['tokens_percentiles']['90']:.0f}, 95th={token_dist['tokens_percentiles']['95']:.0f}, 99th={token_dist['tokens_percentiles']['99']:.0f}")
                    print(f"  📊 Standard deviation: {token_dist['tokens_std']:.1f}")
                
                if 'text_unit_distribution' in merging_stats and merging_stats['text_unit_distribution']:
                    unit_dist = merging_stats['text_unit_distribution']
                    print(f"\n📝 Text Units per Chunk Distribution:")
                    print(f"  📊 Quartiles: Q1={unit_dist['text_units_quartiles']['q1']:.0f}, Median={unit_dist['text_units_median']:.0f}, Q3={unit_dist['text_units_quartiles']['q3']:.0f} (IQR={unit_dist['text_units_quartiles']['iqr']:.0f})")
                    print(f"  📊 Percentiles: 10th={unit_dist['text_units_percentiles']['10']:.0f}, 90th={unit_dist['text_units_percentiles']['90']:.0f}, 95th={unit_dist['text_units_percentiles']['95']:.0f}, 99th={unit_dist['text_units_percentiles']['99']:.0f}")
                    print(f"  📊 Standard deviation: {unit_dist['text_units_std']:.1f}")
                
                # Show merge stopping statistics if available
                if 'merge_stopping_percentages' in merging_stats:
                    stopping_percentages = merging_stats['merge_stopping_percentages']
                    print(f"\n📊 Why chunks stopped growing:")
                    print(f"  • Single text unit: {stopping_percentages['single_text_unit']:.1f}%")
                    print(f"  • Similarity threshold: {stopping_percentages['similarity_threshold']:.1f}%") 
                    print(f"  • Token limit: {stopping_percentages['token_limit']:.1f}%")
                    print(f"  • Distance limit: {stopping_percentages['distance_limit']:.1f}%")
                    print(f"  • End of text units: {stopping_percentages['end_of_text_units']:.1f}%")
            except Exception as e:
                logger.error(f"Error displaying merging statistics: {e}")
                print(f"  ❌ Error displaying merging statistics: {e}")
        
        print("="*60)
        
        # Show cache info
        try:
            cache_info = orchestrator.embedding_cache.get_cache_info()
            if cache_info:
                print(f"📊 Embedding cache: {cache_info.get('cached_sentences', 0)} sentences cached")
                if 'stats' in cache_info and cache_info['stats']:
                    hit_rate = cache_info['stats'].get('hit_rate', 0)
                    print(f"🎯 Cache hit rate: {hit_rate:.2%}")
        except Exception as e:
            logger.warning(f"Could not get cache info: {e}")
            print(f"📊 Embedding cache: info unavailable")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        logger.error(f"Main execution failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())