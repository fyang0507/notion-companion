#!/usr/bin/env python3
"""
Test script to verify the multilingual chunking functionality.
This is a simplified test to ensure everything works before running the full chunking script.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.multilingual_chunker import MultiLingualChunker
from utils.config_loader import ConfigLoader
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


async def test_chunking():
    """Test the chunking functionality with sample Chinese text"""
    
    # Sample Chinese text from the JSON data
    sample_text = """
    # 2025年可能是一个重要的转折点
    
    ## 一、转型、周期性压力
    
    2018年前后，中国经济增长模式逐步摆脱依靠债务基建和房地产驱动的增长形式，转向依靠技术进步和产业升级。
    经济转型过程中有些行业兴起，有些行业衰落，总量层面经济增速放慢可以理解可以想像，属于转型过程中的成长的烦恼。
    
    在此之后，经济增速下滑更多来自于周期的扰动而不是转型的代价。
    """
    
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
        
        # Test chunking
        chunks = await chunker.chunk_text(sample_text, "test_doc")
        
        logger.info(f"Generated {len(chunks)} chunks:")
        for i, chunk in enumerate(chunks):
            logger.info(f"Chunk {i + 1}:")
            logger.info(f"  - Content: {chunk.content[:100]}...")
            logger.info(f"  - Sentences: {chunk.start_sentence} to {chunk.end_sentence}")
            logger.info(f"  - Has embedding: {chunk.embedding is not None}")
            logger.info(f"  - Token count: {len(tokenizer.encode(chunk.content))}")
            logger.info("")
        
        logger.info("✅ Test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_chunking())
    sys.exit(0 if success else 1) 