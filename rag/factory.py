"""
Retrieval Strategy Factory

Config-driven factory for creating retrieval strategies based on benchmark configuration.
Maps strategy names to their corresponding implementation classes.
"""

import logging
from typing import Dict, Any, Type
from .strategies.base_strategy import BaseRetrievalStrategy
from .strategies.basic_similarity_strategy import BasicSimilarityStrategy

logger = logging.getLogger(__name__)


class RetrievalStrategyRegistry:
    """Registry that maps strategy names to implementation classes."""
    
    def __init__(self):
        self._strategies: Dict[str, Type[BaseRetrievalStrategy]] = {}
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """Register the built-in retrieval strategies."""
        self._strategies["basic_similarity"] = BasicSimilarityStrategy
        logger.info(f"Registered {len(self._strategies)} retrieval strategies: {list(self._strategies.keys())}")
    
    def register(self, name: str, strategy_class: Type[BaseRetrievalStrategy]):
        """Register a new retrieval strategy."""
        self._strategies[name] = strategy_class
        logger.info(f"Registered retrieval strategy: {name}")
    
    def get_strategy_class(self, name: str) -> Type[BaseRetrievalStrategy]:
        """Get the strategy class for a given name."""
        if name not in self._strategies:
            available = list(self._strategies.keys())
            raise ValueError(f"Unknown retrieval strategy: {name}. Available strategies: {available}")
        return self._strategies[name]
    
    def list_strategies(self) -> list[str]:
        """List all available strategy names."""
        return list(self._strategies.keys())


class RetrievalStrategyFactory:
    """Factory for creating retrieval strategies based on configuration."""
    
    def __init__(self):
        self.registry = RetrievalStrategyRegistry()
    
    def create_strategy(self, strategy_config: Dict[str, Any], database, openai_service, 
                      embeddings_config: Dict[str, Any]) -> BaseRetrievalStrategy:
        """
        Create a retrieval strategy based on configuration.
        
        Args:
            strategy_config: Strategy configuration from [strategies.retrieval]
            database: Database instance for data access
            openai_service: OpenAI service instance for embeddings
            embeddings_config: Embeddings configuration from [embeddings]
            
        Returns:
            Configured retrieval strategy instance
        """
        strategy_name = strategy_config.get("strategy")
        if not strategy_name:
            raise ValueError("Strategy name is required in retrieval configuration")
        
        strategy_class = self.registry.get_strategy_class(strategy_name)
        
        logger.info(f"Creating retrieval strategy: {strategy_name}")
        
        # Pass full configuration and dependencies to strategy class for self-validation
        # Each strategy class is responsible for handling its own initialization
        full_config = {
            "strategy_config": strategy_config,
            "embeddings_config": embeddings_config,
            "database": database,
            "openai_service": openai_service
        }
        
        return strategy_class.from_config(full_config)


# Global factory instance
_retrieval_factory = RetrievalStrategyFactory()


def get_retrieval_factory() -> RetrievalStrategyFactory:
    """Get the global retrieval strategy factory."""
    return _retrieval_factory