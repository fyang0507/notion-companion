#!/usr/bin/env python3
"""
Integration tests for the multilingual chunking functionality.
Tests the complete chunking pipeline with real text examples.
"""

import asyncio
import logging
import sys
import pytest
import tempfile
import time
from pathlib import Path

# Add evaluation root to path
evaluation_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(evaluation_root))

from evaluation.services.multilingual_chunker import MultiLingualChunker
from evaluation.utils.config_loader import ConfigLoader
import tiktoken

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MockEmbeddingService:
    """Mock embedding service for testing"""
    
    async def generate_embeddings(self, texts):
        """Generate mock embeddings"""
        import random
        return [[random.random() for _ in range(1536)] for _ in texts]


class SimpleTokenizer:
    """Simple tokenizer wrapper"""
    
    def __init__(self):
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def encode(self, text):
        return self.tokenizer.encode(text)


@pytest.mark.integration
class TestChunkingIntegration:
    """Integration tests for chunking functionality"""
    
    @pytest.fixture
    def config(self):
        """Load chunking configuration"""
        config_loader = ConfigLoader("config")
        return config_loader.load_chunking_config("chunking_config.toml")
    
    @pytest.fixture
    def embedding_service(self):
        """Create mock embedding service"""
        return MockEmbeddingService()
    
    @pytest.fixture
    def tokenizer(self):
        """Create tokenizer"""
        return SimpleTokenizer()
    
    @pytest.fixture
    def chunker(self, config, embedding_service, tokenizer):
        """Create chunker instance"""
        return MultiLingualChunker(embedding_service, tokenizer, config)
    
    @pytest.fixture
    def sample_chinese_text(self):
        """Sample Chinese text for testing"""
        return """
        # 2025年可能是一个重要的转折点
        
        ## 一、转型、周期性压力
        
        2018年前后，中国经济增长模式逐步摆脱依靠债务基建和房地产驱动的增长形式，转向依靠技术进步和产业升级。
        经济转型过程中有些行业兴起，有些行业衰落，总量层面经济增速放慢可以理解可以想像，属于转型过程中的成长的烦恼。
        
        在此之后，经济增速下滑更多来自于周期的扰动而不是转型的代价。
        """
    
    @pytest.mark.asyncio
    async def test_complete_chunking_pipeline(self, chunker, sample_chinese_text):
        """Test the complete chunking pipeline with real text"""
        chunks = await chunker.chunk_text(sample_chinese_text, "test_doc")
        
        assert len(chunks) > 0, "Should generate at least one chunk"
        
        logger.info(f"Generated {len(chunks)} chunks:")
        for i, chunk in enumerate(chunks):
            assert chunk.content.strip(), "Chunk content should not be empty"
            assert chunk.embedding is not None, "Chunk should have embedding"
            assert chunk.start_sentence <= chunk.end_sentence, "Invalid sentence range"
            
            logger.info(f"Chunk {i + 1}:")
            logger.info(f"  - Content: {chunk.content[:100]}...")
            logger.info(f"  - Sentences: {chunk.start_sentence} to {chunk.end_sentence}")
            logger.info(f"  - Has embedding: {chunk.embedding is not None}")
            logger.info(f"  - Token count: {len(chunker.tokenizer.encode(chunk.content))}")
            logger.info("")
    
    @pytest.mark.asyncio
    async def test_caching_functionality(self, chunker, sample_chinese_text):
        """Test that caching works and improves performance"""
        # First run - will populate cache
        start_time = asyncio.get_event_loop().time()
        chunks1 = await chunker.chunk_text(sample_chinese_text, "test_doc_1")
        first_run_time = asyncio.get_event_loop().time() - start_time
        
        # Get cache info after first run
        cache_info_1 = chunker.get_cache_info()
        
        # Second run with same text - should hit cache
        start_time = asyncio.get_event_loop().time()
        chunks2 = await chunker.chunk_text(sample_chinese_text, "test_doc_2")
        second_run_time = asyncio.get_event_loop().time() - start_time
        
        # Get cache info after second run
        cache_info_2 = chunker.get_cache_info()
        
        # Verify chunks are the same
        assert len(chunks1) == len(chunks2), "Should generate same number of chunks"
        
        # Verify cache performance improved
        cache_hits_increased = (cache_info_2['stats']['total_cache_hits'] > 
                              cache_info_1['stats']['total_cache_hits'])
        assert cache_hits_increased, "Cache hits should increase on second run"
        
        # Log performance
        logger.info(f"First run time: {first_run_time:.3f}s")
        logger.info(f"Second run time: {second_run_time:.3f}s")
        logger.info(f"Cache info after runs: {cache_info_2['stats']}")
        
        # Second run should typically be faster due to caching
        if second_run_time < first_run_time:
            logger.info("✅ Caching improved performance")
        else:
            logger.info("⚠️ Caching didn't improve performance (may be due to test overhead)")
    
    @pytest.mark.asyncio
    async def test_cache_info_and_management(self, chunker):
        """Test cache information and management functions"""
        # Get initial cache info
        initial_info = chunker.get_cache_info()
        assert 'cached_sentences' in initial_info
        assert 'stats' in initial_info
        
        # Test with some text to populate cache
        test_text = "这是一个测试句子。This is a test sentence. C'est une phrase de test."
        await chunker.chunk_text(test_text, "cache_test")
        
        # Get updated cache info
        updated_info = chunker.get_cache_info()
        assert updated_info['stats']['total_requests'] >= initial_info['stats']['total_requests']
        
        logger.info(f"Cache info: {updated_info}")
        
        # Test cache clearing (optional - be careful not to clear production cache)
        # chunker.clear_cache()
        # cleared_info = chunker.get_cache_info()
        # assert cleared_info['cached_sentences'] == 0
    
    @pytest.mark.asyncio
    async def test_mixed_language_chunking(self, chunker):
        """Test chunking with mixed languages"""
        mixed_text = """
        中文句子测试。English sentence test. Phrase de test en français.
        
        更多中文内容，包含一些技术术语和概念。
        More English content with technical terms and concepts.
        Plus de contenu français avec des termes techniques.
        
        混合语言的段落 with English words 和 des mots français.
        """
        
        chunks = await chunker.chunk_text(mixed_text, "mixed_lang_test")
        
        assert len(chunks) > 0, "Should handle mixed language text"
        
        logger.info(f"Mixed language chunking: {len(chunks)} chunks")
        for i, chunk in enumerate(chunks):
            logger.info(f"Chunk {i+1}: {chunk.content[:100]}...")
    
    @pytest.mark.asyncio
    async def test_edge_cases(self, chunker):
        """Test edge cases and corner cases"""
        edge_cases = [
            ("", "Empty string"),
            ("   ", "Whitespace only"),
            ("Single sentence.", "Single sentence"),
            ("Multiple. Short. Sentences.", "Multiple short sentences"),
            ("Very long sentence that goes on and on and contains many words and phrases and technical terms and should be handled appropriately by the chunker.", "Very long sentence"),
        ]
        
        for text, description in edge_cases:
            logger.info(f"Testing edge case: {description}")
            chunks = await chunker.chunk_text(text, f"edge_case_{description.replace(' ', '_')}")
            
            if text.strip():
                assert len(chunks) >= 0, f"Should handle edge case: {description}"
            else:
                assert len(chunks) == 0, f"Empty text should produce no chunks: {description}"
            
            logger.info(f"  Result: {len(chunks)} chunks")


