"""
Enhanced newline-based text splitter for evaluation dataset preparation.

This splitter provides flexible newline-based chunking with support for:
- Line-by-line splitting (single newlines)
- Paragraph splitting (multiple consecutive newlines)
- Configurable behavior via chunking configuration

Provides a simpler alternative to the robust sentence splitter for cases where
atomic sentence splitting is too granular.
"""

import logging
import re
from typing import List, Dict

logger = logging.getLogger(__name__)


class NewlineSplitter:
    """Enhanced newline-based text splitter with paragraph support."""
    
    def __init__(self, config: Dict):
        """
        Initialize the newline splitter.
        
        Args:
            config: Configuration dictionary with optional newline splitting settings
        """
        self.config = config
        
        # Get newline splitting configuration from dedicated section
        newline_config = config.get('newline_splitter', {})
        
        # Default to paragraph mode (multiple newlines = paragraph breaks)
        self.split_mode = newline_config.get('split_mode', 'paragraph')
        
        # Minimum number of consecutive newlines to consider a paragraph break
        self.paragraph_break_threshold = newline_config.get('paragraph_break_threshold', 2)
        
        logger.info(f"NewlineSplitter initialized with mode: {self.split_mode}")
    
    def split(self, text: str) -> List[str]:
        """
        Split text into chunks using newlines as boundaries.
        
        Args:
            text: Input text to split
            
        Returns:
            List of text chunks split according to configured mode
        """
        if not text.strip():
            return []
        
        if self.split_mode == 'paragraph':
            return self._split_by_paragraphs(text)
        elif self.split_mode == 'line':
            return self._split_by_lines(text)
        else:
            raise ValueError(f"Unknown split_mode: {self.split_mode}. Must be 'paragraph' or 'line'")
    
    def _split_by_lines(self, text: str) -> List[str]:
        """Split text by individual lines (original behavior)."""
        lines = text.split('\n')
        chunks = []
        
        for line in lines:
            stripped_line = line.strip()
            if stripped_line:  # Only include non-empty lines
                chunks.append(stripped_line)
        
        logger.debug(f"Split text into {len(chunks)} chunks by lines")
        return chunks
    
    def _split_by_paragraphs(self, text: str) -> List[str]:
        """
        Split text by paragraphs (multiple consecutive newlines).
        
        This method treats multiple consecutive newlines as paragraph separators
        and groups lines within each paragraph together.
        """
        # Create regex pattern for paragraph breaks
        # \n{2,} matches 2 or more consecutive newlines
        paragraph_pattern = f'\\n{{{self.paragraph_break_threshold},}}'
        
        # Split on paragraph breaks
        paragraphs = re.split(paragraph_pattern, text)
        chunks = []
        
        for paragraph in paragraphs:
            # Clean up the paragraph
            cleaned_paragraph = paragraph.strip()
            if cleaned_paragraph:
                # For each paragraph, normalize internal newlines to spaces
                # This keeps related lines together as one chunk
                normalized_paragraph = re.sub(r'\n+', ' ', cleaned_paragraph)
                normalized_paragraph = re.sub(r'\s+', ' ', normalized_paragraph)  # Normalize whitespace
                chunks.append(normalized_paragraph)
        
        logger.debug(f"Split text into {len(chunks)} chunks by paragraphs")
        return chunks