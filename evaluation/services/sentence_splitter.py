"""
Robust sentence splitter for multi-lingual text.

Handles:
- Robust sentence boundary detection
- Paired quotation marks (only closing quotes end sentences)  
- Abbreviation detection to avoid false splits
- Multi-language support (Chinese, English, French)
"""

import re
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class QuoteStateMachine:
    """Handle ambiguous ASCII quotes that use same character for open/close"""
    
    def __init__(self, quote_pairs_config: List[List[str]], sentence_punctuation: set):
        # Build quote pairs dictionary from configuration
        self.quote_pairs = {}
        for opening, closing in quote_pairs_config:
            self.quote_pairs[opening] = closing
        
        # Only closing quotes should end sentences
        self.closing_quotes = set(self.quote_pairs.values())
        self.ambiguous_quotes = {'"', "'"}
        
        # Store sentence punctuation for context detection
        self.sentence_punctuation = sentence_punctuation
    
    def is_closing_quote(self, quote_char: str, position: int, text: str) -> bool:
        """Determine if a quote character is a closing quote"""
        if quote_char not in self.ambiguous_quotes:
            # Unambiguous quotes (different open/close chars)
            return quote_char in self.closing_quotes
        
        # For ambiguous quotes, use context to determine
        return self._detect_closing_context(quote_char, position, text)
    
    def _detect_closing_context(self, quote_char: str, position: int, text: str) -> bool:
        """Use heuristics to detect if ASCII quote is closing"""
        # Heuristic 1: Preceded by sentence punctuation -> likely closing
        if position > 0 and text[position-1] in self.sentence_punctuation:
            return True
        
        # Heuristic 2: Followed by space + capital letter -> likely closing
        if (position + 1 < len(text) and 
            text[position + 1].isspace() and
            position + 2 < len(text) and
            (text[position + 2].isupper() or '\u4e00' <= text[position + 2] <= '\u9fff')):
            return True
            
        # Heuristic 3: At end of text -> likely closing
        if position >= len(text) - 1:
            return True
            
        # Heuristic 4: Check quote balance in surrounding context
        return self._check_quote_balance(quote_char, position, text)
    
    def _check_quote_balance(self, quote_char: str, position: int, text: str) -> bool:
        """Check if this quote balances an earlier opening quote"""
        # Look backward for unmatched opening quote
        quote_count = 0
        for i in range(position - 1, -1, -1):
            if text[i] == quote_char:
                quote_count += 1
            # Stop at sentence boundaries
            if text[i] in self.sentence_punctuation:
                break
        
        # Odd count suggests this is a closing quote
        return quote_count % 2 == 1


