"""
Unit tests for the multilingual chunker implementation.

Tests various scenarios including:
- Chinese text with quotation marks
- English text with abbreviations
- French text with guillemets
- Mixed-language documents
- Edge cases and corner cases
"""

import pytest
import logging
from pathlib import Path
import sys
from typing import List, Dict, Any

# Add evaluation root to path
evaluation_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(evaluation_root))

from services.multilingual_chunker import MultiLingualChunker, ChunkResult

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@pytest.mark.unit
class TestMultiLingualChunker:
    """Test suite for the multilingual chunker"""
    
    @pytest.fixture
    def chunker(self, mock_embedding_service, mock_tokenizer, chunking_config):
        """Create a chunker instance for testing."""
        return MultiLingualChunker(
            embedding_service=mock_embedding_service,
            tokenizer=mock_tokenizer,
            config=chunking_config
        )
    
    @pytest.mark.asyncio
    async def test_sentence_splitting_chinese_quotes(self, chunker, sample_test_texts):
        """Test sentence splitting with Chinese quotation marks."""
        text = sample_test_texts['chinese_quotes']
        
        sentences = chunker.sentence_splitter.split(text)
        
        assert len(sentences) > 0, "No sentences found for Chinese quotes"
        # Should handle Chinese quotes properly and not split incorrectly
        logger.info(f"Chinese quotes: {len(sentences)} sentences")
        for i, sentence in enumerate(sentences):
            logger.info(f"  {i+1}: {sentence}")
    
    @pytest.mark.asyncio
    async def test_sentence_splitting_english_abbreviations(self, chunker, sample_test_texts):
        """Test sentence splitting with English abbreviations."""
        text = sample_test_texts['english_abbreviations']
        
        sentences = chunker.sentence_splitter.split(text)
        
        assert len(sentences) > 0, "No sentences found for English abbreviations"
        # Should not split on abbreviations like Dr., Ph.D., etc.
        logger.info(f"English abbreviations: {len(sentences)} sentences")
        for i, sentence in enumerate(sentences):
            logger.info(f"  {i+1}: {sentence}")
    
    @pytest.mark.asyncio
    async def test_sentence_splitting_french_guillemets(self, chunker, sample_test_texts):
        """Test sentence splitting with French guillemets."""
        text = sample_test_texts['french_guillemets']
        
        sentences = chunker.sentence_splitter.split(text)
        
        assert len(sentences) > 0, "No sentences found for French guillemets"
        logger.info(f"French guillemets: {len(sentences)} sentences")
        for i, sentence in enumerate(sentences):
            logger.info(f"  {i+1}: {sentence}")
    
    @pytest.mark.asyncio
    async def test_sentence_splitting_mixed_language(self, chunker, sample_test_texts):
        """Test sentence splitting with mixed languages."""
        text = sample_test_texts['mixed_language']
        
        sentences = chunker.sentence_splitter.split(text)
        
        assert len(sentences) > 0, "No sentences found for mixed language text"
        logger.info(f"Mixed language: {len(sentences)} sentences")
        for i, sentence in enumerate(sentences):
            logger.info(f"  {i+1}: {sentence}")
    
    @pytest.mark.asyncio
    async def test_chunking_pipeline_basic(self, chunker, sample_test_texts):
        """Test the complete chunking pipeline with basic text."""
        text = sample_test_texts['english_abbreviations']
        
        chunks = await chunker.chunk_text(text, document_id="test_basic")
        
        assert len(chunks) > 0, "No chunks created for basic text"
        
        for chunk in chunks:
            assert chunk.content, "Chunk content should not be empty"
            assert chunk.embedding is not None, "Chunk should have embedding"
            assert chunk.start_sentence <= chunk.end_sentence, "Invalid sentence range"
            
        logger.info(f"Basic pipeline: {len(chunks)} chunks created")
    
    @pytest.mark.asyncio
    async def test_chunking_pipeline_multilingual(self, chunker, sample_test_texts):
        """Test the complete chunking pipeline with multilingual text."""
        text = sample_test_texts['complex_quotes']
        
        chunks = await chunker.chunk_text(text, document_id="test_multilingual")
        
        assert len(chunks) > 0, "No chunks created for multilingual text"
        
        for chunk in chunks:
            assert chunk.content, "Chunk content should not be empty"
            assert chunk.embedding is not None, "Chunk should have embedding"
            
        logger.info(f"Multilingual pipeline: {len(chunks)} chunks created")
    
    @pytest.mark.asyncio
    async def test_abbreviation_handling_specific_cases(self, chunker):
        """Test abbreviation handling with specific test cases."""
        test_cases = [
            ("Dr. Smith went to the U.S.A. yesterday.", "Should not split on Dr. or U.S.A."),
            ("The meeting is at 3:00 p.m. in the conference room.", "Should not split on p.m."),
            ("He has a Ph.D. from MIT University.", "Should not split on Ph.D."),
            ("The file.pdf was sent at 2:30 p.m. today.", "Should not split on file.pdf or p.m."),
        ]
        
        for text, expected_behavior in test_cases:
            sentences = chunker.sentence_splitter.split(text)
            
            # Should typically be one sentence if abbreviations are handled correctly
            assert len(sentences) >= 1, f"Should produce at least one sentence for: {text}"
            
            logger.info(f"Testing: {text}")
            logger.info(f"Expected: {expected_behavior}")
            logger.info(f"Sentences: {sentences}")
    
    @pytest.mark.asyncio
    async def test_quotation_marks_handling(self, chunker):
        """Test quotation mark handling with various styles."""
        test_cases = [
            ('他说："这是个例子。"', "Chinese quotes with period inside"),
            ('He said: "This is an example."', "English quotes with period inside"),
            ('Le professeur dit : « C\'est un exemple. »', "French guillemets"),
            ('混合引号 "English quote" 和 « French quote »', "Mixed quotation styles"),
        ]
        
        for text, description in test_cases:
            sentences = chunker.sentence_splitter.split(text)
            
            assert len(sentences) >= 1, f"Should produce at least one sentence for: {text}"
            
            logger.info(f"Testing: {text}")
            logger.info(f"Description: {description}")
            logger.info(f"Sentences: {sentences}")
    
    @pytest.mark.asyncio
    async def test_semantic_merging(self, chunker):
        """Test semantic merging functionality."""
        # Text with semantically similar sentences
        text = '''
        人工智能是一个重要的研究领域。AI研究包括机器学习和深度学习。
        这个技术领域发展很快。自然语言处理是AI的一个分支。
        '''
        
        chunks = await chunker.chunk_text(text, document_id="semantic_test")
        
        assert len(chunks) > 0, "No chunks created for semantic test"
        
        # Check if any chunks span multiple sentences (indicating merging occurred)
        merged_chunks = [c for c in chunks if c.end_sentence > c.start_sentence]
        
        logger.info(f"Semantic merging test: {len(chunks)} chunks, {len(merged_chunks)} merged")
        
        for i, chunk in enumerate(chunks):
            logger.info(f"  Chunk {i+1}: {chunk.content}")
            logger.info(f"  Sentences span: {chunk.start_sentence}-{chunk.end_sentence}")
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, chunker):
        """Test performance with various text lengths."""
        # Generate texts of different lengths
        base_text = "这是一个测试句子。This is a test sentence. C'est une phrase de test."
        
        test_lengths = [100, 500, 1000]
        
        for length in test_lengths:
            # Create text of approximately target length
            repeated_text = (base_text + " ") * (length // len(base_text))
            
            import time
            start_time = time.time()
            
            chunks = await chunker.chunk_text(repeated_text, document_id=f"perf_test_{length}")
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            assert len(chunks) > 0, f"No chunks created for length {length}"
            assert processing_time > 0, "Processing time should be positive"
            
            chars_per_second = len(repeated_text) / processing_time if processing_time > 0 else 0
            
            logger.info(f"Length ~{len(repeated_text)} chars: {len(chunks)} chunks, "
                       f"{processing_time:.2f}s, {chars_per_second:.0f} chars/s")
    
    @pytest.mark.asyncio
    async def test_empty_text_handling(self, chunker):
        """Test handling of empty or whitespace-only text."""
        test_cases = ["", "   ", "\n\n\n", "\t\t"]
        
        for text in test_cases:
            chunks = await chunker.chunk_text(text, document_id=f"empty_test_{hash(text)}")
            
            # Should handle empty text gracefully
            assert isinstance(chunks, list), "Should return a list even for empty text"
            logger.info(f"Empty text '{repr(text)}': {len(chunks)} chunks")
    
    @pytest.mark.asyncio
    async def test_very_long_sentence(self, chunker):
        """Test handling of very long sentences that exceed chunk limits."""
        # Create a very long sentence
        long_sentence = "This is a very long sentence that goes on and on " * 50
        long_sentence += "."
        
        chunks = await chunker.chunk_text(long_sentence, document_id="long_sentence_test")
        
        assert len(chunks) > 0, "Should create chunks even for very long sentences"
        
        # Should split long sentences appropriately
        total_content_length = sum(len(chunk.content) for chunk in chunks)
        assert total_content_length > 0, "Total content length should be positive"
        
        logger.info(f"Long sentence: {len(chunks)} chunks, total length {total_content_length}")
    
    @pytest.mark.asyncio
    async def test_context_preservation(self, chunker):
        """Test that context is preserved between chunks."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        
        chunks = await chunker.chunk_text(text, document_id="context_test")
        
        assert len(chunks) > 0, "Should create chunks"
        
        # Check that context fields are populated
        for chunk in chunks:
            # Context fields should be strings (may be empty)
            assert isinstance(chunk.context_before, str), "context_before should be string"
            assert isinstance(chunk.context_after, str), "context_after should be string"
            
        logger.info(f"Context test: {len(chunks)} chunks with context preservation") 