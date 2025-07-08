#!/usr/bin/env python3
"""
Script to view a sample of the generated chunks without the large embeddings.
"""

import json
import sys
from pathlib import Path

def view_chunks(chunks_file):
    """View a sample of chunks without the embeddings"""
    
    try:
        with open(chunks_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        metadata = data.get('metadata', {})
        chunks = data.get('chunks', [])
        
        print(f"📊 Chunks Metadata:")
        print(f"   Total chunks: {metadata.get('total_chunks', 0)}")
        print(f"   Created at: {metadata.get('created_at', 'N/A')}")
        print(f"   Actual chunks loaded: {len(chunks)}")
        print()
        
        # Show first few chunks
        print("📄 Sample Chunks (first 3):")
        for i, chunk in enumerate(chunks[:3]):
            print(f"\n--- Chunk {i + 1} ---")
            print(f"Document ID: {chunk.get('document_id', 'N/A')}")
            print(f"Document Title: {chunk.get('document_title', 'N/A')[:100]}...")
            print(f"Chunk ID: {chunk.get('chunk_id', 'N/A')}")
            print(f"Sentences: {chunk.get('start_sentence', 'N/A')} to {chunk.get('end_sentence', 'N/A')}")
            print(f"Token count: {chunk.get('token_count', 'N/A')}")
            print(f"Has embedding: {chunk.get('embedding') is not None}")
            print(f"Embedding size: {len(chunk.get('embedding', [])) if chunk.get('embedding') else 0}")
            print(f"Content: {chunk.get('content', 'N/A')[:200]}...")
            print(f"Context before: {chunk.get('context_before', 'N/A')[:100]}...")
            print(f"Context after: {chunk.get('context_after', 'N/A')[:100]}...")
        
        # Show stats by document
        doc_stats = {}
        for chunk in chunks:
            doc_id = chunk.get('document_id', 'unknown')
            if doc_id not in doc_stats:
                doc_stats[doc_id] = {
                    'count': 0,
                    'total_tokens': 0,
                    'title': chunk.get('document_title', 'N/A')
                }
            doc_stats[doc_id]['count'] += 1
            doc_stats[doc_id]['total_tokens'] += chunk.get('token_count', 0)
        
        print(f"\n📈 Statistics by Document:")
        for doc_id, stats in doc_stats.items():
            avg_tokens = stats['total_tokens'] / stats['count'] if stats['count'] > 0 else 0
            print(f"   {stats['title'][:60]}...")
            print(f"      Document ID: {doc_id}")
            print(f"      Chunks: {stats['count']}")
            print(f"      Total tokens: {stats['total_tokens']}")
            print(f"      Avg tokens/chunk: {avg_tokens:.1f}")
            print()
        
    except Exception as e:
        print(f"Error viewing chunks: {e}")
        return False
    
    return True

if __name__ == "__main__":
    chunks_file = "data/processed/768446a113_20250707_135150_chunks.json"
    
    if len(sys.argv) > 1:
        chunks_file = sys.argv[1]
    
    if not Path(chunks_file).exists():
        print(f"Chunks file not found: {chunks_file}")
        sys.exit(1)
    
    print(f"📋 Viewing chunks from: {chunks_file}")
    print("=" * 80)
    
    success = view_chunks(chunks_file)
    sys.exit(0 if success else 1) 