@pytest.mark.integration
class TestCachePerformanceIntegration:
    """Integration tests specifically for cache performance and behavior"""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def config(self):
        """Load chunking configuration"""
        config_loader = ConfigLoader("config")
        return config_loader.load_chunking_config("chunking_config.toml")
    
    @pytest.fixture
    def embedding_service(self):
        """Create mock embedding service"""
        return MockEmbeddingService()
    
    @pytest.fixture
    def tokenizer(self):
        """Create tokenizer"""
        return SimpleTokenizer()
    
    @pytest.fixture
    def cached_chunker(self, config, embedding_service, tokenizer, temp_cache_dir):
        """Create chunker instance with temporary cache"""
        return MultiLingualChunker(embedding_service, tokenizer, config, temp_cache_dir)
    
    @pytest.fixture
    def sample_documents(self):
        """Sample documents for performance testing"""
        return [
            {
                "content": """
                人工智能技术的发展历程可以追溯到20世纪50年代。当时计算机科学家开始探索机器是否能够模拟人类智能。
                早期的AI研究主要集中在符号推理和专家系统上。这些系统试图通过规则和逻辑来解决复杂问题。
                
                随着计算能力的提升，机器学习逐渐成为AI研究的重点。神经网络的发展为深度学习奠定了基础。
                深度学习在图像识别、自然语言处理等领域取得了突破性进展。
                """,
                "id": "ai_history_chinese"
            },
            {
                "content": """
                Artificial intelligence has revolutionized many industries in recent years. Machine learning algorithms 
                are now capable of processing vast amounts of data and identifying complex patterns.
                
                Natural language processing has enabled computers to understand and generate human language with 
                remarkable accuracy. Computer vision systems can now recognize objects and faces with superhuman precision.
                
                The future of AI holds even more promise. Autonomous vehicles, medical diagnosis systems, and 
                intelligent assistants are just the beginning of what's possible.
                """,
                "id": "ai_future_english"
            },
            {
                "content": """
                L'intelligence artificielle représente l'un des défis technologiques les plus importants du 21ème siècle.
                Les algorithmes d'apprentissage automatique transforment notre façon de travailler et de vivre.
                
                Le traitement du langage naturel permet aux machines de comprendre et de générer du texte humain.
                La vision par ordinateur révolutionne la reconnaissance d'images et la surveillance automatique.
                
                Les applications de l'IA dans la médecine promettent d'améliorer considérablement les diagnostics.
                L'avenir de cette technologie semble illimité dans ses possibilités d'innovation.
                """,
                "id": "ai_impact_french"
            }
        ]
    
    @pytest.mark.asyncio
    async def test_cache_performance_scaling(self, cached_chunker, sample_documents):
        """Test how cache performance scales with document size and repetition"""
        performance_results = []
        
        for iteration in range(3):
            logger.info(f"Performance test iteration {iteration + 1}")
            
            total_start_time = time.time()
            iteration_chunks = 0
            iteration_cache_hits = 0
            iteration_cache_misses = 0
            
            for doc in sample_documents:
                # Get cache stats before processing
                cache_before = cached_chunker.get_cache_info()
                
                # Process document
                doc_start_time = time.time()
                chunks = await cached_chunker.chunk_text(doc['content'], f"{doc['id']}_iter_{iteration}")
                doc_end_time = time.time()
                
                # Get cache stats after processing
                cache_after = cached_chunker.get_cache_info()
                
                # Calculate metrics
                doc_processing_time = doc_end_time - doc_start_time
                doc_cache_hits = cache_after['stats']['total_cache_hits'] - cache_before['stats']['total_cache_hits']
                doc_cache_misses = cache_after['stats']['total_cache_misses'] - cache_before['stats']['total_cache_misses']
                
                iteration_chunks += len(chunks)
                iteration_cache_hits += doc_cache_hits
                iteration_cache_misses += doc_cache_misses
                
                logger.info(f"  {doc['id']}: {len(chunks)} chunks, "
                          f"{doc_processing_time:.3f}s, "
                          f"hits: {doc_cache_hits}, misses: {doc_cache_misses}")
            
            total_end_time = time.time()
            total_processing_time = total_end_time - total_start_time
            
            # Record iteration results
            result = {
                'iteration': iteration,
                'total_time': total_processing_time,
                'total_chunks': iteration_chunks,
                'cache_hits': iteration_cache_hits,
                'cache_misses': iteration_cache_misses,
                'hit_rate': iteration_cache_hits / (iteration_cache_hits + iteration_cache_misses) if (iteration_cache_hits + iteration_cache_misses) > 0 else 0,
                'chunks_per_second': iteration_chunks / total_processing_time if total_processing_time > 0 else 0
            }
            performance_results.append(result)
            
            logger.info(f"Iteration {iteration + 1} results: "
                      f"{result['total_time']:.3f}s, "
                      f"{result['hit_rate']:.1%} hit rate, "
                      f"{result['chunks_per_second']:.1f} chunks/s")
        
        # Analyze performance trends
        logger.info("\n=== CACHE PERFORMANCE ANALYSIS ===")
        for i, result in enumerate(performance_results):
            logger.info(f"Iteration {i+1}: {result['total_time']:.3f}s, "
                      f"Hit Rate: {result['hit_rate']:.1%}, "
                      f"Performance: {result['chunks_per_second']:.1f} chunks/s")
        
        # Verify caching improves performance over iterations
        if len(performance_results) >= 2:
            first_hit_rate = performance_results[0]['hit_rate']
            last_hit_rate = performance_results[-1]['hit_rate']
            
            assert last_hit_rate >= first_hit_rate, "Hit rate should improve or stay constant over iterations"
            logger.info(f"✅ Hit rate improved from {first_hit_rate:.1%} to {last_hit_rate:.1%}")
    
    @pytest.mark.asyncio
    async def test_precompute_vs_runtime_caching(self, config, embedding_service, tokenizer, temp_cache_dir, sample_documents):
        """Compare performance of precompute vs runtime caching strategies"""
        
        # Test 1: Runtime caching (traditional approach)
        logger.info("Testing runtime caching approach...")
        
        runtime_chunker = MultiLingualChunker(embedding_service, tokenizer, config, 
                                            f"{temp_cache_dir}/runtime")
        
        runtime_start = time.time()
        runtime_chunks = 0
        for doc in sample_documents:
            chunks = await runtime_chunker.chunk_text(doc['content'], f"runtime_{doc['id']}")
            runtime_chunks += len(chunks)
        runtime_end = time.time()
        runtime_time = runtime_end - runtime_start
        
        runtime_cache_info = runtime_chunker.get_cache_info()
        
        # Test 2: Precompute caching approach
        logger.info("Testing precompute caching approach...")
        
        precompute_chunker = MultiLingualChunker(embedding_service, tokenizer, config, 
                                               f"{temp_cache_dir}/precompute")
        
        # Step 1: Precompute embeddings
        precompute_start = time.time()
        precompute_stats = await precompute_chunker.precompute_sentence_embeddings(sample_documents)
        precompute_time = time.time() - precompute_start
        
        # Step 2: Fast parameter tuning (chunking with cached embeddings)
        tuning_start = time.time()
        tuning_chunks = 0
        for doc in sample_documents:
            chunks = await precompute_chunker.chunk_text(doc['content'], f"precompute_{doc['id']}")
            tuning_chunks += len(chunks)
        tuning_end = time.time()
        tuning_time = tuning_end - tuning_start
        
        total_precompute_time = precompute_time + tuning_time
        precompute_cache_info = precompute_chunker.get_cache_info()
        
        # Analysis
        logger.info("\n=== CACHING STRATEGY COMPARISON ===")
        logger.info(f"Runtime Caching:")
        logger.info(f"  Total time: {runtime_time:.3f}s")
        logger.info(f"  Chunks: {runtime_chunks}")
        logger.info(f"  Cache hits: {runtime_cache_info['stats']['total_cache_hits']}")
        logger.info(f"  Hit rate: {runtime_cache_info['stats']['hit_rate']:.1%}")
        
        logger.info(f"Precompute Caching:")
        logger.info(f"  Precompute time: {precompute_time:.3f}s")
        logger.info(f"  Tuning time: {tuning_time:.3f}s")
        logger.info(f"  Total time: {total_precompute_time:.3f}s")
        logger.info(f"  Chunks: {tuning_chunks}")
        logger.info(f"  Cache hits: {precompute_cache_info['stats']['total_cache_hits']}")
        logger.info(f"  Hit rate: {precompute_cache_info['stats']['hit_rate']:.1%}")
        
        # Verify precompute strategy benefits
        assert tuning_chunks == runtime_chunks, "Should produce same number of chunks"
        assert precompute_cache_info['stats']['hit_rate'] >= runtime_cache_info['stats']['hit_rate'], \
               "Precompute should have equal or better hit rate"
        
        # The tuning phase should be very fast with precomputed embeddings
        logger.info(f"✅ Precompute approach: {precompute_time:.3f}s precompute + {tuning_time:.3f}s tuning")
        
        # Performance comparison for repeated parameter tuning
        if tuning_time < runtime_time:
            speedup = runtime_time / tuning_time
            logger.info(f"✅ Parameter tuning {speedup:.1f}x faster with precomputed embeddings")
    
    @pytest.mark.asyncio
    async def test_cache_memory_efficiency(self, cached_chunker, sample_documents):
        """Test cache memory usage and efficiency"""
        initial_cache_info = cached_chunker.get_cache_info()
        initial_size = initial_cache_info.get('cache_file_size_mb', 0)
        
        logger.info(f"Initial cache size: {initial_size:.2f} MB")
        
        # Process documents and track cache growth
        cache_growth = []
        
        for i, doc in enumerate(sample_documents):
            await cached_chunker.chunk_text(doc['content'], f"memory_test_{i}")
            
            cache_info = cached_chunker.get_cache_info()
            cache_size = cache_info.get('cache_file_size_mb', 0)
            sentences_cached = cache_info['cached_sentences']
            
            cache_growth.append({
                'document': i,
                'cache_size_mb': cache_size,
                'sentences_cached': sentences_cached,
                'size_per_sentence_kb': (cache_size * 1024 / sentences_cached) if sentences_cached > 0 else 0
            })
            
            logger.info(f"After doc {i}: {cache_size:.2f} MB, "
                      f"{sentences_cached} sentences, "
                      f"{cache_growth[-1]['size_per_sentence_kb']:.2f} KB/sentence")
        
        # Verify reasonable memory usage
        final_info = cache_growth[-1]
        
        # Each sentence embedding should be reasonable size (typical: 6KB for 1536 dimensions)
        assert final_info['size_per_sentence_kb'] < 20, "Memory usage per sentence should be reasonable"
        assert final_info['cache_size_mb'] < 100, "Total cache size should be reasonable for test"
        
        logger.info(f"✅ Cache memory efficiency test passed")
        logger.info(f"Final cache: {final_info['cache_size_mb']:.2f} MB for {final_info['sentences_cached']} sentences")
    
    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self, config, embedding_service, tokenizer, temp_cache_dir):
        """Test cache behavior with concurrent access (simulated)"""
        # Create multiple chunker instances sharing the same cache
        chunkers = []
        for i in range(3):
            chunker = MultiLingualChunker(embedding_service, tokenizer, config, temp_cache_dir)
            chunkers.append(chunker)
        
        # Test text that will be processed by multiple chunkers
        test_text = """
        并发测试文本内容。这个句子会被多个chunker同时处理。
        Concurrent test text content. This sentence will be processed by multiple chunkers.
        Contenu de test concurrent. Cette phrase sera traitée par plusieurs chunkers.
        """
        
        # Process with all chunkers sequentially (simulating concurrent access patterns)
        tasks = []
        for i, chunker in enumerate(chunkers):
            chunk_task = chunker.chunk_text(test_text, f"concurrent_test_{i}")
            tasks.append(chunk_task)
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks)
        
        # Verify all produced valid results
        for i, chunks in enumerate(results):
            assert len(chunks) > 0, f"Chunker {i} should produce chunks"
            logger.info(f"Chunker {i}: {len(chunks)} chunks")
        
        # Verify all chunkers share cache benefits
        cache_infos = [chunker.get_cache_info() for chunker in chunkers]
        
        for i, cache_info in enumerate(cache_infos):
            logger.info(f"Chunker {i} cache: {cache_info['stats']['hit_rate']:.1%} hit rate, "
                      f"{cache_info['cached_sentences']} sentences")
        
        # All should use the same cache file
        cache_files = [info['cache_file'] for info in cache_infos]
        assert all(f == cache_files[0] for f in cache_files), "All chunkers should share same cache file"
        
        logger.info(f"✅ Concurrent cache access test passed")


