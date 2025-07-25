"""
Retrieval Metrics Evaluator

Evaluates RAG retrieval performance using Rouge-L scoring and various IR metrics.
Supports precision@k, recall@k, MRR with proper multi-chunk handling.
"""

import logging
import math
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from rouge_score import rouge_scorer

# Import multilingual tokenizer from qa_self_verifier
from .qa_self_verifier import MultilingualTokenizer

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResults:
    """Container for retrieval results from a single query."""
    query_id: int
    query: str
    expected_chunk: str
    expected_metadata: Dict[str, Any]
    retrieved_chunks: List[Dict[str, Any]]


@dataclass
class MetricResult:
    """Results from a single metric evaluation."""
    metric_name: str
    k_value: Optional[int]
    score: float
    correct_retrievals: int
    total_questions: int
    detailed_results: List[Dict[str, Any]]
    evaluation_timestamp: str
    rouge_threshold: float
    metadata: Dict[str, Any]


class RetrievalMetricsEvaluator:
    """
    Evaluates retrieval performance using Rouge-L scoring and various IR metrics.
    
    This evaluator:
    1. Receives pre-retrieved results from the orchestrator
    2. Uses Rouge-L scoring to measure semantic similarity
    3. Handles multi-chunk expected results properly
    4. Calculates precision@k, recall@k, MRR with correct multi-chunk logic
    """
    
    def __init__(self, rouge_threshold: float):
        """
        Initialize the retrieval metrics evaluator.
        
        Args:
            rouge_threshold: Minimum Rouge-L score to consider a match
        """
        self.retrieval_results = []
        self.rouge_threshold = rouge_threshold
        # Initialize Rouge-L scorer with multilingual tokenizer for Chinese + English content
        multilingual_tokenizer = MultilingualTokenizer()
        self.rouge_scorer = rouge_scorer.RougeScorer(
            ['rougeL'], 
            use_stemmer=False,  # Disable stemming for multilingual text
            tokenizer=multilingual_tokenizer
        )
        # Cache for Rouge-L scores to avoid recomputation
        self.rouge_scores_cache = []
        logger.info(f"RetrievalMetricsEvaluator initialized with Rouge-L threshold: {rouge_threshold}")
        logger.info("Using multilingual tokenizer for Chinese + English content")
    
    def set_retrieval_results(self, retrieval_results: List[RetrievalResults]):
        """
        Set the retrieval results for evaluation and precompute all Rouge-L scores.
        
        Args:
            retrieval_results: List of RetrievalResults containing queries and their retrieved chunks
        """
        self.retrieval_results = retrieval_results
        logger.info(f"Loaded retrieval results for {len(self.retrieval_results)} queries")
        
        # Precompute all Rouge-L scores to avoid recomputation across metrics
        logger.info("Precomputing Rouge-L scores for all query-chunk pairs...")
        self.rouge_scores_cache = []
        
        for result in self.retrieval_results:
            query_rouge_scores = []
            for chunk in result.retrieved_chunks:
                rouge_score = self._calculate_rouge_l(result.expected_chunk, chunk['content'])
                query_rouge_scores.append(rouge_score)
            self.rouge_scores_cache.append(query_rouge_scores)
        
        total_scores = sum(len(scores) for scores in self.rouge_scores_cache)
        logger.info(f"✅ Precomputed {total_scores} Rouge-L scores for efficient metric evaluation")
    
    def evaluate_precision_at_k(self, k: int) -> MetricResult:
        """
        Evaluate precision@k using precomputed Rouge-L scores.
        
        Precision@k = (number of relevant chunks in top-k) / k
        where relevance is determined by Rouge-L score >= threshold
        
        Args:
            k: The k value for precision@k (number of top results to consider)
            
        Returns:
            MetricResult with precision@k metrics and detailed analysis
        """
        if not self.retrieval_results:
            raise ValueError("No retrieval results loaded. Call set_retrieval_results() first.")
        
        if not self.rouge_scores_cache:
            raise ValueError("Rouge-L scores not cached. This indicates an issue with set_retrieval_results().")
        
        logger.info(f"Computing precision@{k} using cached Rouge-L scores (threshold: {self.rouge_threshold})")
        
        total_precision = 0.0
        total_questions = len(self.retrieval_results)
        detailed_results = []
        queries_with_matches = 0
        
        for i, result in enumerate(self.retrieval_results):
            # Get top-k results for this query
            top_k_chunks = result.retrieved_chunks[:k]
            # Get precomputed Rouge-L scores for this query
            query_rouge_scores = self.rouge_scores_cache[i][:k]
            
            # Count matches using precomputed Rouge-L scores
            matches = []
            for j, (chunk, rouge_l_score) in enumerate(zip(top_k_chunks, query_rouge_scores)):
                is_match = rouge_l_score >= self.rouge_threshold
                if is_match:
                    matches.append({
                        'rank': j + 1,
                        'chunk_id': chunk.get('chunk_id'),
                        'content_preview': chunk.get('content', '')[:100] + '...',
                        'rouge_l_score': rouge_l_score,
                        'similarity_score': chunk.get('similarity_score', 0.0)
                    })
            
            # Calculate precision for this query
            query_precision = len(matches) / k if k > 0 else 0.0
            total_precision += query_precision
            
            if len(matches) > 0:
                queries_with_matches += 1
            
            # Store detailed results
            detailed_result = {
                'query_id': result.query_id,
                'query': result.query,
                'expected_chunk': result.expected_chunk,
                'expected_metadata': result.expected_metadata,
                'top_k_results': [
                    {
                        'rank': j + 1,
                        'content': chunk.get('content', ''),
                        'similarity_score': chunk.get('similarity_score', 0.0),
                        'document_title': chunk.get('document_title', ''),
                        'chunk_id': chunk.get('chunk_id'),
                        'rouge_l_score': query_rouge_scores[j],
                        'is_relevant': query_rouge_scores[j] >= self.rouge_threshold
                    }
                    for j, chunk in enumerate(top_k_chunks)
                ],
                'matches_found': len(matches),
                'query_precision': query_precision,
                'match_details': matches,
                'retrieval_metadata': {
                    'total_retrieved': len(result.retrieved_chunks),
                    'top_k_used': k,
                    'rouge_threshold': self.rouge_threshold
                }
            }
            detailed_results.append(detailed_result)
        
        # Calculate overall precision@k
        precision_at_k = total_precision / total_questions if total_questions > 0 else 0.0
        
        return MetricResult(
            metric_name=f"precision_at_{k}",
            k_value=k,
            score=precision_at_k,
            correct_retrievals=queries_with_matches,
            total_questions=total_questions,
            detailed_results=detailed_results,
            evaluation_timestamp=datetime.now().isoformat(),
            rouge_threshold=self.rouge_threshold,
            metadata={
                'metric_type': 'precision',
                'k_value': k,
                'rouge_threshold': self.rouge_threshold,
                'total_matches_across_queries': sum(len(dr['match_details']) for dr in detailed_results)
            }
        )
    
    def evaluate_recall_at_k(self, k: int) -> MetricResult:
        """
        Evaluate recall@k using precomputed Rouge-L scores.
        
        Recall@k = (expected chunk found in top-k) / (total expected chunks)
        
        Since we have one expected_chunk (ground truth) per query, total relevant is always 1.
        Recall@k is 1.0 if we find the expected chunk in top-k (Rouge-L >= threshold), 0.0 otherwise.
        
        Args:
            k: The k value for recall@k (number of top results to consider)
            
        Returns:
            MetricResult with recall@k metrics and detailed analysis
        """
        if not self.retrieval_results:
            raise ValueError("No retrieval results loaded. Call set_retrieval_results() first.")
        
        if not self.rouge_scores_cache:
            raise ValueError("Rouge-L scores not cached. This indicates an issue with set_retrieval_results().")
        
        logger.info(f"Computing recall@{k} using cached Rouge-L scores (threshold: {self.rouge_threshold})")
        
        total_recall = 0.0
        total_questions = len(self.retrieval_results)
        detailed_results = []
        queries_with_matches = 0
        
        for i, result in enumerate(self.retrieval_results):
            # Get precomputed Rouge-L scores for this query
            query_rouge_scores = self.rouge_scores_cache[i]
            
            # Check if expected chunk is found in top-k using cached scores
            top_k_rouge_scores = query_rouge_scores[:k]
            relevant_in_top_k = []
            for j, rouge_l_score in enumerate(top_k_rouge_scores):
                if rouge_l_score >= self.rouge_threshold:
                    relevant_in_top_k.append({
                        'rank': j + 1,
                        'chunk_id': result.retrieved_chunks[j].get('chunk_id'),
                        'rouge_l_score': rouge_l_score
                    })
            
            # Calculate recall for this query
            # total_relevant is always 1 since we have one expected_chunk (ground truth)
            total_relevant = 1
            # found_relevant is 1 if we found the expected chunk in top-k, 0 otherwise
            found_relevant = 1 if len(relevant_in_top_k) > 0 else 0
            
            query_recall = found_relevant / total_relevant  # Either 0.0 or 1.0
            total_recall += query_recall
            
            if found_relevant > 0:
                queries_with_matches += 1
            
            # Store detailed results
            detailed_result = {
                'query_id': result.query_id,
                'query': result.query,
                'expected_chunk': result.expected_chunk,
                'expected_metadata': result.expected_metadata,
                'total_relevant_chunks': total_relevant,  # Always 1
                'expected_chunk_found_in_top_k': found_relevant,  # 0 or 1
                'query_recall': query_recall,
                'relevant_chunks_details': relevant_in_top_k,
                'best_match_in_top_k': max(top_k_rouge_scores) if top_k_rouge_scores else 0.0,
                'retrieval_metadata': {
                    'total_retrieved': len(result.retrieved_chunks),
                    'top_k_used': k,
                    'rouge_threshold': self.rouge_threshold,
                    'total_relevant_explanation': 'Always 1 since we have one expected_chunk'
                }
            }
            detailed_results.append(detailed_result)
        
        # Calculate overall recall@k
        recall_at_k = total_recall / total_questions if total_questions > 0 else 0.0
        
        return MetricResult(
            metric_name=f"recall_at_{k}",
            k_value=k,
            score=recall_at_k,
            correct_retrievals=queries_with_matches,
            total_questions=total_questions,
            detailed_results=detailed_results,
            evaluation_timestamp=datetime.now().isoformat(),
            rouge_threshold=self.rouge_threshold,
            metadata={
                'metric_type': 'recall',
                'k_value': k,
                'rouge_threshold': self.rouge_threshold,
                'total_relevant_per_query': 1,  # Always 1 since we have one expected_chunk per query
                'avg_best_match_score': sum(dr['best_match_in_top_k'] for dr in detailed_results) / len(detailed_results) if detailed_results else 0
            }
        )
    
    def evaluate_mrr(self) -> MetricResult:
        """
        Evaluate Mean Reciprocal Rank (MRR) using Rouge-L scoring.
        
        MRR = (1/|Q|) * Σ(1/rank_i) where rank_i is the rank of the first relevant result for query i
        """
        if not self.retrieval_results:
            raise ValueError("No retrieval results loaded. Call set_retrieval_results() first.")
        
        if not self.rouge_scores_cache:
            raise ValueError("Rouge-L scores not cached. This indicates an issue with set_retrieval_results().")
        
        logger.info(f"Computing MRR using cached Rouge-L scores (threshold: {self.rouge_threshold})")
        
        reciprocal_ranks = []
        detailed_results = []
        queries_with_relevant = 0
        
        for i, result in enumerate(self.retrieval_results):
            reciprocal_rank = 0.0
            first_relevant_rank = None
            first_relevant_score = None
            
            # Get precomputed Rouge-L scores for this query
            query_rouge_scores = self.rouge_scores_cache[i]
            
            # Find the rank of the first relevant result using cached scores
            for rank, rouge_l_score in enumerate(query_rouge_scores, 1):
                if rouge_l_score >= self.rouge_threshold:
                    reciprocal_rank = 1.0 / rank
                    first_relevant_rank = rank
                    first_relevant_score = rouge_l_score
                    queries_with_relevant += 1
                    break
            
            reciprocal_ranks.append(reciprocal_rank)
            
            detailed_result = {
                'query_id': result.query_id,
                'query': result.query,
                'expected_chunk': result.expected_chunk,
                'expected_metadata': result.expected_metadata,
                'reciprocal_rank': reciprocal_rank,
                'first_relevant_rank': first_relevant_rank,
                'first_relevant_rouge_score': first_relevant_score,
                'total_retrieved': len(result.retrieved_chunks)
            }
            detailed_results.append(detailed_result)
        
        # Calculate MRR
        mrr_score = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0
        
        return MetricResult(
            metric_name="mrr",
            k_value=None,
            score=mrr_score,
            correct_retrievals=queries_with_relevant,
            total_questions=len(self.retrieval_results),
            detailed_results=detailed_results,
            evaluation_timestamp=datetime.now().isoformat(),
            rouge_threshold=self.rouge_threshold,
            metadata={
                'metric_type': 'mrr',
                'rouge_threshold': self.rouge_threshold,
                'queries_with_relevant_results': queries_with_relevant
            }
        )
    
    def evaluate_ndcg_at_k(self, k: int) -> MetricResult:
        """
        Evaluate NDCG@k (Normalized Discounted Cumulative Gain) using binary relevance.
        
        NDCG@k = DCG@k / IDCG@k
        where DCG@k = Σ(i=1 to k) rel_i / log2(i+1) (rel_i = 1 if rouge_score >= threshold, 0 otherwise)
        and IDCG@k = perfect ranking of relevant documents (binary relevance)
        
        Uses binary relevance for both DCG and IDCG to ensure mathematical soundness (NDCG ≤ 1.0).
        Rouge-L scores are used to determine relevance, but DCG uses binary values.
        
        Args:
            k: The k value for NDCG@k (number of top results to consider)
            
        Returns:
            MetricResult with NDCG@k metrics and detailed analysis
        """
        if not self.retrieval_results:
            raise ValueError("No retrieval results loaded. Call set_retrieval_results() first.")
        
        if not self.rouge_scores_cache:
            raise ValueError("Rouge-L scores not cached. This indicates an issue with set_retrieval_results().")
        
        logger.info(f"Computing NDCG@{k} using binary relevance (Rouge-L threshold: {self.rouge_threshold})")
        
        total_ndcg = 0.0
        total_questions = len(self.retrieval_results)
        detailed_results = []
        queries_with_nonzero_scores = 0
        
        for i, result in enumerate(self.retrieval_results):
            # Get precomputed Rouge-L scores for this query
            query_rouge_scores = self.rouge_scores_cache[i]
            
            # Calculate DCG@k for actual ranking using binary relevance
            dcg_at_k = 0.0
            relevant_positions = []
            
            for j in range(min(k, len(query_rouge_scores))):
                rouge_score = query_rouge_scores[j]
                # Use binary relevance: 1.0 if above threshold, 0.0 otherwise
                relevance = 1.0 if rouge_score >= self.rouge_threshold else 0.0
                dcg_at_k += relevance / math.log2(j + 2)  # j+2 because log2(1) is 0
                
                if relevance > 0:
                    relevant_positions.append({
                        'position': j + 1,
                        'rouge_score': rouge_score,
                        'binary_relevance': relevance
                    })
            
            # Calculate IDCG@k (Ideal DCG) - perfect ranking using binary relevance
            # Count how many documents are relevant (above threshold)
            relevant_count = sum(1 for score in query_rouge_scores if score >= self.rouge_threshold)
            
            # IDCG@k: place all relevant documents at top positions with binary relevance (1.0)
            ideal_relevant_k = min(k, relevant_count)
            
            idcg_at_k = 0.0
            for j in range(ideal_relevant_k):
                # Use binary relevance: 1.0 for each relevant document in ideal ranking
                idcg_at_k += 1.0 / math.log2(j + 2)
            
            # Calculate NDCG@k
            query_ndcg = dcg_at_k / idcg_at_k if idcg_at_k > 0 else 0.0
            total_ndcg += query_ndcg
            
            # Count queries with relevant documents in top-k
            if len(relevant_positions) > 0:
                queries_with_nonzero_scores += 1
            
            # Store detailed results
            detailed_result = {
                'query_id': result.query_id,
                'query': result.query,
                'expected_chunk': result.expected_chunk,
                'expected_metadata': result.expected_metadata,
                'dcg_at_k': dcg_at_k,
                'idcg_at_k': idcg_at_k,
                'query_ndcg': query_ndcg,
                'relevant_positions': relevant_positions,
                'top_k_rouge_scores': query_rouge_scores[:k],
                'relevant_documents_total': relevant_count,
                'relevant_in_top_k': len(relevant_positions),
                'max_rouge_in_top_k': max(query_rouge_scores[:k]) if query_rouge_scores[:k] else 0.0,
                'retrieval_metadata': {
                    'total_retrieved': len(result.retrieved_chunks),
                    'top_k_used': k,
                    'uses_binary_relevance': True,
                    'rouge_threshold': self.rouge_threshold
                }
            }
            detailed_results.append(detailed_result)
        
        # Calculate overall NDCG@k
        ndcg_at_k = total_ndcg / total_questions if total_questions > 0 else 0.0
        
        return MetricResult(
            metric_name=f"ndcg_at_{k}",
            k_value=k,
            score=ndcg_at_k,
            correct_retrievals=queries_with_nonzero_scores,  # Queries with some relevance
            total_questions=total_questions,
            detailed_results=detailed_results,
            evaluation_timestamp=datetime.now().isoformat(),
            rouge_threshold=self.rouge_threshold,
            metadata={
                'metric_type': 'ndcg',
                'k_value': k,
                'uses_binary_relevance': True,
                'rouge_threshold': self.rouge_threshold,
                'avg_max_rouge_in_top_k': sum(dr['max_rouge_in_top_k'] for dr in detailed_results) / len(detailed_results) if detailed_results else 0,
                'avg_relevant_docs_per_query': sum(dr['relevant_documents_total'] for dr in detailed_results) / len(detailed_results) if detailed_results else 0,
                'idcg_calculation': 'Uses binary relevance (1.0 for relevant docs) for mathematical soundness'
            }
        )
    
    def evaluate_multiple_metrics(self, k_values: List[int], metrics: List[str] = None) -> Dict[str, MetricResult]:
        """
        Evaluate multiple metrics on the same retrieval results.
        
        Args:
            k_values: List of k values for precision@k, recall@k, and NDCG@k
            metrics: List of metrics to evaluate ['precision', 'recall', 'mrr', 'ndcg']
            
        Returns:
            Dictionary mapping metric names to MetricResult objects
        """
        if metrics is None:
            metrics = ['precision', 'recall', 'mrr', 'ndcg']
        
        results = {}
        
        # Evaluate precision@k, recall@k, and NDCG@k for each k
        if 'precision' in metrics:
            for k in k_values:
                metric_name = f"precision_at_{k}"
                results[metric_name] = self.evaluate_precision_at_k(k)
        
        if 'recall' in metrics:
            for k in k_values:
                metric_name = f"recall_at_{k}"
                results[metric_name] = self.evaluate_recall_at_k(k)
        
        if 'ndcg' in metrics:
            for k in k_values:
                metric_name = f"ndcg_at_{k}"
                results[metric_name] = self.evaluate_ndcg_at_k(k)
        
        # Evaluate MRR (doesn't depend on k)
        if 'mrr' in metrics:
            results['mrr'] = self.evaluate_mrr()
        
        return results
    
    def _calculate_rouge_l(self, reference: str, candidate: str) -> float:
        """
        Calculate Rouge-L score between reference and candidate texts using rouge-score library.
        
        Args:
            reference: Reference text (expected chunk)
            candidate: Candidate text (retrieved chunk)
            
        Returns:
            Rouge-L F1 score between 0.0 and 1.0
        """
        if not reference or not candidate:
            return 0.0
        
        try:
            # Use rouge-score library for accurate Rouge-L calculation
            scores = self.rouge_scorer.score(reference, candidate)
            # Return F1 score for Rouge-L (harmonic mean of precision and recall)
            return scores['rougeL'].fmeasure
        except Exception as e:
            logger.warning(f"Error calculating Rouge-L score: {e}")
            return 0.0
    
    def analyze_results(self, result: MetricResult) -> Dict[str, Any]:
        """Provide detailed analysis of metric results."""
        analysis = {
            'summary': {
                'metric_name': result.metric_name,
                'score': result.score,
                'success_rate_percent': result.score * 100,
                'correct_retrievals': result.correct_retrievals,
                'failed_retrievals': result.total_questions - result.correct_retrievals,
                'total_questions': result.total_questions,
                'rouge_threshold': result.rouge_threshold
            },
            'distribution': {
                'matches_by_rank': {},
                'rouge_score_stats': {},
                'error_count': 0
            }
        }
        
        # Analyze match distribution and Rouge scores
        rouge_scores = []
        rank_matches = {}
        
        for detail in result.detailed_results:
            if 'error' in detail:
                analysis['distribution']['error_count'] += 1
                continue
            
            # For precision and recall metrics
            if 'match_details' in detail:
                for match in detail['match_details']:
                    rank = match['rank']
                    rank_matches[rank] = rank_matches.get(rank, 0) + 1
                    rouge_scores.append(match['rouge_l_score'])
            
            # For MRR metric
            elif 'first_relevant_rouge_score' in detail and detail['first_relevant_rouge_score']:
                rouge_scores.append(detail['first_relevant_rouge_score'])
        
        analysis['distribution']['matches_by_rank'] = rank_matches
        
        # Rouge score statistics
        if rouge_scores:
            analysis['distribution']['rouge_score_stats'] = {
                'mean': sum(rouge_scores) / len(rouge_scores),
                'min': min(rouge_scores),
                'max': max(rouge_scores),
                'count': len(rouge_scores),
                'above_threshold': sum(1 for score in rouge_scores if score >= result.rouge_threshold)
            }
        
        return analysis


def get_retrieval_metrics_evaluator(rouge_threshold: float) -> RetrievalMetricsEvaluator:
    """
    Factory function to create a retrieval metrics evaluator service component.
    
    The evaluator precomputes all Rouge-L scores once when retrieval results are set,
    then reuses cached scores for efficient evaluation of multiple metrics.
    
    Features:
    - Multilingual tokenizer for Chinese + English content
    - Rouge-L score caching for performance optimization
    - Support for precision@k, recall@k, NDCG@k (with binary relevance), and MRR metrics
    - Proper multi-chunk aware evaluation
    
    Args:
        rouge_threshold: Minimum Rouge-L score to consider a match
        
    Returns:
        RetrievalMetricsEvaluator instance with multilingual Rouge-L scoring and caching
    """
    return RetrievalMetricsEvaluator(rouge_threshold=rouge_threshold)