class RobustSentenceSplitter:
    """Robust sentence splitter handling multiple languages and edge cases"""
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Require chunking configuration - fail hard if missing
        if 'chunking' not in config:
            raise ValueError("Missing required 'chunking' configuration section")
        
        chunking_config = config['chunking']
        
        # Require sentence punctuation configuration first
        if 'chinese_punctuation' not in chunking_config:
            raise ValueError("Missing required 'chinese_punctuation' in chunking configuration")
        if 'western_punctuation' not in chunking_config:
            raise ValueError("Missing required 'western_punctuation' in chunking configuration")
            
        # Build combined sentence punctuation set from config
        self.sentence_punctuation = set(
            chunking_config['chinese_punctuation'] + 
            chunking_config['western_punctuation']
        )
        
        # Require quote_pairs configuration
        if 'quote_pairs' not in chunking_config:
            raise ValueError("Missing required 'quote_pairs' in chunking configuration")
        self.quote_machine = QuoteStateMachine(chunking_config['quote_pairs'], self.sentence_punctuation)
        
        # Build abbreviation pattern - these can be empty lists
        all_abbreviations = (
            chunking_config.get('english_abbreviations', []) + 
            chunking_config.get('french_abbreviations', [])
        )
        self.abbreviations_pattern = '|'.join(re.escape(abbr) for abbr in all_abbreviations)
        
        # Compile patterns for efficiency
        self._compile_patterns()
        
        logger.info("RobustSentenceSplitter initialized")
    
    def _compile_patterns(self):
        """Compile regex patterns for efficiency"""
        # Chinese punctuation (always sentence boundaries)
        chunking_config = self.config.get('chunking', {})
        chinese_punct = ''.join(re.escape(p) for p in chunking_config.get('chinese_punctuation', []))
        
        # Western punctuation with abbreviation protection
        western_punct = ''.join(re.escape(p) for p in chunking_config.get('western_punctuation', []))
        
        # All possible quotes
        all_quotes = ''.join(re.escape(q) for q in chunking_config.get('quotation_marks', []))
        
        # Simpler pattern without variable-width lookbehind
        # We'll handle abbreviation detection in the boundary detection logic
        self.boundary_pattern = re.compile(
            f'([{chinese_punct}])([{all_quotes}]*)|'  # Chinese punct + optional quotes
            f'([{western_punct}])'  # Western punctuation
            f'([{all_quotes}]*)'  # Optional quotes
            f'(?!\\d)'  # Not before digit (decimals)
            f'(?![a-z])'  # Not before lowercase (file extensions)
        )
        
        # Separate pattern for abbreviation detection
        self.abbreviation_pattern = re.compile(
            f'\\b({self.abbreviations_pattern})\\.$',
            re.IGNORECASE
        ) if self.abbreviations_pattern else None
    
    def split(self, text: str) -> List[str]:
        """Split text into sentences using robust boundary detection"""
        if not text.strip():
            return []
        
        sentences = []
        current_sentence = ""
        last_end = 0
        
        for match in self.boundary_pattern.finditer(text):
            # Add text up to this potential boundary
            current_sentence += text[last_end:match.start()]
            
            # Determine if this is a real sentence boundary
            if self._is_sentence_boundary(match, text):
                # Add the punctuation to current sentence
                current_sentence += match.group(0)
                
                # Save the sentence and start a new one
                if current_sentence.strip():
                    sentences.append(current_sentence.strip())
                current_sentence = ""
            else:
                # Not a boundary, continue building current sentence
                current_sentence += match.group(0)
            
            last_end = match.end()
        
        # Add any remaining text
        current_sentence += text[last_end:]
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        return sentences
    
    def _is_sentence_boundary(self, match, text: str) -> bool:
        """Determine if a punctuation match is a real sentence boundary"""
        chinese_punct = match.group(1)
        chinese_quotes = match.group(2) or ""
        western_punct = match.group(3)
        western_quotes = match.group(4) or ""
        
        # Chinese punctuation is always a boundary
        if chinese_punct:
            # Check if any following quotes are closing quotes
            if chinese_quotes:
                return self._has_closing_quote(chinese_quotes, match.start(2), text)
            return True
        
        # Western punctuation - check context
        if western_punct:
            # Check if this is part of an abbreviation
            if western_punct == '.' and self.abbreviation_pattern:
                # Look backwards to see if this period is part of an abbreviation
                start_pos = max(0, match.start() - 20)  # Look back 20 chars
                preceding_text = text[start_pos:match.end()]
                if self.abbreviation_pattern.search(preceding_text):
                    return False  # This is an abbreviation, not a sentence boundary
            
            # Must be followed by capital letter, Chinese character, or end of text
            next_pos = match.end()
            
            # Skip whitespace
            while next_pos < len(text) and text[next_pos].isspace():
                next_pos += 1
            
            if next_pos >= len(text):
                return True  # End of text
            
            next_char = text[next_pos]
            if (next_char.isupper() or 
                '\u4e00' <= next_char <= '\u9fff' or  # Chinese character
                '\u00C0' <= next_char <= '\u017F'):   # Accented letters (French)
                
                # Check quotes if present
                if western_quotes:
                    return self._has_closing_quote(western_quotes, match.start(4), text)
                return True
        
        return False
    
    def _has_closing_quote(self, quotes: str, start_pos: int, text: str) -> bool:
        """Check if quote sequence contains any closing quotes"""
        for i, quote_char in enumerate(quotes):
            if self.quote_machine.is_closing_quote(quote_char, start_pos + i, text):
                return True
        return False 