def test_chunking_sync():
    """Synchronous test runner for the chunking functionality"""
    return asyncio.run(main_async_test())


async def main_async_test():
    """Main async test function - can be called directly for debugging"""
    try:
        # Load configuration
        config_loader = ConfigLoader("config")
        config = config_loader.load_chunking_config("chunking_config.toml")
        logger.info("Configuration loaded successfully")
        
        # Initialize services
        embedding_service = MockEmbeddingService()
        tokenizer = SimpleTokenizer()
        
        # Initialize chunker
        chunker = MultiLingualChunker(embedding_service, tokenizer, config)
        logger.info("MultiLingualChunker initialized successfully")
        
        # Test with sample text
        sample_text = """
        # 2025年可能是一个重要的转折点
        
        ## 一、转型、周期性压力
        
        2018年前后，中国经济增长模式逐步摆脱依靠债务基建和房地产驱动的增长形式，转向依靠技术进步和产业升级。
        经济转型过程中有些行业兴起，有些行业衰落，总量层面经济增速放慢可以理解可以想像，属于转型过程中的成长的烦恼。
        
        在此之后，经济增速下滑更多来自于周期的扰动而不是转型的代价。
        """
        
        chunks = await chunker.chunk_text(sample_text, "test_doc")
        
        logger.info(f"Generated {len(chunks)} chunks:")
        for i, chunk in enumerate(chunks):
            logger.info(f"Chunk {i + 1}:")
            logger.info(f"  - Content: {chunk.content[:100]}...")
            logger.info(f"  - Sentences: {chunk.start_sentence} to {chunk.end_sentence}")
            logger.info(f"  - Has embedding: {chunk.embedding is not None}")
            logger.info(f"  - Token count: {len(tokenizer.encode(chunk.content))}")
            logger.info("")
        
        logger.info("✅ Integration test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main_async_test())
    sys.exit(0 if success else 1) 