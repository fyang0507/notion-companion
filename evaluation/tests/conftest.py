"""Shared test fixtures and configuration for evaluation tests."""

import os
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
from typing import Dict, Any, List
from pathlib import Path
import sys
from dotenv import load_dotenv

# Add evaluation root to Python path
evaluation_root = Path(__file__).parent.parent
sys.path.insert(0, str(evaluation_root))

# Load environment variables from root .env file
# This ensures integration tests use the actual environment configuration
root_dir = evaluation_root.parent
load_dotenv(dotenv_path=root_dir / ".env")

# Test environment setup
os.environ["TESTING"] = "true"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service for testing."""
    mock_service = Mock()
    
    # Mock embeddings generation
    async def mock_generate_embeddings(texts: List[str]) -> List[List[float]]:
        """Generate deterministic embeddings for testing."""
        embeddings = []
        for i, text in enumerate(texts):
            # Create deterministic embedding based on text hash
            text_hash = hash(text.lower().strip())
            embedding = [float((text_hash + j) % 100) / 100.0 for j in range(1536)]
            embeddings.append(embedding)
        return embeddings
    
    mock_service.generate_embeddings = mock_generate_embeddings
    mock_service.dimension = 1536
    
    return mock_service


@pytest.fixture
def mock_tokenizer():
    """Mock tokenizer for testing."""
    mock_tokenizer = Mock()
    
    def mock_encode(text: str) -> List[int]:
        """Simple tokenization approximation for testing."""
        # Rough approximation: 1 token per 4 characters for English
        # Chinese characters are typically 1 token each
        token_count = 0
        for char in text:
            if '\u4e00' <= char <= '\u9fff':  # Chinese character
                token_count += 1
            elif char.isalnum():
                token_count += 0.25  # English words
            elif char.isspace():
                continue
            else:
                token_count += 0.1  # Punctuation
        
        return list(range(int(token_count)))
    
    mock_tokenizer.encode = mock_encode
    return mock_tokenizer


@pytest.fixture
def mock_notion_client():
    """Mock Notion client for testing."""
    mock_client = Mock()
    
    # Mock database pages response
    mock_client.databases.query.return_value = {
        "results": [
            {
                "id": "test-page-1",
                "properties": {
                    "Name": {"title": [{"text": {"content": "Test Document 1"}}]},
                    "Content": {"rich_text": [{"text": {"content": "This is test content for document 1."}}]}
                },
                "last_edited_time": "2023-01-01T00:00:00.000Z",
                "created_time": "2023-01-01T00:00:00.000Z"
            },
            {
                "id": "test-page-2", 
                "properties": {
                    "Name": {"title": [{"text": {"content": "Test Document 2"}}]},
                    "Content": {"rich_text": [{"text": {"content": "This is test content for document 2."}}]}
                },
                "last_edited_time": "2023-01-02T00:00:00.000Z",
                "created_time": "2023-01-02T00:00:00.000Z"
            }
        ],
        "has_more": False
    }
    
    # Mock page blocks response
    mock_client.blocks.children.list.return_value = {
        "results": [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"text": {"content": "This is a paragraph of test content."}}]
                }
            }
        ],
        "has_more": False
    }
    
    return mock_client


@pytest.fixture
def sample_test_texts() -> Dict[str, str]:
    """Sample texts for testing various scenarios."""
    return {
        'chinese_quotes': '''
        他说："这是一个很好的例子。"然后他继续解释说："我们需要理解这个概念。"
        '''.strip(),
        
        'english_abbreviations': '''
        Dr. Smith works at the University. He has a Ph.D. from MIT and is currently researching A.I. 
        The meeting is at 3:00 p.m. in room 101.
        '''.strip(),
        
        'french_guillemets': '''
        Le professeur a dit : « C'est un exemple parfait. » Il a continué : « Nous devons comprendre ce concept. »
        '''.strip(),
        
        'mixed_language': '''
        The research paper titled "人工智能的发展" discusses various topics. 
        Dr. Zhang explained: "This is important research." 
        En français, nous disons « C'est très intéressant. »
        '''.strip(),
        
        'complex_quotes': '''
        他在论文中写道："人工智能的发展需要考虑多个因素。"接着，他引用了另一位学者的观点："这个领域还有很多挑战。"
        The author stated: "AI development requires multiple considerations." 
        Le chercheur a noté : « Il y a encore beaucoup de défis dans ce domaine. »
        '''.strip(),
    }


@pytest.fixture
def sample_documents() -> List[Dict[str, Any]]:
    """Sample document data for testing."""
    return [
        {
            "id": "doc-1",
            "title": "Machine Learning Basics",
            "content": "Machine learning is a subset of artificial intelligence. It focuses on algorithms that can learn from data.",
            "database_id": "test-db-1",
            "page_id": "page-1",
            "last_edited": "2023-01-01T00:00:00.000Z"
        },
        {
            "id": "doc-2",
            "title": "Deep Learning Applications", 
            "content": "Deep learning has revolutionized computer vision and natural language processing.",
            "database_id": "test-db-1",
            "page_id": "page-2",
            "last_edited": "2023-01-02T00:00:00.000Z"
        },
        {
            "id": "doc-3",
            "title": "人工智能发展",
            "content": "人工智能技术在近年来发展迅速，特别是在机器学习和深度学习领域取得了重大突破。",
            "database_id": "test-db-2", 
            "page_id": "page-3",
            "last_edited": "2023-01-03T00:00:00.000Z"
        }
    ]


@pytest.fixture
def chunking_config() -> Dict[str, Any]:
    """Default chunking configuration for testing."""
    return {
        "chunking": {
            "chinese_punctuation": ["。", "！", "？", "；", "......"],
            "western_punctuation": [".", "!", "?", "..."],
            "quote_pairs": [
                ["\"", "\""],        # ASCII double quotes (ambiguous)
                ["'", "'"],          # ASCII single quotes (ambiguous)
                ["\u201c", "\u201d"],  # Curved double quotes " " (unambiguous)
                ["\u2018", "\u2019"],  # Curved single quotes ' ' (unambiguous)
                ["\u300c", "\u300d"],  # Chinese corner brackets 「 」 (unambiguous)
                ["\u300e", "\u300f"],  # Chinese double corner brackets 『 』 (unambiguous)
                ["\u00ab", "\u00bb"]   # French guillemets « » (unambiguous)
            ],
            "quotation_marks": [
                "\"", "'",           # ASCII quotes
                "\u201c", "\u201d",  # Curved double quotes " "
                "\u2018", "\u2019",  # Curved single quotes ' '
                "\u300c", "\u300d",  # Chinese corner brackets 「 」
                "\u300e", "\u300f",  # Chinese double corner brackets 『 』
                "\u00ab", "\u00bb"   # French guillemets « »
            ],
            "english_abbreviations": [
                "Mr", "Mrs", "Ms", "Dr", "Prof", "Sr", "Jr",
                "Ph\\.D", "B\\.A", "M\\.A", "B\\.S", "M\\.S", "B\\.Sc", "M\\.Sc",
                "Inc", "Ltd", "Corp", "Co", "LLC",
                "etc", "vs", "i\\.e", "e\\.g", "cf", "ibid",
                "a\\.m", "p\\.m", "AM", "PM",
                "cm", "km", "kg", "lb", "oz", "ft", "in"
            ],
            "french_abbreviations": [
                "M", "Mme", "Mlle", "Dr", "Prof",
                "c\\.-à-d", "p\\. ex", "cf", "etc"
            ]
        },
        "semantic_merging": {
            "similarity_threshold": 0.85,
            "max_merge_distance": 3,
            "max_chunk_size": 500
        },
        "embeddings": {
            "model": "text-embedding-3-small",
            "batch_size": 32,
            "enable_caching": True
        },
        "performance": {
            "debug_logging": False,
            "enable_metrics": True,
            "max_text_length": 100000
        }
    }


@pytest.fixture
def temp_output_dir(tmp_path):
    """Temporary directory for test outputs."""
    output_dir = tmp_path / "test_output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def sample_evaluation_config() -> Dict[str, Any]:
    """Sample configuration for evaluation tests."""
    return {
        "collection": {
            "batch_size": 10,
            "max_retries": 3,
            "retry_delay": 1.0,
            "min_content_length": 10
        },
        "chunking": {
            "max_tokens_per_chunk": 500,
            "overlap_tokens": 50,
            "enable_semantic_merging": True
        },
        "output": {
            "save_raw_data": True,
            "save_processed_chunks": True,
            "save_embeddings": False
        }
    } 