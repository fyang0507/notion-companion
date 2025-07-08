#!/usr/bin/env python3
"""
Manual Sentence Similarity Analysis Tool

This script provides convenient tools for manually analyzing sentence similarities
using the cached step data from the orchestration pipeline.

Manual Analysis Tool Features:

* Document Discovery: --list-docs shows all available documents with sentence counts
* Document Information: --doc-info <doc_id> provides detailed document metadata
* Sentence Pair Analysis: --doc-id <doc_id> --indices 4 5 analyzes specific sentence pairs
* Top Similar Pairs: --top-similar 5 finds the most similar adjacent sentence pairs
* Rich Analysis Output: Includes similarity scores, content hashes, length ratios, and categorized similarity levels

Usage:
    python analyze_sentence_similarity.py --experiment-id 20250708_131759 --doc-id doc123 --indices 4 5
    python analyze_sentence_similarity.py --step2-file path/to/step2.json --step3-file path/to/step3.json
"""

import argparse
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Tuple


class SentenceSimilarityAnalyzer:
    """Tool for analyzing sentence similarities from cached pipeline data."""
    
    def __init__(self, step2_file: str = None, step3_file: str = None, experiment_id: str = None):
        """
        Initialize analyzer with step files or experiment ID.
        
        Args:
            step2_file: Path to step 2 sentence splitting file
            step3_file: Path to step 3 embedding generation file 
            experiment_id: Experiment ID to auto-find files
        """
        if experiment_id:
            # Auto-find files based on experiment ID
            cached_dir = Path(__file__).parent.parent / "data"
            step2_pattern = f"{experiment_id}_step2_sentence_splitting_*.json"
            step3_pattern = f"{experiment_id}_step3_embedding_generation_*.json"
            
            step2_files = list(cached_dir.glob(step2_pattern))
            step3_files = list(cached_dir.glob(step3_pattern))
            
            if not step2_files:
                raise FileNotFoundError(f"No step 2 file found for experiment {experiment_id}")
            if not step3_files:
                raise FileNotFoundError(f"No step 3 file found for experiment {experiment_id}")
                
            self.step2_file = step2_files[0]
            self.step3_file = step3_files[0]
        else:
            if not step2_file or not step3_file:
                raise ValueError("Must provide either experiment_id or both step2_file and step3_file")
            self.step2_file = Path(step2_file)
            self.step3_file = Path(step3_file)
        
        # Load data
        self.step2_data = self._load_step_data(self.step2_file)
        self.step3_data = self._load_step_data(self.step3_file)
        
        print(f"📂 Loaded Step 2: {self.step2_file}")
        print(f"📂 Loaded Step 3: {self.step3_file}")
        
    def _load_step_data(self, file_path: Path) -> Dict[str, Any]:
        """Load step data from JSON file."""
        if not file_path.exists():
            raise FileNotFoundError(f"Step file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data['data']
    
    def list_documents(self) -> List[str]:
        """List all available document IDs."""
        return list(self.step2_data['document_sentences'].keys())
    
    def get_document_info(self, doc_id: str) -> Dict[str, Any]:
        """Get information about a specific document."""
        if doc_id not in self.step2_data['document_sentences']:
            raise ValueError(f"Document {doc_id} not found")
        
        sentences = self.step2_data['document_sentences'][doc_id]
        return {
            'document_id': doc_id,
            'total_sentences': len(sentences),
            'sentence_indices': list(sentences.keys()),
            'title': self.step2_data['input_documents'].get(doc_id, {}).get('title', 'Unknown')
        }
    
    def get_sentence_by_index(self, doc_id: str, sentence_index: int) -> Dict[str, Any]:
        """Get sentence information by document ID and index."""
        if doc_id not in self.step2_data['document_sentences']:
            raise ValueError(f"Document {doc_id} not found")
        
        doc_sentences = self.step2_data['document_sentences'][doc_id]
        if str(sentence_index) not in doc_sentences:
            available_indices = list(doc_sentences.keys())
            raise ValueError(f"Sentence index {sentence_index} not found. Available: {available_indices}")
        
        sentence_info = doc_sentences[str(sentence_index)]
        
        # Get embedding from step 3 data using hash lookup
        sentence_hash = sentence_info['hash']
        embedding_info = self.step3_data['global_sentence_lookup'].get(sentence_hash)
        
        return {
            'document_id': doc_id,
            'sentence_index': sentence_index,
            'content': sentence_info['content'],
            'hash': sentence_hash,
            'char_length': sentence_info['char_length'],
            'word_count': sentence_info['word_count'],
            'embedding': embedding_info['embedding'] if embedding_info else None,
            'embedding_dimensions': len(embedding_info['embedding']) if embedding_info and embedding_info['embedding'] else 0
        }
    
    def calculate_cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings."""
        if not embedding1 or not embedding2:
            raise ValueError("Both embeddings must be provided and non-empty")
        
        # Convert to numpy arrays
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norms = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        
        if norms == 0:
            return 0.0
        
        return dot_product / norms
    
    def analyze_sentence_pair(self, doc_id: str, index1: int, index2: int) -> Dict[str, Any]:
        """Analyze similarity between two sentences in the same document."""
        sentence1 = self.get_sentence_by_index(doc_id, index1)
        sentence2 = self.get_sentence_by_index(doc_id, index2)
        
        # Calculate similarity
        similarity = self.calculate_cosine_similarity(sentence1['embedding'], sentence2['embedding'])
        
        return {
            'sentence1': sentence1,
            'sentence2': sentence2,
            'cosine_similarity': similarity,
            'analysis': {
                'similarity_level': self._categorize_similarity(similarity),
                'length_ratio': sentence2['char_length'] / sentence1['char_length'] if sentence1['char_length'] > 0 else 0,
                'word_count_ratio': sentence2['word_count'] / sentence1['word_count'] if sentence1['word_count'] > 0 else 0
            }
        }
    
    def _categorize_similarity(self, similarity: float) -> str:
        """Categorize similarity score into human-readable levels."""
        if similarity >= 0.9:
            return "Very High (0.9+)"
        elif similarity >= 0.7:
            return "High (0.7-0.9)"
        elif similarity >= 0.5:
            return "Moderate (0.5-0.7)"
        elif similarity >= 0.3:
            return "Low (0.3-0.5)"
        else:
            return "Very Low (<0.3)"
    
    def find_most_similar_pairs(self, doc_id: str, top_n: int = 10) -> List[Dict[str, Any]]:
        """Find the most similar adjacent sentence pairs in a document."""
        doc_info = self.get_document_info(doc_id)
        total_sentences = doc_info['total_sentences']
        
        similarities = []
        
        for i in range(total_sentences - 1):
            try:
                analysis = self.analyze_sentence_pair(doc_id, i, i + 1)
                similarities.append({
                    'indices': (i, i + 1),
                    'similarity': analysis['cosine_similarity'],
                    'sentence1_preview': analysis['sentence1']['content'][:100] + "..." if len(analysis['sentence1']['content']) > 100 else analysis['sentence1']['content'],
                    'sentence2_preview': analysis['sentence2']['content'][:100] + "..." if len(analysis['sentence2']['content']) > 100 else analysis['sentence2']['content']
                })
            except Exception as e:
                print(f"Warning: Could not analyze pair ({i}, {i+1}): {e}")
                continue
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        return similarities[:top_n]
    
    def print_analysis_report(self, doc_id: str, index1: int, index2: int):
        """Print a detailed analysis report for two sentences."""
        analysis = self.analyze_sentence_pair(doc_id, index1, index2)
        
        print("\n" + "="*80)
        print("📊 SENTENCE SIMILARITY ANALYSIS")
        print("="*80)
        print(f"Document ID: {doc_id}")
        print(f"Sentence Indices: {index1} ↔ {index2}")
        print(f"Cosine Similarity: {analysis['cosine_similarity']:.4f}")
        print(f"Similarity Level: {analysis['analysis']['similarity_level']}")
        print()
        
        print("📝 SENTENCE 1:")
        print(f"  Index: {analysis['sentence1']['sentence_index']}")
        print(f"  Hash: {analysis['sentence1']['hash']}")
        print(f"  Length: {analysis['sentence1']['char_length']} chars, {analysis['sentence1']['word_count']} words")
        print(f"  Content: {analysis['sentence1']['content']}")
        print()
        
        print("📝 SENTENCE 2:")
        print(f"  Index: {analysis['sentence2']['sentence_index']}")
        print(f"  Hash: {analysis['sentence2']['hash']}")
        print(f"  Length: {analysis['sentence2']['char_length']} chars, {analysis['sentence2']['word_count']} words")
        print(f"  Content: {analysis['sentence2']['content']}")
        print()
        
        print("📈 ANALYSIS:")
        print(f"  Length Ratio: {analysis['analysis']['length_ratio']:.2f}")
        print(f"  Word Count Ratio: {analysis['analysis']['word_count_ratio']:.2f}")
        print(f"  Embedding Dimensions: {analysis['sentence1']['embedding_dimensions']}")
        print("="*80)


def main():
    """Main entry point for the analysis tool."""
    parser = argparse.ArgumentParser(description='Analyze sentence similarities from cached pipeline data')
    
    # Input methods
    parser.add_argument('--experiment-id', help='Experiment ID to auto-find files')
    parser.add_argument('--step2-file', help='Path to step 2 sentence splitting file')
    parser.add_argument('--step3-file', help='Path to step 3 embedding generation file')
    
    # Analysis options
    parser.add_argument('--doc-id', help='Document ID to analyze')
    parser.add_argument('--indices', nargs=2, type=int, help='Two sentence indices to compare')
    parser.add_argument('--list-docs', action='store_true', help='List all available documents')
    parser.add_argument('--doc-info', help='Get information about a specific document')
    parser.add_argument('--top-similar', type=int, default=10, help='Find top N most similar adjacent pairs')
    
    args = parser.parse_args()
    
    # Validate input
    if not args.experiment_id and not (args.step2_file and args.step3_file):
        print("❌ Error: Must provide either --experiment-id or both --step2-file and --step3-file")
        return
    
    try:
        # Initialize analyzer
        analyzer = SentenceSimilarityAnalyzer(
            step2_file=args.step2_file,
            step3_file=args.step3_file,
            experiment_id=args.experiment_id
        )
        
        # Handle different analysis commands
        if args.list_docs:
            print("\n📋 Available Documents:")
            docs = analyzer.list_documents()
            for i, doc_id in enumerate(docs):
                doc_info = analyzer.get_document_info(doc_id)
                print(f"  {i+1}. {doc_id} ({doc_info['total_sentences']} sentences) - {doc_info['title']}")
        
        elif args.doc_info:
            doc_info = analyzer.get_document_info(args.doc_info)
            print(f"\n📄 Document Information:")
            print(f"  ID: {doc_info['document_id']}")
            print(f"  Title: {doc_info['title']}")
            print(f"  Total Sentences: {doc_info['total_sentences']}")
            print(f"  Available Indices: 0 to {doc_info['total_sentences'] - 1}")
        
        elif args.doc_id and args.indices:
            # Analyze specific sentence pair
            analyzer.print_analysis_report(args.doc_id, args.indices[0], args.indices[1])
        
        elif args.doc_id:
            # Find most similar pairs in document
            print(f"\n🔍 Top {args.top_similar} Most Similar Adjacent Sentence Pairs:")
            pairs = analyzer.find_most_similar_pairs(args.doc_id, args.top_similar)
            
            for i, pair in enumerate(pairs):
                print(f"\n{i+1}. Indices {pair['indices'][0]}-{pair['indices'][1]} (Similarity: {pair['similarity']:.4f})")
                print(f"   Sentence {pair['indices'][0]}: {pair['sentence1_preview']}")
                print(f"   Sentence {pair['indices'][1]}: {pair['sentence2_preview']}")
        
        else:
            print("❌ Error: Please specify an analysis command. Use --help for options.")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()