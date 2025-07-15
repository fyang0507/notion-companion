"""
Base Strategy Interface for RAG Retrieval

This module defines the base interface that all retrieval strategies must implement.
It provides a common contract for different retrieval approaches.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class RetrievalResult:
    """Result from a retrieval operation."""
    id: str
    title: str
    content: str
    score: float
    metadata: Dict[str, Any]
    chunk_id: Optional[str] = None
    document_id: Optional[str] = None
    similarity: Optional[float] = None
    
    def __post_init__(self):
        # Ensure similarity is set for backward compatibility
        if self.similarity is None:
            self.similarity = self.score

class BaseRetrievalStrategy(ABC):
    """
    Base class for all retrieval strategies.
    
    This abstract base class defines the interface that all retrieval strategies
    must implement. It provides a common contract for different approaches to
    retrieving relevant documents and chunks.
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
    
    @abstractmethod
    async def retrieve(
        self, 
        query: str, 
        filters: Dict[str, Any], 
        limit: int = 10,
        **kwargs
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant documents/chunks for a query.
        
        Args:
            query: Search query string
            filters: Dictionary of filters to apply
            limit: Maximum number of results to return
            **kwargs: Additional strategy-specific parameters
            
        Returns:
            List of RetrievalResult objects
        """
        pass
    
    @abstractmethod
    async def retrieve_with_embedding(
        self, 
        query_embedding: List[float], 
        filters: Dict[str, Any], 
        limit: int = 10,
        **kwargs
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant documents/chunks using a pre-computed embedding.
        
        Args:
            query_embedding: Pre-computed query embedding vector
            filters: Dictionary of filters to apply
            limit: Maximum number of results to return
            **kwargs: Additional strategy-specific parameters
            
        Returns:
            List of RetrievalResult objects
        """
        pass
    
    def get_name(self) -> str:
        """Get the strategy name."""
        return self.name
    
    def get_description(self) -> str:
        """Get the strategy description."""
        return self.description
    
    def get_parameters(self) -> Dict[str, Any]:
        """
        Get strategy-specific parameters.
        
        Returns:
            Dictionary of parameters and their current values
        """
        return {}
    
    def set_parameters(self, params: Dict[str, Any]):
        """
        Set strategy-specific parameters.
        
        Args:
            params: Dictionary of parameters to set
        """
        pass 