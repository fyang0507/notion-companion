"""
Strategy Registry for RAG Retrieval

This module provides a centralized registry for managing different retrieval strategies.
It allows for dynamic registration, retrieval, and listing of available strategies.
"""

from typing import Dict, List, Optional, Type
from .base_strategy import BaseRetrievalStrategy
import logging

logger = logging.getLogger(__name__)

class StrategyRegistry:
    """
    Registry for managing retrieval strategies.
    
    This class provides a centralized way to register, retrieve, and manage
    different retrieval strategies. It follows the registry pattern to allow
    for dynamic strategy selection at runtime.
    """
    
    _strategies: Dict[str, BaseRetrievalStrategy] = {}
    _strategy_classes: Dict[str, Type[BaseRetrievalStrategy]] = {}
    
    @classmethod
    def register(cls, name: str, strategy: BaseRetrievalStrategy):
        """
        Register a strategy instance.
        
        Args:
            name: Strategy name
            strategy: Strategy instance
        """
        cls._strategies[name] = strategy
        cls._strategy_classes[name] = type(strategy)
        logger.info(f"Registered strategy: {name}")
    
    @classmethod
    def register_class(cls, name: str, strategy_class: Type[BaseRetrievalStrategy]):
        """
        Register a strategy class (will be instantiated when needed).
        
        Args:
            name: Strategy name
            strategy_class: Strategy class
        """
        cls._strategy_classes[name] = strategy_class
        logger.info(f"Registered strategy class: {name}")
    
    @classmethod
    def get_strategy(cls, name: str) -> Optional[BaseRetrievalStrategy]:
        """
        Get a strategy instance by name.
        
        Args:
            name: Strategy name
            
        Returns:
            Strategy instance or None if not found
        """
        if name in cls._strategies:
            return cls._strategies[name]
        
        # If not instantiated but class is registered, instantiate it
        if name in cls._strategy_classes:
            strategy_class = cls._strategy_classes[name]
            try:
                strategy = strategy_class(name=name)
                cls._strategies[name] = strategy
                return strategy
            except Exception as e:
                logger.error(f"Failed to instantiate strategy {name}: {e}")
                return None
        
        return None
    
    @classmethod
    def list_strategies(cls) -> List[str]:
        """
        Get list of all registered strategy names.
        
        Returns:
            List of strategy names
        """
        all_names = set(cls._strategies.keys()) | set(cls._strategy_classes.keys())
        return sorted(list(all_names))
    
    @classmethod
    def get_strategy_info(cls, name: str) -> Optional[Dict[str, str]]:
        """
        Get information about a strategy.
        
        Args:
            name: Strategy name
            
        Returns:
            Dictionary with strategy information
        """
        strategy = cls.get_strategy(name)
        if strategy:
            return {
                'name': strategy.get_name(),
                'description': strategy.get_description(),
                'parameters': strategy.get_parameters()
            }
        return None
    
    @classmethod
    def unregister(cls, name: str):
        """
        Unregister a strategy.
        
        Args:
            name: Strategy name
        """
        if name in cls._strategies:
            del cls._strategies[name]
        if name in cls._strategy_classes:
            del cls._strategy_classes[name]
        logger.info(f"Unregistered strategy: {name}")
    
    @classmethod
    def clear_registry(cls):
        """Clear all registered strategies."""
        cls._strategies.clear()
        cls._strategy_classes.clear()
        logger.info("Cleared strategy registry")
    
    @classmethod
    def get_registry_status(cls) -> Dict[str, int]:
        """
        Get registry status.
        
        Returns:
            Dictionary with registry statistics
        """
        return {
            'total_strategies': len(cls.list_strategies()),
            'instantiated_strategies': len(cls._strategies),
            'registered_classes': len(cls._strategy_classes)
        } 