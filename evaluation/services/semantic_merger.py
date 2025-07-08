"""
Semantic similarity-based sentence merger for text chunking.

Handles:
- Token-aware semantic similarity merging
- Cosine similarity calculation between sentence embeddings  
- Configurable similarity thresholds and merge limits
- Adjacent sentence grouping with token size constraints
"""

import logging
from typing import List, Dict, Optional
import numpy as np
from dataclasses import dataclass

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


@dataclass
class MergingStatistics:
    """Statistics about why chunk creation stopped for analysis"""
    total_chunks: int = 0
    single_sentence_chunks: int = 0  # Chunks that never attempted to merge
    stopped_by_similarity: int = 0
    stopped_by_token_limit: int = 0
    stopped_by_distance_limit: int = 0
    stopped_by_end_of_sentences: int = 0
    
    def get_percentages(self) -> Dict[str, float]:
        """Get percentages of each stopping reason"""
        if self.total_chunks == 0:
            return {
                'single_sentence': 0.0,
                'similarity_threshold': 0.0,
                'token_limit': 0.0,
                'distance_limit': 0.0,
                'end_of_sentences': 0.0
            }
        
        return {
            'single_sentence': (self.single_sentence_chunks / self.total_chunks) * 100,
            'similarity_threshold': (self.stopped_by_similarity / self.total_chunks) * 100,
            'token_limit': (self.stopped_by_token_limit / self.total_chunks) * 100,
            'distance_limit': (self.stopped_by_distance_limit / self.total_chunks) * 100,
            'end_of_sentences': (self.stopped_by_end_of_sentences / self.total_chunks) * 100
        }


class SemanticMerger:
    """Merge semantically similar adjacent sentences based on embeddings with token-aware limits"""
    
    def __init__(self, tokenizer, config: Dict):
        self.tokenizer = tokenizer
        
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
        
        # Initialize global statistics tracking
        self.global_stats = MergingStatistics()
        
        logger.info("SemanticMerger initialized")
    
    def merge_sentences(self, sentences: List[str], embeddings: List[List[float]]) -> tuple[List[ChunkResult], MergingStatistics]:
        """
        Merge semantically similar adjacent sentences based on provided embeddings.
        
        Args:
            sentences: List of sentence strings
            embeddings: Corresponding embeddings for each sentence
            
        Returns:
            Tuple of (List of ChunkResult objects, MergingStatistics)
        """
        stats = MergingStatistics()
        
        if not sentences:
            return [], stats
        
        if len(sentences) != len(embeddings):
            raise ValueError(f"Mismatch between sentences ({len(sentences)}) and embeddings ({len(embeddings)})")
        
        if len(sentences) == 1:
            return [ChunkResult(
                content=sentences[0],
                start_sentence=0,
                end_sentence=0
            )], stats
        
        # Calculate similarity matrix
        similarity_matrix = self._calculate_similarity_matrix(embeddings)
        
        # Merge similar adjacent sentences with statistics tracking
        chunks = self._merge_by_similarity(sentences, similarity_matrix, stats)
        
        # Update global statistics
        self.global_stats.total_chunks += stats.total_chunks
        self.global_stats.single_sentence_chunks += stats.single_sentence_chunks
        self.global_stats.stopped_by_similarity += stats.stopped_by_similarity
        self.global_stats.stopped_by_token_limit += stats.stopped_by_token_limit
        self.global_stats.stopped_by_distance_limit += stats.stopped_by_distance_limit
        self.global_stats.stopped_by_end_of_sentences += stats.stopped_by_end_of_sentences
        
        return chunks, stats
    
    def _calculate_similarity_matrix(self, embeddings: List[List[float]]) -> np.ndarray:
        """Calculate cosine similarity matrix between all sentence embeddings"""
        embeddings_array = np.array(embeddings)
        
        # Normalize embeddings
        norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
        normalized_embeddings = embeddings_array / (norms + 1e-8)
        
        # Calculate cosine similarity
        similarity_matrix = np.dot(normalized_embeddings, normalized_embeddings.T)
        
        return similarity_matrix
    
    def _merge_by_similarity(self, sentences: List[str], similarity_matrix: np.ndarray, stats: MergingStatistics) -> List[ChunkResult]:
        """Merge adjacent sentences based on similarity threshold with token-aware limits"""
        chunks = []
        i = 0
        
        while i < len(sentences):
            chunk_sentences = [sentences[i]]
            start_idx = i
            j = i + 1
            merge_count = 0
            stop_reason = None
            
            # Look ahead for similar sentences to merge
            while j < len(sentences) and merge_count < self.max_merge_distance:
                # Check semantic similarity
                if similarity_matrix[i][j] < self.similarity_threshold:
                    stop_reason = 'similarity'
                    break
                
                # Check token count before adding sentence
                test_content = ' '.join(chunk_sentences + [sentences[j]])
                token_count = len(self.tokenizer.encode(test_content))
                
                if token_count > self.max_chunk_size:
                    # Would exceed token limit, stop merging
                    stop_reason = 'token_limit'
                    break
                
                # Safe to add this sentence
                chunk_sentences.append(sentences[j])
                merge_count += 1
                j += 1
            
            # Record why this chunk stopped growing
            stats.total_chunks += 1
            
            if len(chunk_sentences) == 1:
                # Single sentence chunk - check if it could attempt to merge
                if j >= len(sentences):
                    # Last sentence in document - no next sentence to merge with
                    stats.single_sentence_chunks += 1
                elif stop_reason == 'similarity':
                    # First merge attempt failed due to similarity
                    stats.stopped_by_similarity += 1
                elif stop_reason == 'token_limit':
                    # First merge attempt failed due to token limit
                    stats.stopped_by_token_limit += 1
                else:
                    # Other reasons (shouldn't happen for single sentences)
                    stats.single_sentence_chunks += 1
            else:
                # Multi-sentence chunk - record why it stopped
                if stop_reason == 'similarity':
                    stats.stopped_by_similarity += 1
                elif stop_reason == 'token_limit':
                    stats.stopped_by_token_limit += 1
                elif merge_count >= self.max_merge_distance and j < len(sentences):
                    stats.stopped_by_distance_limit += 1
                elif j >= len(sentences):
                    stats.stopped_by_end_of_sentences += 1
            
            # Create chunk result
            chunk = ChunkResult(
                content=' '.join(chunk_sentences),
                start_sentence=start_idx,
                end_sentence=j - 1
            )
            
            chunks.append(chunk)
            i = j
        
        return chunks 