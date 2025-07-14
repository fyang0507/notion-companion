#!/usr/bin/env python3
"""
Test script for Enhanced RAG with Contextual Retrieval

This script tests the new contextual chunking and search functionality
without starting the full backend server.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from services.contextual_chunker import ContextualChunker
from services.openai_service import get_openai_service
from database import get_db, init_db

async def test_contextual_chunking():
    """Test contextual chunking with real content."""
    print("🧩 Testing Contextual Chunking...")
    
    try:
        # Initialize services
        openai_service = get_openai_service()
        chunker = ContextualChunker(openai_service, max_tokens=500, overlap_tokens=50)
        
        # Test content
        test_title = "Machine Learning in Healthcare"
        test_content = """
# Introduction

Machine learning (ML) has emerged as a transformative technology in healthcare, offering unprecedented opportunities to improve patient outcomes, reduce costs, and enhance operational efficiency. This comprehensive review examines the current state of ML applications in healthcare.

# Background and Motivation

The healthcare industry generates vast amounts of data daily, including electronic health records, medical imaging, genomic sequences, and sensor data from wearable devices. Traditional analytical methods often fall short in extracting meaningful insights from these complex, high-dimensional datasets.

# Key Applications

## Diagnostic Imaging
Machine learning algorithms, particularly deep learning models, have shown remarkable success in medical image analysis. Convolutional neural networks (CNNs) can detect diabetic retinopathy in retinal photographs with accuracy matching or exceeding that of human specialists.

## Drug Discovery
ML accelerates drug discovery by predicting molecular behavior, identifying potential drug targets, and optimizing clinical trial design. This has the potential to reduce the typical 10-15 year drug development timeline.

## Personalized Medicine
By analyzing patient-specific data including genetics, lifestyle, and medical history, ML enables personalized treatment recommendations that can improve therapeutic outcomes while minimizing adverse effects.

# Challenges and Limitations

Despite its promise, ML in healthcare faces significant challenges including data privacy concerns, regulatory hurdles, interpretability requirements, and the need for robust validation in clinical settings.

# Future Directions

The future of ML in healthcare lies in federated learning approaches that preserve privacy while enabling collaborative model training, explainable AI that provides clinically interpretable insights, and real-time decision support systems integrated into clinical workflows.

# Conclusion

Machine learning represents a paradigm shift in healthcare, offering tools to unlock insights from complex medical data. While challenges remain, continued research and development promise to deliver increasingly sophisticated and clinically valuable applications.
"""
        
        # Test chunking
        chunks = await chunker.chunk_with_context(test_content, test_title)
        
        print(f"  ✅ Generated {len(chunks)} chunks")
        
        # Display sample chunks
        for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
            print(f"\n  Chunk {i+1}:")
            print(f"    Content: {chunk['content'][:100]}...")
            print(f"    Context: {chunk.get('chunk_context', 'N/A')}")
            print(f"    Summary: {chunk.get('chunk_summary', 'N/A')}")
            
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return False
    
    print()

async def test_database_functions():
    """Test the new database functions."""
    print("🗄️  Testing Database Functions...")
    
    try:
        # Initialize database
        await init_db()
        db = get_db()
        
        # Test contextual chunk search function
        # Note: This will return empty results if no data is in the database
        test_embedding = [0.1] * 1536  # Dummy embedding
        
        response = db.client.rpc('match_contextual_chunks', {
            'query_embedding': test_embedding,
            'database_filter': None,
            'match_threshold': 0.5,
            'match_count': 5
        }).execute()
        
        print(f"  ✅ match_contextual_chunks function works (returned {len(response.data)} results)")
        
        # Test chunk context function
        # This will return null for non-existent chunk ID, which is expected
        test_chunk_id = "00000000-0000-0000-0000-000000000000"
        response = db.client.rpc('get_chunk_with_context', {
            'chunk_id_param': test_chunk_id,
            'include_adjacent': True
        }).execute()
        
        print(f"  ✅ get_chunk_with_context function works (returned: {response.data is not None})")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error testing database functions: {str(e)}")
        return False
    
    print()

async def main():
    """Run all tests."""
    print("🚀 Testing Enhanced RAG with Contextual Retrieval\n")
    
    # Test 1: Contextual Chunking (requires OpenAI API)
    print("Note: Contextual chunking test requires OpenAI API key")
    if os.getenv('OPENAI_API_KEY'):
        await test_contextual_chunking()
    else:
        print("  ⚠️  Skipping contextual chunking test (no OPENAI_API_KEY)")
        print()
    
    # Test 2: Database Functions (requires Supabase)
    print("Note: Database test requires Supabase credentials")
    if os.getenv('NEXT_PUBLIC_SUPABASE_URL') and os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY'):
        await test_database_functions()
    else:
        print("  ⚠️  Skipping database test (no Supabase credentials)")
        print()
    
    print("✨ Testing complete!")
    print()
    print("Next steps:")
    print("1. Apply the updated schema.sql to your Supabase database")
    print("2. Run document sync to test the full pipeline: `cd backend && .venv/bin/python scripts/sync_databases.py`")
    print("3. Test the enhanced search API endpoints")

if __name__ == "__main__":
    asyncio.run(main())