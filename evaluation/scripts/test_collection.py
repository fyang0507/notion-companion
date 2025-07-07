#!/usr/bin/env python3
"""
Simple test script for the evaluation collection system.
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables from root folder
root_dir = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=root_dir / ".env")

from services.data_collector import DataCollector


async def test_collection():
    """Test the simplified collection system."""
    print("🧪 Testing simplified collection system...")
    
    # Check environment
    notion_token = os.getenv("NOTION_ACCESS_TOKEN")
    if not notion_token:
        print("❌ NOTION_ACCESS_TOKEN not set")
        return False
    
    # Test database ID (you can change this)
    test_database_id = "1519782c4f4a80dc9deff9768446a113"
    
    try:
        # Initialize collector (will load env vars automatically)
        collector = DataCollector(output_dir="test_data")
        
        # Test single database collection
        print(f"📚 Testing collection for database: {test_database_id[:8]}...")
        
        stats = await collector.collect_database(test_database_id, min_content_length=10)
        
        # Print results
        print(f"✅ Collection completed!")
        print(f"   Total documents: {stats.total_documents}")
        print(f"   Successful: {stats.successful}")
        print(f"   Failed: {stats.failed}")
        print(f"   Skipped: {stats.skipped}")
        
        if stats.errors:
            print(f"   Errors: {len(stats.errors)}")
            for error in stats.errors[:3]:
                print(f"     - {error}")
        
        if stats.successful > 0:
            print("✅ Test passed - successfully collected documents")
            return True
        else:
            print("⚠️  Test warning - no documents collected")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def main():
    """Main test runner."""
    success = await test_collection()
    
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 