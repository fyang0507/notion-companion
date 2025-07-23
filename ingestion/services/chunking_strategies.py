"""
Chunking Strategies

Abstract base classes for content-aware chunking strategies.
Concrete implementations should be added in experiments.
"""

import tiktoken
from typing import List, Dict, Any
from abc import ABC, abstractmethod
import logging

class ChunkingStrategy(ABC):
    """Base class for content-aware chunking strategies."""
    
    def __init__(self, max_tokens: int = 1000, overlap_tokens: int = 100):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self.logger = logging.getLogger(__name__)
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self.encoding.encode(text))
    
    @abstractmethod
    async def create_semantic_chunks(self, content: str, title: str) -> List[Dict[str, Any]]:
        """Create chunks respecting content-specific semantics."""
        pass
    
    def _create_chunk_with_metadata(self, content: str, index: int, section_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a chunk with standard metadata."""
        section_info = section_info or {}
        temp_id = f"temp_chunk_{index}"
        
        return {
            'temp_id': temp_id,
            'index': index,
            'content': content.strip(),
            'token_count': self.count_tokens(content),
            'section_title': section_info.get('title', ''),
            'section_level': section_info.get('level', 0),
            'hierarchy': section_info.get('hierarchy', []),
            'chunk_type': section_info.get('chunk_type', 'content')
        }