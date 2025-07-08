"""
Multi-lingual text chunker for Chinese, English, and French text.

Handles:
- Robust sentence boundary detection
- Paired quotation marks (only closing quotes end sentences)
- Abbreviation detection to avoid false splits
- Semantic similarity merging
- Token-based optimization
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ChunkResult:
    """Result of chunking operation"""
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
    """Merge semantically similar adjacent sentences into chunks"""
    
    def __init__(self, embedding_service, config: Dict):
        self.embedding_service = embedding_service
        
        # Require semantic_merging configuration - fail hard if missing
        if 'semantic_merging' not in config:
            raise ValueError("Missing required 'semantic_merging' configuration section")
        
        semantic_config = config['semantic_merging']
        
        # Require key semantic merging parameters
        if 'similarity_threshold' not in semantic_config:
            raise ValueError("Missing required 'similarity_threshold' in semantic_merging configuration")
        if 'max_merge_distance' not in semantic_config:
            raise ValueError("Missing required 'max_merge_distance' in semantic_merging configuration")
            
        self.similarity_threshold = semantic_config['similarity_threshold']
        self.max_merge_distance = semantic_config['max_merge_distance']
    
    async def merge_sentences(self, sentences: List[str]) -> List[ChunkResult]:
        """Merge semantically similar adjacent sentences"""
        if not sentences:
            return []
        
        if len(sentences) == 1:
            return [ChunkResult(
                content=sentences[0],
                start_sentence=0,
                end_sentence=0
            )]
        
        # Get embeddings for all sentences
        embeddings = await self.embedding_service.generate_embeddings(sentences)
        
        # Calculate similarity matrix
        similarity_matrix = self._calculate_similarity_matrix(embeddings)
        
        # Merge similar adjacent sentences
        chunks = self._merge_by_similarity(sentences, similarity_matrix)
        
        return chunks
    
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
        """Merge adjacent sentences based on similarity threshold"""
        chunks = []
        i = 0
        
        while i < len(sentences):
            chunk_sentences = [sentences[i]]
            start_idx = i
            j = i + 1
            
            # Look ahead for similar sentences to merge
            merge_count = 0
            while (j < len(sentences) and 
                   merge_count < self.max_merge_distance and
                   similarity_matrix[i][j] >= self.similarity_threshold):
                
                chunk_sentences.append(sentences[j])
                merge_count += 1
                j += 1
            
            # Create chunk result
            chunk = ChunkResult(
                content=' '.join(chunk_sentences),
                start_sentence=start_idx,
                end_sentence=j - 1,
                context_before=self._get_context_before(sentences, start_idx),
                context_after=self._get_context_after(sentences, j - 1)
            )
            
            chunks.append(chunk)
            i = j
        
        return chunks
    
    def _get_context_before(self, sentences: List[str], start_idx: int, context_size: int = 2) -> str:
        """Get context sentences before the chunk"""
        if start_idx == 0:
            return ""
        
        context_start = max(0, start_idx - context_size)
        context_sentences = sentences[context_start:start_idx]
        return ' '.join(context_sentences)
    
    def _get_context_after(self, sentences: List[str], end_idx: int, context_size: int = 2) -> str:
        """Get context sentences after the chunk"""
        if end_idx >= len(sentences) - 1:
            return ""
        
        context_end = min(len(sentences), end_idx + 1 + context_size)
        context_sentences = sentences[end_idx + 1:context_end]
        return ' '.join(context_sentences)


class TokenOptimizer:
    """Optimize chunk length based on token count"""
    
    def __init__(self, tokenizer, config: Dict):
        self.tokenizer = tokenizer
        
        # Require token_optimization configuration - fail hard if missing
        if 'token_optimization' not in config:
            raise ValueError("Missing required 'token_optimization' configuration section")
        
        token_config = config['token_optimization']
        
        # Require key token optimization parameters
        if 'target_chunk_size' not in token_config:
            raise ValueError("Missing required 'target_chunk_size' in token_optimization configuration")
        if 'max_chunk_size' not in token_config:
            raise ValueError("Missing required 'max_chunk_size' in token_optimization configuration")
        if 'overlap_tokens' not in token_config:
            raise ValueError("Missing required 'overlap_tokens' in token_optimization configuration")
            
        self.target_chunk_size = token_config['target_chunk_size']
        self.max_chunk_size = token_config['max_chunk_size']
        self.overlap_tokens = token_config['overlap_tokens']
        
        # Require chunking configuration for punctuation pattern
        if 'chunking' not in config:
            raise ValueError("Missing required 'chunking' configuration section")
        
        chunking_config = config['chunking']
        
        if 'chinese_punctuation' not in chunking_config:
            raise ValueError("Missing required 'chinese_punctuation' in chunking configuration")
        if 'western_punctuation' not in chunking_config:
            raise ValueError("Missing required 'western_punctuation' in chunking configuration")
        
        # Build sentence punctuation pattern from config
        all_punctuation = (
            chunking_config['chinese_punctuation'] + 
            chunking_config['western_punctuation']
        )
        # Escape special regex characters and join for pattern
        escaped_punct = [re.escape(p) for p in all_punctuation]
        self.sentence_punctuation_pattern = '[' + ''.join(escaped_punct) + ']+'
    
    def optimize_chunks(self, chunks: List[ChunkResult]) -> List[ChunkResult]:
        """Optimize chunk sizes based on token count"""
        optimized_chunks = []
        
        for chunk in chunks:
            token_count = len(self.tokenizer.encode(chunk.content))
            
            if token_count <= self.target_chunk_size:
                # Chunk is good size
                optimized_chunks.append(chunk)
            elif token_count <= self.max_chunk_size:
                # Chunk is acceptable but large
                optimized_chunks.append(chunk)
            else:
                # Chunk is too large, need to split
                split_chunks = self._split_large_chunk(chunk)
                optimized_chunks.extend(split_chunks)
        
        # Add overlap between chunks
        return self._add_chunk_overlap(optimized_chunks)
    
    def _split_large_chunk(self, chunk: ChunkResult) -> List[ChunkResult]:
        """Split a chunk that's too large"""
        # Simple sentence-based splitting for now
        sentences = re.split(self.sentence_punctuation_pattern, chunk.content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        sub_chunks = []
        current_content = ""
        current_sentences = []
        
        for sentence in sentences:
            test_content = current_content + (" " if current_content else "") + sentence
            token_count = len(self.tokenizer.encode(test_content))
            
            if token_count <= self.target_chunk_size:
                current_content = test_content
                current_sentences.append(sentence)
            else:
                # Save current chunk and start new one
                if current_content:
                    sub_chunks.append(ChunkResult(
                        content=current_content,
                        start_sentence=chunk.start_sentence,
                        end_sentence=chunk.end_sentence
                    ))
                
                current_content = sentence
                current_sentences = [sentence]
        
        # Add final chunk
        if current_content:
            sub_chunks.append(ChunkResult(
                content=current_content,
                start_sentence=chunk.start_sentence,
                end_sentence=chunk.end_sentence
            ))
        
        return sub_chunks
    
    def _add_chunk_overlap(self, chunks: List[ChunkResult]) -> List[ChunkResult]:
        """Add overlap between adjacent chunks"""
        if len(chunks) <= 1:
            return chunks
        
        # For now, implement basic overlap by extending chunk boundaries
        # In a full implementation, this would extract overlapping sentences
        return chunks


class MultiLingualChunker:
    """Main multi-lingual chunker service"""
    
    def __init__(self, embedding_service, tokenizer, config: Dict):
        self.embedding_service = embedding_service
        self.tokenizer = tokenizer
        self.config = config
        
        self.sentence_splitter = RobustSentenceSplitter(config)
        self.semantic_merger = SemanticMerger(embedding_service, config)
        self.token_optimizer = TokenOptimizer(tokenizer, config)
        
        logger.info("MultiLingualChunker initialized")
    
    async def chunk_text(self, text: str, document_id: str = None) -> List[ChunkResult]:
        """Main chunking method for multi-lingual text"""
        if not text.strip():
            return []
        
        try:
            # Step 1: Split into sentences with robust boundary detection
            logger.debug(f"Splitting text into sentences (length: {len(text)})")
            sentences = self.sentence_splitter.split(text)
            logger.debug(f"Found {len(sentences)} sentences")
            
            # Step 2: Semantic similarity merging
            logger.debug("Performing semantic similarity merging")
            chunks = await self.semantic_merger.merge_sentences(sentences)
            logger.debug(f"Created {len(chunks)} semantic chunks")
            
            # Step 3: Token-based optimization
            logger.debug("Optimizing chunk token lengths")
            final_chunks = self.token_optimizer.optimize_chunks(chunks)
            logger.debug(f"Final chunk count: {len(final_chunks)}")
            
            # Add metadata
            for i, chunk in enumerate(final_chunks):
                chunk.embedding = await self._get_chunk_embedding(chunk.content)
            
            return final_chunks
            
        except Exception as e:
            logger.error(f"Error chunking text: {str(e)}")
            raise
    
    async def _get_chunk_embedding(self, content: str) -> List[float]:
        """Get embedding for chunk content"""
        try:
            embeddings = await self.embedding_service.generate_embeddings([content])
            return embeddings[0] if embeddings else []
        except Exception as e:
            logger.warning(f"Failed to generate embedding for chunk: {str(e)}")
            return [] 