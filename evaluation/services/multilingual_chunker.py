"""
Multi-lingual text chunker for Chinese, English, and French text.

Enhanced version with sentence-level embedding caching for fast parameter tuning.

Handles:
- Robust sentence boundary detection
- Paired quotation marks (only closing quotes end sentences)
- Abbreviation detection to avoid false splits
- Token-aware semantic similarity merging
- Sentence-level embedding caching for fast parameter experimentation
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
import numpy as np
from dataclasses import dataclass

# Import caching functionality  
from .sentence_embedding_cache import SentenceEmbeddingCache

logger = logging.getLogger(__name__)


@dataclass
class ChunkResult:
    """Result of chunking operation for evaluation dataset preparation"""
    content: str
    start_sentence: int
    end_sentence: int
    embedding: Optional[List[float]] = None
    context_before: str = ""
    context_after: str = ""


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


class SemanticMerger:
    """Merge semantically similar adjacent sentences into chunks with token-aware limits and caching"""
    
    def __init__(self, embedding_service, tokenizer, config: Dict, cache_dir: str = "data/cache"):
        self.embedding_service = embedding_service
        self.tokenizer = tokenizer
        
        # Initialize embedding cache
        self.embedding_cache = SentenceEmbeddingCache(cache_dir)
        
        # Require semantic_merging configuration - fail hard if missing
        if 'semantic_merging' not in config:
            raise ValueError("Missing required 'semantic_merging' configuration section")
        
        semantic_config = config['semantic_merging']
        
        # Require key semantic merging parameters
        if 'similarity_threshold' not in semantic_config:
            raise ValueError("Missing required 'similarity_threshold' in semantic_merging configuration")
        if 'max_merge_distance' not in semantic_config:
            raise ValueError("Missing required 'max_merge_distance' in semantic_merging configuration")
        if 'max_chunk_size' not in semantic_config:
            raise ValueError("Missing required 'max_chunk_size' in semantic_merging configuration")
            
        self.similarity_threshold = semantic_config['similarity_threshold']
        self.max_merge_distance = semantic_config['max_merge_distance']
        self.max_chunk_size = semantic_config['max_chunk_size']
    
    async def merge_sentences(self, sentences: List[str]) -> List[ChunkResult]:
        """Merge semantically similar adjacent sentences using cached embeddings"""
        if not sentences:
            return []
        
        if len(sentences) == 1:
            return [ChunkResult(
                content=sentences[0],
                start_sentence=0,
                end_sentence=0
            )]
        
        # Get embeddings with caching
        logger.debug(f"Getting embeddings for {len(sentences)} sentences")
        embeddings, cache_hits, cache_misses = await self.embedding_cache.get_embeddings(
            sentences, self.embedding_service
        )
        
        logger.info(f"Sentence embedding cache performance: {cache_hits} hits, {cache_misses} misses")
        
        # Calculate similarity matrix
        similarity_matrix = self._calculate_similarity_matrix(embeddings)
        
        # Merge similar adjacent sentences
        chunks = self._merge_by_similarity(sentences, similarity_matrix)
        
        return chunks
    
    def get_cache_info(self) -> Dict:
        """Get cache information and statistics"""
        return self.embedding_cache.get_cache_info()
    
    def clear_cache(self):
        """Clear embedding cache"""
        self.embedding_cache.clear_cache()
    
    def _calculate_similarity_matrix(self, embeddings: List[List[float]]) -> np.ndarray:
        """Calculate cosine similarity matrix between all sentence embeddings"""
        embeddings_array = np.array(embeddings)
        
        # Normalize embeddings
        norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
        normalized_embeddings = embeddings_array / (norms + 1e-8)
        
        # Calculate cosine similarity
        similarity_matrix = np.dot(normalized_embeddings, normalized_embeddings.T)
        
        return similarity_matrix
    
    def _merge_by_similarity(self, sentences: List[str], similarity_matrix: np.ndarray) -> List[ChunkResult]:
        """Merge adjacent sentences based on similarity threshold with token-aware limits"""
        chunks = []
        i = 0
        
        while i < len(sentences):
            chunk_sentences = [sentences[i]]
            start_idx = i
            j = i + 1
            
            # Look ahead for similar sentences to merge
            merge_count = 0
            while j < len(sentences) and merge_count < self.max_merge_distance:
                # Check semantic similarity
                if similarity_matrix[i][j] < self.similarity_threshold:
                    break
                
                # Check token count before adding sentence
                test_content = ' '.join(chunk_sentences + [sentences[j]])
                token_count = len(self.tokenizer.encode(test_content))
                
                if token_count > self.max_chunk_size:
                    # Would exceed token limit, stop merging
                    break
                
                # Safe to add this sentence
                chunk_sentences.append(sentences[j])
                merge_count += 1
                j += 1
            
            # Create chunk result
            chunk = ChunkResult(
                content=' '.join(chunk_sentences),
                start_sentence=start_idx,
                end_sentence=j - 1
            )
            
            chunks.append(chunk)
            i = j
        
        return chunks


class MultiLingualChunker:
    """Main multi-lingual chunker service with integrated token-aware semantic merging and caching"""
    
    def __init__(self, embedding_service, tokenizer, config: Dict, cache_dir: str = "data/cache"):
        self.embedding_service = embedding_service
        self.tokenizer = tokenizer
        self.config = config
        self.cache_dir = cache_dir
        
        self.sentence_splitter = RobustSentenceSplitter(config)
        self.semantic_merger = SemanticMerger(embedding_service, tokenizer, config, cache_dir)
        
        logger.info("MultiLingualChunker initialized with caching")
    
    async def chunk_text(self, text: str, document_id: str = None) -> List[ChunkResult]:
        """Main chunking method for multi-lingual text with integrated token-aware semantic merging and caching"""
        if not text.strip():
            return []
        
        try:
            # Step 1: Split into sentences with robust boundary detection
            logger.debug(f"Splitting text into sentences (length: {len(text)})")
            sentences = self.sentence_splitter.split(text)
            logger.debug(f"Found {len(sentences)} sentences")
            
            # Step 2: Token-aware semantic similarity merging with caching
            logger.debug("Performing cached token-aware semantic similarity merging")
            chunks = await self.semantic_merger.merge_sentences(sentences)
            logger.debug(f"Created {len(chunks)} semantic chunks")
            
            # Step 3: Add embeddings
            for i, chunk in enumerate(chunks):
                chunk.embedding = await self._get_chunk_embedding(chunk.content)
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking text: {str(e)}")
            raise
    
    def get_cache_info(self) -> Dict:
        """Get comprehensive cache information"""
        return self.semantic_merger.get_cache_info()
    
    def clear_cache(self):
        """Clear all caching"""
        self.semantic_merger.clear_cache()
    
    async def precompute_sentence_embeddings(self, documents: List[Dict]) -> Dict:
        """
        Precompute and cache sentence embeddings for all documents.
        
        This is useful for Step 2 preparation - cache all sentence embeddings
        before experimenting with different chunk merging parameters.
        
        Args:
            documents: List of document dictionaries with 'content' field
            
        Returns:
            Statistics about the precomputation process
        """
        logger.info("Starting sentence embedding precomputation")
        
        total_sentences = 0
        total_documents = len(documents)
        cache_hits = 0
        cache_misses = 0
        
        for i, doc in enumerate(documents):
            content = doc.get('content', '')
            if not content.strip():
                continue
            
            logger.info(f"Precomputing embeddings for document {i+1}/{total_documents}")
            
            # Split into sentences
            sentences = self.sentence_splitter.split(content)
            total_sentences += len(sentences)
            
            # Get/cache embeddings
            _, hits, misses = await self.semantic_merger.embedding_cache.get_embeddings(
                sentences, self.embedding_service
            )
            
            cache_hits += hits
            cache_misses += misses
        
        stats = {
            'total_documents': total_documents,
            'total_sentences': total_sentences,
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'hit_rate': cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0,
            'cache_info': self.get_cache_info()
        }
        
        logger.info(f"Sentence embedding precomputation complete: {stats}")
        return stats
    
    async def _get_chunk_embedding(self, content: str) -> List[float]:
        """Get embedding for chunk content"""
        try:
            embeddings = await self.embedding_service.generate_embeddings([content])
            return embeddings[0] if embeddings else []
        except Exception as e:
            logger.warning(f"Failed to generate embedding for chunk: {str(e)}")
            return [] 