#!/usr/bin/env python3
"""
Test script for V3 schema data ingestion.
This script tests the basic functionality of the new schema and sync process.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv(dotenv_path="../.env")  # Backend .env
load_dotenv(dotenv_path="../../.env")  # Root .env

from database_v3 import init_db, get_db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_database_connection():
    """Test basic database connection and schema."""
    logger.info("🔍 Testing database connection...")
    
    try:
        await init_db()
        db = get_db()
        
        # Test basic operations
        logger.info("✅ Database initialized successfully")
        
        # Get database stats
        stats = db.get_database_stats()
        logger.info(f"📊 Database stats: {stats}")
        
        # Test notion databases table
        databases = db.get_notion_databases()
        logger.info(f"📚 Found {len(databases)} notion databases")
        
        for db_record in databases:
            logger.info(f"  - {db_record.get('database_name', 'Unknown')} ({db_record.get('database_id', 'No ID')})")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


async def test_sync_single_database():
    """Test syncing a single database if NOTION_DATABASE_ID is provided."""
    database_id = os.getenv("NOTION_DATABASE_ID")
    
    if not database_id:
        logger.info("⏭️  No NOTION_DATABASE_ID provided, skipping sync test")
        return True
    
    logger.info(f"🔄 Testing sync for database: {database_id}")
    
    try:
        # Import and run the sync
        from sync_databases_v3 import NotionDatabaseSyncerV3, create_single_database_config
        
        config = create_single_database_config(database_id)
        syncer = NotionDatabaseSyncerV3(dry_run=True)  # Use dry run for testing
        
        await syncer.initialize()
        
        result = await syncer.sync_database(config)
        
        if result.get('success'):
            logger.info(f"✅ Sync test completed successfully:")
            logger.info(f"   Pages would be processed: {result.get('pages_processed', 0)}")
            logger.info(f"   Pages would be created: {result.get('pages_created', 0)}")
            logger.info(f"   Pages would be updated: {result.get('pages_updated', 0)}")
            return True
        else:
            logger.error(f"❌ Sync test failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Sync test failed: {e}")
        return False


async def test_vector_search():
    """Test vector search functionality."""
    logger.info("🔍 Testing vector search...")
    
    try:
        db = get_db()
        
        # Create a dummy embedding for testing
        dummy_embedding = [0.1] * 1536  # OpenAI embedding dimension
        
        # Test document search
        doc_results = db.vector_search_documents(
            query_embedding=dummy_embedding,
            match_threshold=0.1,  # Low threshold for testing
            match_count=5
        )
        
        logger.info(f"📄 Document search returned {len(doc_results)} results")
        
        # Test chunk search
        chunk_results = db.vector_search_chunks(
            query_embedding=dummy_embedding,
            match_threshold=0.1,
            match_count=5
        )
        
        logger.info(f"📝 Chunk search returned {len(chunk_results)} results")
        
        # Test hybrid search
        hybrid_results = db.hybrid_search(
            query_embedding=dummy_embedding,
            match_threshold=0.1,
            match_count=5
        )
        
        logger.info(f"🔀 Hybrid search returned {len(hybrid_results)} results")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Vector search test failed: {e}")
        return False


async def test_chat_sessions():
    """Test chat session functionality."""
    logger.info("💬 Testing chat session functionality...")
    
    try:
        db = get_db()
        
        # Test getting recent chat sessions
        recent_sessions = db.get_recent_chat_sessions(limit=5)
        logger.info(f"📋 Found {len(recent_sessions)} recent chat sessions")
        
        for session in recent_sessions:
            logger.info(f"  - {session.get('title', 'Untitled')} "
                       f"({session.get('message_count', 0)} messages)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Chat session test failed: {e}")
        return False


async def run_all_tests():
    """Run all tests."""
    logger.info("🚀 Starting V3 schema ingestion tests...")
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Chat Sessions", test_chat_sessions),
        ("Vector Search", test_vector_search),
        ("Single Database Sync", test_sync_single_database),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running test: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = await test_func()
            results[test_name] = result
            
            if result:
                logger.info(f"✅ {test_name} passed")
            else:
                logger.error(f"❌ {test_name} failed")
                
        except Exception as e:
            logger.error(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("Test Summary")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name:<30} {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! V3 schema is ready for ingestion.")
        return True
    else:
        logger.error("⚠️  Some tests failed. Please check the configuration.")
        return False


def print_usage():
    """Print usage instructions."""
    print("""
🚀 V3 Schema Ingestion Test

This script tests the new V3 schema and ingestion capabilities.

Environment Variables:
  NOTION_ACCESS_TOKEN     - Your Notion integration token (required for sync test)
  NOTION_DATABASE_ID      - Database ID to test sync with (optional)
  NEXT_PUBLIC_SUPABASE_URL - Your Supabase project URL
  NEXT_PUBLIC_SUPABASE_ANON_KEY - Your Supabase anon key

Usage:
  python test_v3_ingestion.py

What this tests:
  1. Database connection to V3 schema
  2. Basic CRUD operations
  3. Vector search functions
  4. Chat session functionality  
  5. Notion database sync (if NOTION_DATABASE_ID provided)

To run a full sync after testing:
  python sync_databases_v3.py --database-id YOUR_DATABASE_ID
""")


async def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print_usage()
        return
    
    success = await run_all_tests()
    
    if success:
        logger.info("\n🎯 Next steps:")
        logger.info("1. Run actual sync: python sync_databases_v3.py --database-id YOUR_DATABASE_ID")
        logger.info("2. Test frontend with new backend")
        logger.info("3. Update API endpoints to use V3 schema")
        sys.exit(0)
    else:
        logger.error("\n🔧 Fix the failing tests before proceeding with ingestion")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())