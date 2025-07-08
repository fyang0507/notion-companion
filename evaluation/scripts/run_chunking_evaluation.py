#!/usr/bin/env python3
"""
Integration script for multilingual chunker evaluation.

This script demonstrates how to use the multilingual chunker with real data
from the evaluation/data/ folder, integrating with the evaluation system
architecture.
"""

import asyncio
import logging
import json
from pathlib import Path
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.multilingual_chunker import MultiLingualChunker, ChunkResult
from utils.config_loader import ConfigLoader
from scripts.test_multilingual_chunker import MockEmbeddingService, MockTokenizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(project_root / "logs" / "chunking_evaluation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ChunkingEvaluationRunner:
    """Main class for running chunking evaluation on real data"""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = project_root / "data"
        
        self.data_dir = Path(data_dir)
        self.output_dir = project_root / "logs" / "chunking_results"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize services
        self.config_loader = ConfigLoader()
        self.embedding_service = MockEmbeddingService()
        self.tokenizer = MockTokenizer()
        
        # Load configuration (now returns dict directly)
        self.config = self.config_loader.load_chunking_config()
        
        # Initialize chunker
        self.chunker = MultiLingualChunker(
            embedding_service=self.embedding_service,
            tokenizer=self.tokenizer,
            config=self.config
        )
        
        logger.info(f"ChunkingEvaluationRunner initialized")
        logger.info(f"Data directory: {self.data_dir}")
        logger.info(f"Output directory: {self.output_dir}")
    
    def discover_documents(self) -> List[Dict[str, Any]]:
        """Discover all documents in the data directory"""
        documents = []
        
        # Look for different file types
        text_extensions = ['.txt', '.md', '.json']
        
        for ext in text_extensions:
            for file_path in self.data_dir.glob(f"**/*{ext}"):
                if file_path.is_file():
                    documents.append({
                        'path': file_path,
                        'name': file_path.name,
                        'relative_path': file_path.relative_to(self.data_dir),
                        'size': file_path.stat().st_size,
                        'extension': ext
                    })
        
        logger.info(f"Discovered {len(documents)} documents")
        return documents
    
    def load_document_content(self, doc_info: Dict[str, Any]) -> Optional[str]:
        """Load content from a document file"""
        try:
            file_path = doc_info['path']
            
            if doc_info['extension'] == '.json':
                # Handle JSON documents (might contain structured data)
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Extract text content from JSON
                content = self._extract_text_from_json(data)
                
            else:
                # Handle plain text files
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to load document {doc_info['name']}: {str(e)}")
            return None
    
    def _extract_text_from_json(self, data: Any) -> str:
        """Extract text content from JSON data"""
        if isinstance(data, str):
            return data
        elif isinstance(data, dict):
            # Common fields that might contain text content
            text_fields = ['content', 'text', 'body', 'description', 'title', 'summary']
            
            texts = []
            for field in text_fields:
                if field in data and isinstance(data[field], str):
                    texts.append(data[field])
            
            # Recursively extract from nested objects
            for key, value in data.items():
                if key not in text_fields:
                    nested_text = self._extract_text_from_json(value)
                    if nested_text:
                        texts.append(nested_text)
            
            return '\n'.join(texts)
        elif isinstance(data, list):
            texts = []
            for item in data:
                text = self._extract_text_from_json(item)
                if text:
                    texts.append(text)
            return '\n'.join(texts)
        
        return str(data) if data is not None else ""
    
    async def process_document(self, doc_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single document through the chunking pipeline"""
        logger.info(f"Processing document: {doc_info['name']}")
        
        # Load document content
        content = self.load_document_content(doc_info)
        if not content:
            return {
                'document': doc_info,
                'status': 'failed',
                'error': 'Failed to load content'
            }
        
        # Detect language characteristics
        language_info = self._analyze_language_characteristics(content)
        
        # Process through chunking pipeline
        try:
            start_time = datetime.now()
            
            chunks = await self.chunker.chunk_text(
                content, 
                document_id=str(doc_info['relative_path'])
            )
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # Generate chunk statistics
            chunk_stats = self._generate_chunk_statistics(chunks)
            
            result = {
                'document': doc_info,
                'status': 'success',
                'processing_time': processing_time,
                'content_length': len(content),
                'language_info': language_info,
                'chunk_count': len(chunks),
                'chunk_statistics': chunk_stats,
                'chunks': [
                    {
                        'content': chunk.content,
                        'start_sentence': chunk.start_sentence,
                        'end_sentence': chunk.end_sentence,
                        'has_embedding': chunk.embedding is not None,
                        'context_before': chunk.context_before,
                        'context_after': chunk.context_after,
                        'token_count': len(self.tokenizer.encode(chunk.content))
                    }
                    for chunk in chunks
                ]
            }
            
            logger.info(f"Successfully processed {doc_info['name']}: {len(chunks)} chunks in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process document {doc_info['name']}: {str(e)}")
            return {
                'document': doc_info,
                'status': 'failed',
                'error': str(e)
            }
    
    def _analyze_language_characteristics(self, content: str) -> Dict[str, Any]:
        """Analyze language characteristics of the content"""
        # Count different character types
        chinese_chars = sum(1 for char in content if '\u4e00' <= char <= '\u9fff')
        ascii_chars = sum(1 for char in content if char.isascii())
        total_chars = len(content)
        
        # Detect punctuation usage
        chinese_punct = sum(1 for char in content if char in '。！？；')
        western_punct = sum(1 for char in content if char in '.!?')
        
        # Detect quotation marks
        quotation_marks = {}
        for quote in ['"', "'", '"', '"', ''', ''', '「', '」', '『', '』', '«', '»']:
            count = content.count(quote)
            if count > 0:
                quotation_marks[quote] = count
        
        return {
            'total_characters': total_chars,
            'chinese_characters': chinese_chars,
            'ascii_characters': ascii_chars,
            'chinese_char_ratio': chinese_chars / total_chars if total_chars > 0 else 0,
            'chinese_punctuation': chinese_punct,
            'western_punctuation': western_punct,
            'quotation_marks': quotation_marks,
            'estimated_languages': self._estimate_languages(content)
        }
    
    def _estimate_languages(self, content: str) -> List[str]:
        """Estimate languages present in the content"""
        languages = []
        
        # Chinese detection
        chinese_chars = sum(1 for char in content if '\u4e00' <= char <= '\u9fff')
        if chinese_chars > 10:
            languages.append('chinese')
        
        # French detection (basic)
        french_indicators = ['à', 'é', 'è', 'ç', 'ô', 'ù', '«', '»']
        if any(indicator in content for indicator in french_indicators):
            languages.append('french')
        
        # English detection (default for ASCII content)
        ascii_words = len([word for word in content.split() if word.isascii()])
        if ascii_words > 5:
            languages.append('english')
        
        return languages
    
    def _generate_chunk_statistics(self, chunks: List[ChunkResult]) -> Dict[str, Any]:
        """Generate statistics about the chunks"""
        if not chunks:
            return {}
        
        chunk_lengths = [len(chunk.content) for chunk in chunks]
        token_counts = [len(self.tokenizer.encode(chunk.content)) for chunk in chunks]
        
        return {
            'total_chunks': len(chunks),
            'avg_chunk_length': sum(chunk_lengths) / len(chunk_lengths),
            'min_chunk_length': min(chunk_lengths),
            'max_chunk_length': max(chunk_lengths),
            'avg_token_count': sum(token_counts) / len(token_counts),
            'min_token_count': min(token_counts),
            'max_token_count': max(token_counts),
            'chunks_with_embeddings': sum(1 for chunk in chunks if chunk.embedding is not None),
            'chunks_with_context': sum(1 for chunk in chunks if chunk.context_before or chunk.context_after),
            'multi_sentence_chunks': sum(1 for chunk in chunks if chunk.end_sentence > chunk.start_sentence),
        }
    
    def save_results(self, results: List[Dict[str, Any]]) -> Path:
        """Save evaluation results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"chunking_evaluation_{timestamp}.json"
        
        # Generate summary statistics
        summary = self._generate_summary_statistics(results)
        
        output_data = {
            'timestamp': timestamp,
            'configuration': self.config_dict,
            'summary': summary,
            'results': results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Results saved to: {output_file}")
        return output_file
    
    def _generate_summary_statistics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics across all results"""
        successful_results = [r for r in results if r['status'] == 'success']
        failed_results = [r for r in results if r['status'] == 'failed']
        
        if not successful_results:
            return {
                'total_documents': len(results),
                'successful_documents': 0,
                'failed_documents': len(failed_results),
                'success_rate': 0.0
            }
        
        total_chunks = sum(r['chunk_count'] for r in successful_results)
        total_processing_time = sum(r['processing_time'] for r in successful_results)
        total_content_length = sum(r['content_length'] for r in successful_results)
        
        return {
            'total_documents': len(results),
            'successful_documents': len(successful_results),
            'failed_documents': len(failed_results),
            'success_rate': len(successful_results) / len(results),
            'total_chunks_generated': total_chunks,
            'avg_chunks_per_document': total_chunks / len(successful_results),
            'total_processing_time': total_processing_time,
            'avg_processing_time': total_processing_time / len(successful_results),
            'total_content_processed': total_content_length,
            'avg_content_length': total_content_length / len(successful_results),
            'processing_speed_chars_per_second': total_content_length / total_processing_time if total_processing_time > 0 else 0
        }
    
    async def run_evaluation(self, max_documents: int = None) -> Path:
        """Run the complete evaluation pipeline"""
        logger.info("Starting chunking evaluation pipeline...")
        
        # Discover documents
        documents = self.discover_documents()
        
        if max_documents:
            documents = documents[:max_documents]
            logger.info(f"Limited to {max_documents} documents for evaluation")
        
        # Process documents
        results = []
        for i, doc_info in enumerate(documents):
            logger.info(f"Processing document {i+1}/{len(documents)}: {doc_info['name']}")
            
            result = await self.process_document(doc_info)
            results.append(result)
            
            # Log progress
            if (i + 1) % 10 == 0:
                successful = sum(1 for r in results if r['status'] == 'success')
                logger.info(f"Progress: {i+1}/{len(documents)} documents processed, {successful} successful")
        
        # Save results
        output_file = self.save_results(results)
        
        # Print summary
        summary = self._generate_summary_statistics(results)
        logger.info("Evaluation completed!")
        logger.info(f"Summary: {summary}")
        
        return output_file


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run multilingual chunking evaluation")
    parser.add_argument("--data-dir", type=str, help="Directory containing evaluation data")
    parser.add_argument("--max-docs", type=int, help="Maximum number of documents to process")
    parser.add_argument("--config", type=str, help="Configuration file name", default="chunking_config.toml")
    
    args = parser.parse_args()
    
    # Initialize evaluation runner
    runner = ChunkingEvaluationRunner(data_dir=args.data_dir)
    
    # Run evaluation
    try:
        output_file = await runner.run_evaluation(max_documents=args.max_docs)
        print(f"\n✅ Evaluation completed successfully!")
        print(f"Results saved to: {output_file}")
        
    except Exception as e:
        logger.error(f"❌ Evaluation failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 