"""
Token counting utilities using tiktoken.

Provides centralized token counting functionality for consistent
token calculations across the application.
"""

import tiktoken
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Global tokenizer instance for efficiency
_tokenizer: Optional[tiktoken.Encoding] = None

def get_tokenizer() -> tiktoken.Encoding:
    """Get or create the tiktoken encoder instance."""
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = tiktoken.get_encoding("cl100k_base")
    return _tokenizer

def count_tokens(text: str) -> int:
    """
    Count tokens in text using tiktoken.
    
    Args:
        text: The text to count tokens for
        
    Returns:
        Number of tokens in the text
    """
    if not text:
        return 0
    
    try:
        tokenizer = get_tokenizer()
        return len(tokenizer.encode(text))
    except Exception as e:
        raise Exception(f"Error counting tokens: {e}")