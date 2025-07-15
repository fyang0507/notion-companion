"""
RAG Interface

Public interface for the RAG module.
This defines the contract for RAG operations and retrieval strategies.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class SearchResult:
    """Result from a search operation."""
    id: str
    title: str
    content: str
    score: float
    metadata: Dict[str, Any]
    chunk_id: Optional[str] = None

@dataclass
class ChatMessage:
    """Chat message data structure."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str

@dataclass
class ChatResponse:
    """Response from a chat operation."""
    message: str
    sources: List[SearchResult]
    session_id: str
    tokens_used: int

class RAGInterface(ABC):
    """
    Interface for RAG operations.
    
    This interface defines the contract for search and chat operations
    using different retrieval strategies.
    """
    
    @abstractmethod
    async def search(self, query: str, strategy: str = "contextual", **kwargs) -> List[SearchResult]:
        """
        Search for relevant documents using specified strategy.
        
        Args:
            query: Search query
            strategy: Retrieval strategy to use
            **kwargs: Additional search parameters
            
        Returns:
            List of search results
        """
        pass
    
    @abstractmethod
    async def chat(self, messages: List[ChatMessage], session_id: str, **kwargs) -> ChatResponse:
        """
        Generate a chat response using RAG.
        
        Args:
            messages: Chat conversation history
            session_id: Chat session ID
            **kwargs: Additional chat parameters
            
        Returns:
            Chat response with sources
        """
        pass
    
    @abstractmethod
    async def get_available_strategies(self) -> List[str]:
        """
        Get list of available retrieval strategies.
        
        Returns:
            List of strategy names
        """
        pass 