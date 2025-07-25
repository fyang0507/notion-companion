"""
Chunking Strategies

Abstract base classes for content-aware chunking strategies.
Concrete implementations should be added in experiments.
"""

from typing import List, Dict, Any
from abc import ABC, abstractmethod
import logging


class ChunkingStrategy(ABC):
    """Base class for content-aware chunking strategies."""
    
    def __init__(self, max_tokens: int, overlap_tokens: int):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.logger = logging.getLogger(__name__)
    
    @abstractmethod
    async def chunk(self, content: str, title: str) -> List[Dict[str, Any]]:
        """Create chunks respecting content-specific semantics."""
        pass
