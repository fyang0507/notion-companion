"""
Chunking Strategy Factory

Config-driven factory for creating chunking strategies based on benchmark configuration.
Maps strategy names to their corresponding implementation classes.
"""

import logging
from typing import Dict, Any, Type
from .services.chunking_strategies import ChunkingStrategy
from .services.basic_paragraph_chunker import BasicParagraphChunker

logger = logging.getLogger(__name__)


class ChunkingStrategyRegistry:
    """Registry that maps strategy names to implementation classes."""
    
    def __init__(self):
        self._strategies: Dict[str, Type[ChunkingStrategy]] = {}
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """Register the built-in chunking strategies."""
        self._strategies["basic_paragraph"] = BasicParagraphChunker
        logger.info(f"Registered {len(self._strategies)} chunking strategies: {list(self._strategies.keys())}")
    
    def register(self, name: str, strategy_class: Type[ChunkingStrategy]):
        """Register a new chunking strategy."""
        self._strategies[name] = strategy_class
        logger.info(f"Registered chunking strategy: {name}")
    
    def get_strategy_class(self, name: str) -> Type[ChunkingStrategy]:
        """Get the strategy class for a given name."""
        if name not in self._strategies:
            available = list(self._strategies.keys())
            raise ValueError(f"Unknown chunking strategy: {name}. Available strategies: {available}")
        return self._strategies[name]
    
    def list_strategies(self) -> list[str]:
        """List all available strategy names."""
        return list(self._strategies.keys())


class ChunkingStrategyFactory:
    """Factory for creating chunking strategies based on configuration."""
    
    def __init__(self):
        self.registry = ChunkingStrategyRegistry()
    
    def create_strategy(self, strategy_config: Dict[str, Any], ingestion_config: Dict[str, Any]) -> ChunkingStrategy:
        """
        Create a chunking strategy based on configuration.
        
        Args:
            strategy_config: Strategy configuration from [strategies.chunking]
            ingestion_config: Ingestion configuration from [ingestion]
            
        Returns:
            Configured chunking strategy instance
        """
        strategy_name = strategy_config.get("strategy")
        if not strategy_name:
            raise ValueError("Strategy name is required in chunking configuration")
        
        strategy_class = self.registry.get_strategy_class(strategy_name)
        
        logger.info(f"Creating chunking strategy: {strategy_name}")
        
        # Pass full configuration to strategy class for self-validation
        # Each strategy class is responsible for extracting its required parameters
        full_config = {
            "strategy_config": strategy_config,
            "ingestion_config": ingestion_config
        }
        
        return strategy_class.from_config(full_config)


# Global factory instance
_chunking_factory = ChunkingStrategyFactory()


def get_chunking_factory() -> ChunkingStrategyFactory:
    """Get the global chunking strategy factory."""
    return _chunking_factory