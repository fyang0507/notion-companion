"""
Configuration loader for evaluation system.

Loads TOML configuration files and validates structure and values.
Returns nested TOML structure directly - no flattening required.

Process: TOML → validate → return nested dict
"""

import tomllib
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


# Removed ChunkingConfig dataclass - working directly with dictionaries to avoid redundant conversions


class ConfigLoader:
    """Load and manage configuration files"""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            # Default to config directory relative to this file
            config_dir = Path(__file__).parent.parent / "config"
        
        self.config_dir = Path(config_dir)
        self._config_cache = {}
        
        logger.info(f"ConfigLoader initialized with config directory: {self.config_dir}")
    
    def load_chunking_config(self, config_file: str = "chunking_config.toml") -> Dict[str, Any]:
        """Load chunking configuration from TOML file"""
        config_path = self.config_dir / config_file
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        # Check cache first
        cache_key = str(config_path)
        if cache_key in self._config_cache:
            logger.debug(f"Using cached config for {config_file}")
            return self._config_cache[cache_key]
        
        logger.info(f"Loading chunking configuration from {config_path}")
        
        try:
            with open(config_path, 'rb') as f:
                config_data = tomllib.load(f)
            
            # Derive quotation_marks from quote_pairs for backward compatibility
            if 'chunking' in config_data and 'quote_pairs' in config_data['chunking']:
                quote_pairs = config_data['chunking']['quote_pairs']
                quotation_marks = list(set([char for pair in quote_pairs for char in pair]))
                config_data['chunking']['quotation_marks'] = quotation_marks
            
            # Validate configuration structure directly
            self.validate_config(config_data)
            
            # Cache the result
            self._config_cache[cache_key] = config_data
            
            logger.info("Chunking configuration loaded successfully")
            return config_data
            
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_path}: {str(e)}")
            raise
    
    def reload_config(self, config_file: str = "chunking_config.toml") -> Dict[str, Any]:
        """Force reload configuration from file (bypass cache)"""
        config_path = self.config_dir / config_file
        cache_key = str(config_path)
        
        # Clear cache entry
        if cache_key in self._config_cache:
            del self._config_cache[cache_key]
        
        return self.load_chunking_config(config_file)
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration structure and values (central validation method).
        
        Checks required sections exist, validates types, and ensures value ranges
        are acceptable. Raises ValueError with descriptive message on failure.
        """
        try:
            # Check required sections exist
            required_sections = ['chunking', 'semantic_merging', 'embeddings']
            for section in required_sections:
                if section not in config:
                    raise ValueError(f"Missing required configuration section: {section}")
                if not isinstance(config[section], dict):
                    raise ValueError(f"Configuration section '{section}' must be a dictionary")
            
            # Validate semantic_merging section
            semantic_merging = config['semantic_merging']
            similarity_threshold = semantic_merging.get('similarity_threshold')
            if similarity_threshold is None:
                raise ValueError("Missing required field: semantic_merging.similarity_threshold")
            if not isinstance(similarity_threshold, (int, float)):
                raise ValueError(f"similarity_threshold must be a number, got {type(similarity_threshold)}")
            if not 0.0 <= similarity_threshold <= 1.0:
                raise ValueError(f"Similarity threshold must be between 0.0 and 1.0, got {similarity_threshold}")
            
            max_merge_distance = semantic_merging.get('max_merge_distance')
            if max_merge_distance is None:
                raise ValueError("Missing required field: semantic_merging.max_merge_distance")
            if not isinstance(max_merge_distance, int) or max_merge_distance <= 0:
                raise ValueError(f"max_merge_distance must be a positive integer, got {max_merge_distance}")
            
            # Validate token limits in semantic_merging section
            if 'max_chunk_size' not in semantic_merging:
                raise ValueError("Missing required field: semantic_merging.max_chunk_size")
            
            max_chunk_size = semantic_merging['max_chunk_size']
            if not isinstance(max_chunk_size, int) or max_chunk_size <= 0:
                raise ValueError(f"semantic_merging.max_chunk_size must be a positive integer, got {max_chunk_size}")
            
            # Validate embeddings section
            embeddings = config['embeddings']
            
            # Required fields in embeddings section
            required_embedding_fields = ['model', 'batch_size']
            for field in required_embedding_fields:
                if field not in embeddings:
                    raise ValueError(f"Missing required field: embeddings.{field}")
            
            # Validate embeddings configuration values
            model = embeddings['model']
            if not isinstance(model, str) or not model.strip():
                raise ValueError(f"embeddings.model must be a non-empty string, got {model}")
            
            batch_size = embeddings['batch_size']
            if not isinstance(batch_size, int) or batch_size <= 0:
                raise ValueError(f"embeddings.batch_size must be a positive integer, got {batch_size}")
            
            logger.info("Configuration validation passed")
            return True
            
        except (ValueError, KeyError) as e:
            logger.error(f"Configuration validation failed: {str(e)}")
            raise 
