"""
Unit tests for the multilingual chunker implementation.

Tests various scenarios including:
- Chinese text with quotation marks
- English text with abbreviations
- French text with guillemets
- Mixed-language documents
- Edge cases and corner cases
- Caching functionality (NEW)
"""

import pytest
import logging
from pathlib import Path
import sys
from typing import List, Dict, Any
import tempfile
import os

# Add evaluation root to path
evaluation_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(evaluation_root))

from evaluation.services.multilingual_chunker import MultiLingualChunker, ChunkResult

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


@pytest.mark.unit
class TestCachingFunctionality:
    """Test suite for caching functionality in multilingual chunker"""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def cached_chunker(self, mock_embedding_service, mock_tokenizer, chunking_config, temp_cache_dir):
        """Create a chunker instance with temporary cache directory"""
        return MultiLingualChunker(
            embedding_service=mock_embedding_service,
            tokenizer=mock_tokenizer,
            config=chunking_config,
            cache_dir=temp_cache_dir
        )
    
    @pytest.mark.asyncio
    async def test_cache_initialization(self, cached_chunker):
        """Test that cache is properly initialized"""
        cache_info = cached_chunker.get_cache_info()
        
        # Should have all required cache info fields
        assert 'cached_sentences' in cache_info
        assert 'cache_file' in cache_info
        assert 'cache_file_exists' in cache_info
        assert 'stats' in cache_info
        
        # Stats should have required fields
        stats = cache_info['stats']
        assert 'total_requests' in stats
        assert 'total_cache_hits' in stats
        assert 'total_cache_misses' in stats
        assert 'hit_rate' in stats
        
        logger.info(f"Initial cache info: {cache_info}")
    
    @pytest.mark.asyncio
    async def test_sentence_embedding_caching(self, cached_chunker):
        """Test that sentence embeddings are cached and reused"""
        # Test text with repeated sentences
        text1 = "这是一个测试句子。This is a test sentence."
        text2 = "这是一个测试句子。Another test sentence."  # First sentence repeated
        
        # First chunking - should miss cache
        chunks1 = await cached_chunker.chunk_text(text1, "cache_test_1")
        cache_info_1 = cached_chunker.get_cache_info()
        
        # Second chunking with overlapping sentences - should hit cache
        chunks2 = await cached_chunker.chunk_text(text2, "cache_test_2")
        cache_info_2 = cached_chunker.get_cache_info()
        
        # Verify chunks were created
        assert len(chunks1) > 0, "Should create chunks for first text"
        assert len(chunks2) > 0, "Should create chunks for second text"
        
        # Verify cache hits increased
        hits_1 = cache_info_1['stats']['total_cache_hits']
        hits_2 = cache_info_2['stats']['total_cache_hits']
        
        assert hits_2 > hits_1, "Cache hits should increase when reusing sentences"
        
        logger.info(f"Cache hits increased from {hits_1} to {hits_2}")
    
    @pytest.mark.asyncio
    async def test_cache_performance_improvement(self, cached_chunker):
        """Test that caching improves performance on repeated text"""
        import time
        
        text = """
        人工智能技术正在快速发展。机器学习算法变得越来越复杂。
        深度学习模型在各个领域都有应用。自然语言处理技术不断进步。
        """
        
        # First run - populates cache
        start_time = time.time()
        chunks1 = await cached_chunker.chunk_text(text, "perf_test_1")
        first_run_time = time.time() - start_time
        
        # Second run - should use cache
        start_time = time.time()
        chunks2 = await cached_chunker.chunk_text(text, "perf_test_2")
        second_run_time = time.time() - start_time
        
        # Verify results are consistent
        assert len(chunks1) == len(chunks2), "Should produce consistent results"
        
        # Log performance (second run may be faster due to caching)
        logger.info(f"Performance test - First: {first_run_time:.4f}s, Second: {second_run_time:.4f}s")
        
        # Get cache statistics
        cache_info = cached_chunker.get_cache_info()
        logger.info(f"Cache performance: {cache_info['stats']}")
    
    @pytest.mark.asyncio
    async def test_cache_consistency(self, cached_chunker):
        """Test that cached results are consistent with non-cached results"""
        text = "Consistent results test. This text should produce the same chunks."
        
        # First run - creates cache entries
        chunks1 = await cached_chunker.chunk_text(text, "consistency_test_1")
        
        # Second run - should use cache
        chunks2 = await cached_chunker.chunk_text(text, "consistency_test_2")
        
        # Verify consistency
        assert len(chunks1) == len(chunks2), "Should produce same number of chunks"
        
        for i, (chunk1, chunk2) in enumerate(zip(chunks1, chunks2)):
            assert chunk1.content == chunk2.content, f"Chunk {i} content should be identical"
            assert chunk1.start_sentence == chunk2.start_sentence, f"Chunk {i} start should be identical"
            assert chunk1.end_sentence == chunk2.end_sentence, f"Chunk {i} end should be identical"
            
        logger.info(f"Consistency test passed: {len(chunks1)} chunks are identical")
    
    @pytest.mark.asyncio
    async def test_cache_isolation(self, temp_cache_dir, mock_embedding_service, mock_tokenizer, chunking_config):
        """Test that different cache directories are properly isolated"""
        # Create two chunkers with different cache directories
        cache_dir_1 = os.path.join(temp_cache_dir, "cache1")
        cache_dir_2 = os.path.join(temp_cache_dir, "cache2")
        
        chunker1 = MultiLingualChunker(mock_embedding_service, mock_tokenizer, chunking_config, cache_dir_1)
        chunker2 = MultiLingualChunker(mock_embedding_service, mock_tokenizer, chunking_config, cache_dir_2)
        
        text = "Cache isolation test sentence."
        
        # Use first chunker
        await chunker1.chunk_text(text, "isolation_test_1")
        cache_info_1 = chunker1.get_cache_info()
        
        # Use second chunker (should have separate cache)
        await chunker2.chunk_text(text, "isolation_test_2")
        cache_info_2 = chunker2.get_cache_info()
        
        # Verify caches are isolated
        assert cache_info_1['cache_file'] != cache_info_2['cache_file'], "Cache files should be different"
        
        logger.info(f"Cache isolation test passed")
        logger.info(f"Cache 1: {cache_info_1['cache_file']}")
        logger.info(f"Cache 2: {cache_info_2['cache_file']}")
    
    @pytest.mark.asyncio
    async def test_cache_clear_functionality(self, cached_chunker):
        """Test cache clearing functionality"""
        text = "Test cache clearing with this sentence."
        
        # Create some cache entries
        await cached_chunker.chunk_text(text, "clear_test")
        cache_info_before = cached_chunker.get_cache_info()
        
        # Verify cache has entries
        assert cache_info_before['cached_sentences'] > 0, "Cache should have entries before clearing"
        
        # Clear cache
        cached_chunker.clear_cache()
        cache_info_after = cached_chunker.get_cache_info()
        
        # Verify cache is cleared
        assert cache_info_after['cached_sentences'] == 0, "Cache should be empty after clearing"
        
        logger.info(f"Cache clear test: {cache_info_before['cached_sentences']} -> {cache_info_after['cached_sentences']}")
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate_calculation(self, cached_chunker):
        """Test that cache hit rate is calculated correctly"""
        # Use same text multiple times to ensure high hit rate
        text = "Repeated text for hit rate testing."
        
        # First run - all misses
        await cached_chunker.chunk_text(text, "hit_rate_1")
        
        # Subsequent runs - should be hits
        for i in range(3):
            await cached_chunker.chunk_text(text, f"hit_rate_{i+2}")
        
        cache_info = cached_chunker.get_cache_info()
        stats = cache_info['stats']
        
        # Verify hit rate calculation
        total_requests = stats['total_requests']
        hit_rate = stats['hit_rate']
        
        assert total_requests > 0, "Should have made cache requests"
        assert 0 <= hit_rate <= 1, "Hit rate should be between 0 and 1"
        
        # With repeated text, hit rate should be relatively high
        logger.info(f"Hit rate test: {hit_rate:.2%} ({stats['total_cache_hits']}/{total_requests})")
    
    @pytest.mark.asyncio
    async def test_precompute_embeddings(self, cached_chunker):
        """Test the precompute embeddings functionality"""
        # Prepare test documents
        test_documents = [
            {"content": "第一个测试文档内容。包含中文句子。", "id": "doc1"},
            {"content": "Second test document content. Contains English sentences.", "id": "doc2"},
            {"content": "Troisième document de test. Contient des phrases françaises.", "id": "doc3"},
        ]
        
        # Get initial cache state
        initial_cache_info = cached_chunker.get_cache_info()
        initial_sentences = initial_cache_info['cached_sentences']
        
        # Precompute embeddings
        precompute_stats = await cached_chunker.precompute_sentence_embeddings(test_documents)
        
        # Verify precompute results
        assert 'total_documents' in precompute_stats
        assert 'total_sentences' in precompute_stats
        assert 'cache_hits' in precompute_stats
        assert 'cache_misses' in precompute_stats
        assert 'hit_rate' in precompute_stats
        
        assert precompute_stats['total_documents'] == len(test_documents)
        assert precompute_stats['total_sentences'] > 0
        
        # Verify cache was populated
        final_cache_info = cached_chunker.get_cache_info()
        final_sentences = final_cache_info['cached_sentences']
        
        assert final_sentences > initial_sentences, "Cache should have more sentences after precomputation"
        
        logger.info(f"Precompute test: {precompute_stats}")
        logger.info(f"Cache sentences: {initial_sentences} -> {final_sentences}")
    
    @pytest.mark.asyncio
    async def test_cache_with_different_parameters(self, temp_cache_dir, mock_embedding_service, mock_tokenizer):
        """Test that cache works correctly with different chunking parameters"""
        from evaluation.utils.config_loader import ConfigLoader
        
        # Load base config
        config_loader = ConfigLoader("config")
        base_config = config_loader.load_chunking_config("chunking_config.toml")
        
        # Create modified config with different similarity threshold
        import copy
        modified_config = copy.deepcopy(base_config)
        modified_config['semantic_merging']['similarity_threshold'] = 0.9
        
        # Create chunkers with different configs but same cache
        chunker1 = MultiLingualChunker(mock_embedding_service, mock_tokenizer, base_config, temp_cache_dir)
        chunker2 = MultiLingualChunker(mock_embedding_service, mock_tokenizer, modified_config, temp_cache_dir)
        
        text = "Parameter test with this specific sentence content."
        
        # Use both chunkers
        chunks1 = await chunker1.chunk_text(text, "param_test_1")
        chunks2 = await chunker2.chunk_text(text, "param_test_2")
        
        # Both should benefit from shared sentence-level cache
        cache_info_1 = chunker1.get_cache_info()
        cache_info_2 = chunker2.get_cache_info()
        
        # Cache should be shared (same cache file)
        assert cache_info_1['cache_file'] == cache_info_2['cache_file'], "Should share cache file"
        
        # Both should have cache hits (shared sentence embeddings)
        assert cache_info_1['stats']['total_cache_hits'] > 0, "First chunker should have cache hits"
        assert cache_info_2['stats']['total_cache_hits'] > 0, "Second chunker should have cache hits"
        
        logger.info(f"Parameter test passed with shared caching") 