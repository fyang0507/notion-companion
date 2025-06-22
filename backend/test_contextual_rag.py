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

from services.content_type_detector import ContentTypeDetector
from services.contextual_chunker import ContextualChunker
from services.openai_service import get_openai_service
from database import get_db, init_db

async def test_content_type_detection():
    """Test content type detection."""
    print("🔍 Testing Content Type Detection...")
    
    detector = ContentTypeDetector()
    
    # Test cases
    test_cases = [
        {
            'title': 'Reading Notes: The Lean Startup',
            'content': '- Key takeaway: Build-Measure-Learn cycle\n- Important quote: "The only way to win is to learn faster than anyone else"\n- Action items: Apply MVP approach to our product',
            'expected': 'reading_notes'
        },
        {
            'title': 'Machine Learning in Healthcare: A Comprehensive Review',
            'content': '# Introduction\nMachine learning has revolutionized healthcare...\n\n# Methodology\nWe conducted a systematic review...\n\n# Results\nOur findings indicate...\n\n# Conclusion\nML shows promise...',
            'expected': 'article'
        },
        {
            'title': 'API Documentation',
            'content': '# Setup Guide\n\n1. Install dependencies\n2. Configure environment\n\n```bash\nnpm install\n```\n\n## Authentication\nUse Bearer tokens...',
            'expected': 'documentation'
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        detected = detector.detect_content_type(case['title'], case['content'], {})
        status = "✅" if detected == case['expected'] else "❌"
        print(f"  Test {i}: {status} '{case['title']}' -> {detected} (expected: {case['expected']})")
    
    print()

async def test_contextual_chunking():
    """Test contextual chunking with sample content."""
    print("🧩 Testing Contextual Chunking...")
    
    try:
        # Initialize services
        openai_service = get_openai_service()
        chunker = ContextualChunker(openai_service, max_tokens=500, overlap_tokens=50)
        
        # Sample reading notes content
        sample_content = """
# Key Insights from "The Lean Startup"

## Build-Measure-Learn Cycle
- The fundamental principle is to build a minimum viable product (MVP)
- Measure how customers respond to the product
- Learn from the data and iterate quickly

## Validated Learning
- Traditional business planning is often based on assumptions
- Startups should focus on validated learning through experiments
- Each experiment should test a specific hypothesis

## Innovation Accounting
- Traditional accounting doesn't work for startups
- Need to measure progress differently
- Focus on learning milestones rather than traditional metrics

## Key Quotes
> "The only way to win is to learn faster than anyone else"

> "We must learn what customers really want, not what they say they want"

## Action Items
- Implement build-measure-learn cycle in our product development
- Define clear hypotheses for each feature
- Set up metrics to track validated learning
        """
        
        # Test chunking
        chunks = await chunker.chunk_with_context(
            content=sample_content,
            title="Reading Notes: The Lean Startup",
            page_data={}
        )
        
        print(f"  Generated {len(chunks)} contextual chunks")
        
        # Display first chunk details
        if chunks:
            first_chunk = chunks[0]
            print(f"  First chunk:")
            print(f"    Content Type: {first_chunk.get('content_type', 'unknown')}")
            print(f"    Section: {first_chunk.get('section_title', 'N/A')}")
            print(f"    Context: {first_chunk.get('chunk_context', 'N/A')[:100]}...")
            print(f"    Summary: {first_chunk.get('chunk_summary', 'N/A')[:100]}...")
            print(f"    Has contextual content: {'contextual_content' in first_chunk}")
            print(f"    Position metadata: {first_chunk.get('chunk_position', {})}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error in contextual chunking: {str(e)}")
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
    
    # Test 1: Content Type Detection
    await test_content_type_detection()
    
    # Test 2: Contextual Chunking (requires OpenAI API)
    print("Note: Contextual chunking test requires OpenAI API key")
    if os.getenv('OPENAI_API_KEY'):
        await test_contextual_chunking()
    else:
        print("  ⚠️  Skipping contextual chunking test (no OPENAI_API_KEY)")
        print()
    
    # Test 3: Database Functions (requires Supabase)
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