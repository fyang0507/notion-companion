#!/usr/bin/env python3
"""
Document Chunking Script

This script converts downloaded documents into chunks using the multilingual chunker.
It processes JSON files in the evaluation/data directory and saves the chunked results.
"""

import json
import logging
import asyncio
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import tiktoken
from datetime import datetime

# Add parent directories to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.multilingual_chunker import MultiLingualChunker, ChunkResult
from utils.config_loader import ConfigLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chunk_documents.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """Chunked document result for serialization"""
    document_id: str
    document_title: str
    chunk_id: str
    content: str
    start_sentence: int
    end_sentence: int
    embedding: Optional[List[float]]
    context_before: str
    context_after: str
    token_count: int
    created_at: str


class MockEmbeddingService:
    """Mock embedding service for testing purposes"""
    
    def __init__(self, model_name: str = "text-embedding-3-small"):
        self.model_name = model_name
        logger.info(f"Initialized MockEmbeddingService with model: {model_name}")
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings (random vectors) for the given texts"""
        import random
        embeddings = []
        for text in texts:
            # Generate a mock embedding vector of dimension 1536 (OpenAI standard)
            embedding = [random.random() for _ in range(1536)]
            embeddings.append(embedding)
        
        logger.debug(f"Generated {len(embeddings)} mock embeddings")
        return embeddings


class SimpleTokenizer:
    """Simple tokenizer wrapper using tiktoken"""
    
    def __init__(self, model_name: str = "cl100k_base"):
        try:
            self.tokenizer = tiktoken.get_encoding(model_name)
            logger.info(f"Initialized tokenizer with encoding: {model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize tokenizer: {e}")
            raise
    
    def encode(self, text: str) -> List[int]:
        """Encode text to tokens"""
        return self.tokenizer.encode(text)
    
    def decode(self, tokens: List[int]) -> str:
        """Decode tokens to text"""
        return self.tokenizer.decode(tokens)


class DocumentChunker:
    """Main document chunking service"""
    
    def __init__(self, config_path: str = "config/chunking_config.toml"):
        # Parse config path
        config_path = Path(config_path)
        if config_path.is_file():
            config_dir = config_path.parent
            config_file = config_path.name
        else:
            config_dir = config_path
            config_file = "chunking_config.toml"
        
        # Load configuration using ConfigLoader
        config_loader = ConfigLoader(config_dir)
        self.config = config_loader.load_chunking_config(config_file)
        
        # Initialize services
        self.embedding_service = MockEmbeddingService()
        self.tokenizer = SimpleTokenizer()
        
        # Initialize multilingual chunker
        self.chunker = MultiLingualChunker(
            self.embedding_service,
            self.tokenizer,
            self.config
        )
        
        logger.info("DocumentChunker initialized successfully")
    
    async def load_documents(self, json_file_path: str) -> List[Dict[str, Any]]:
        """Load documents from JSON file"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            documents = data.get('documents', [])
            logger.info(f"Loaded {len(documents)} documents from {json_file_path}")
            return documents
        
        except Exception as e:
            logger.error(f"Error loading documents from {json_file_path}: {e}")
            raise
    
    async def chunk_document(self, document: Dict[str, Any]) -> List[DocumentChunk]:
        """Chunk a single document"""
        try:
            doc_id = document.get('id', '')
            title = document.get('title', '')
            content = document.get('content', '')
            
            if not content.strip():
                logger.warning(f"Empty content for document {doc_id}")
                return []
            
            logger.info(f"Chunking document: {title[:50]}...")
            
            # Use the multilingual chunker
            chunks = await self.chunker.chunk_text(content, doc_id)
            
            # Convert to serializable format
            result_chunks = []
            for i, chunk in enumerate(chunks):
                # Count tokens
                token_count = len(self.tokenizer.encode(chunk.content))
                
                chunk_result = DocumentChunk(
                    document_id=doc_id,
                    document_title=title,
                    chunk_id=f"{doc_id}_chunk_{i}",
                    content=chunk.content,
                    start_sentence=chunk.start_sentence,
                    end_sentence=chunk.end_sentence,
                    embedding=chunk.embedding,
                    context_before=chunk.context_before,
                    context_after=chunk.context_after,
                    token_count=token_count,
                    created_at=datetime.now().isoformat()
                )
                result_chunks.append(chunk_result)
            
            logger.info(f"Created {len(result_chunks)} chunks for document {doc_id}")
            return result_chunks
        
        except Exception as e:
            logger.error(f"Error chunking document {document.get('id', 'unknown')}: {e}")
            raise
    
    async def process_documents(self, json_file_path: str) -> List[DocumentChunk]:
        """Process all documents in a JSON file"""
        documents = await self.load_documents(json_file_path)
        all_chunks = []
        
        for doc in documents:
            try:
                chunks = await self.chunk_document(doc)
                all_chunks.extend(chunks)
            except Exception as e:
                logger.error(f"Failed to process document {doc.get('id', 'unknown')}: {e}")
                continue
        
        return all_chunks
    
    def save_chunks(self, chunks: List[DocumentChunk], output_path: str):
        """Save chunks to JSON file"""
        try:
            # Convert to dictionary format for JSON serialization
            chunks_data = {
                'metadata': {
                    'total_chunks': len(chunks),
                    'created_at': datetime.now().isoformat(),
                    'config': self.config
                },
                'chunks': [asdict(chunk) for chunk in chunks]
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(chunks_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved {len(chunks)} chunks to {output_path}")
        
        except Exception as e:
            logger.error(f"Error saving chunks to {output_path}: {e}")
            raise


async def main():
    """Main function to run the document chunking process"""
    try:
        # Initialize chunker
        chunker = DocumentChunker()
        
        # Find all JSON files in the data directory
        data_dir = Path("data")
        json_files = list(data_dir.glob("*.json"))
        
        if not json_files:
            logger.error("No JSON files found in evaluation/data directory")
            return
        
        # Process each JSON file
        for json_file in json_files:
            logger.info(f"Processing {json_file}")
            
            # Process documents
            chunks = await chunker.process_documents(str(json_file))
            
            if not chunks:
                logger.warning(f"No chunks generated for {json_file}")
                continue
            
            # Generate output filename
            output_file = data_dir / "processed" / f"{json_file.stem}_chunks.json"
            output_file.parent.mkdir(exist_ok=True)
            
            # Save chunks
            chunker.save_chunks(chunks, str(output_file))
            
            # Print summary
            total_tokens = sum(chunk.token_count for chunk in chunks)
            logger.info(f"Summary for {json_file.name}:")
            logger.info(f"  - Total chunks: {len(chunks)}")
            logger.info(f"  - Total tokens: {total_tokens}")
            logger.info(f"  - Average tokens per chunk: {total_tokens / len(chunks):.1f}")
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main()) 