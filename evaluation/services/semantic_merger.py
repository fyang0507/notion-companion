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
        
        logger.info("SemanticMerger initialized")
    
    def merge_sentences(self, sentences: List[str], embeddings: List[List[float]]) -> List[ChunkResult]:
        """
        Merge semantically similar adjacent sentences based on provided embeddings.
        
        Args:
            sentences: List of sentence strings
            embeddings: Corresponding embeddings for each sentence
            
        Returns:
            List of ChunkResult objects
        """
        if not sentences:
            return []
        
        if len(sentences) != len(embeddings):
            raise ValueError(f"Mismatch between sentences ({len(sentences)}) and embeddings ({len(embeddings)})")
        
        if len(sentences) == 1:
            return [ChunkResult(
                content=sentences[0],
                start_sentence=0,
                end_sentence=0
            )]
        
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