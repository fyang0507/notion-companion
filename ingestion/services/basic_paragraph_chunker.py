"""
Basic Paragraph Chunker

Simple paragraph-based chunking strategy using \n\n splitting for benchmark experiments.
This is the most basic chunking approach without any sophisticated semantic analysis.
"""

import logging
from typing import List, Dict, Any
from .chunking_strategies import ChunkingStrategy
from shared.utils import count_tokens

logger = logging.getLogger(__name__)


class BasicParagraphChunker(ChunkingStrategy):
    """
    Simple paragraph-based chunker using \\n\\n splitting.
    
    This chunker:
    1. Splits content by double newlines (paragraphs)
    2. Respects max token limits
    3. Creates simple chunks with basic positional metadata
    4. Used for benchmark/baseline experiments
    """
    
    def __init__(self, max_tokens: int, overlap_tokens: int):
        super().__init__(max_tokens, overlap_tokens)
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'BasicParagraphChunker':
        """
        Create BasicParagraphChunker from configuration dictionary.
        
        Args:
            config: Configuration containing strategy_config and ingestion_config
            
        Returns:
            Configured BasicParagraphChunker instance
        """
        ingestion_config = config.get("ingestion_config", {})
        
        # Extract required parameters with defaults
        max_tokens = ingestion_config["max_tokens"]
        overlap_tokens = ingestion_config["overlap_tokens"]
        
        logger.info(f"Creating BasicParagraphChunker with max_tokens={max_tokens}, overlap_tokens={overlap_tokens}")
        
        return cls(max_tokens=max_tokens, overlap_tokens=overlap_tokens)
    
    async def chunk(self, content: str, title: str) -> List[Dict[str, Any]]:
        """
        Create chunks by splitting on paragraphs to match evaluation dataset.
        
        This implementation matches the evaluation system's paragraph splitting approach
        which uses multiple consecutive newlines (\\n\\n+) as paragraph separators.
        
        Args:
            content: The text content to chunk
            title: The document title (for context, not used in basic chunking)
            
        Returns:
            List of chunk dictionaries with basic metadata
        """
        if not content.strip():
            logger.debug("Empty content provided, returning no chunks")
            return []
        
        # Split by paragraphs using double newlines (matches evaluation config)
        # This matches the evaluation dataset's paragraph-based approach
        import re
        paragraphs = re.split(r'\n{2,}', content)
        chunks = []
        chunk_index = 0
        
        logger.debug(f"Processing {len(paragraphs)} paragraphs for document: {title[:50]}...")
        
        for paragraph in paragraphs:
            # Clean up the paragraph
            cleaned_paragraph = paragraph.strip()
            if not cleaned_paragraph:  # Skip empty paragraphs
                continue
            
            # Create chunk for each paragraph
            chunk_data = self._create_chunk_data(cleaned_paragraph, chunk_index)
            chunks.append(chunk_data)
            chunk_index += 1
        
        logger.info(f"Created {len(chunks)} chunks for document: {title[:50]}...")
        return chunks
    
    def _create_chunk_data(self, content: str, chunk_index: int) -> Dict[str, Any]:
        """Create chunk data dictionary with basic metadata."""
        token_count = count_tokens(content)
        
        return {
            'content': content,
            'chunk_index': chunk_index,
            'token_count': token_count,
            'chunking_strategy': 'basic_paragraph',
            # Positional linking fields (will be set during insertion)
            'prev_chunk_id': None,
            'next_chunk_id': None,
            # Metadata for the chunk
            'chunk_metadata': {},
        }
