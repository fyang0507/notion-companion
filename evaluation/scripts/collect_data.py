#!/usr/bin/env python3
"""
Simple data collection script for evaluation.

Usage:
    python collect_data.py
    python collect_data.py --config custom_config.toml
    python collect_data.py --database-id <database_id>
"""

import argparse
import asyncio
import sys
import tomllib
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables from root folder
root_dir = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=root_dir / ".env")

from services.data_collector import DataCollector


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Collect data from Notion for evaluation')
    parser.add_argument('--config', help='Config file path', default='config/evaluation.toml')
    parser.add_argument('--database-id', help='Single database ID to collect')
    
    args = parser.parse_args()
    
    # Load config or use single database
    if args.database_id:
        database_ids = [args.database_id]
        output_dir = "data"
        min_content_length = 10
    else:
        try:
            with open(args.config, 'rb') as f:
                config = tomllib.load(f)
            
            database_ids = config['collection']['database_ids']
            output_dir = config['collection']['output_dir']
            min_content_length = config['collection']['min_content_length']
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            sys.exit(1)
    
    if not database_ids:
        print("❌ Error: No database IDs specified")
        sys.exit(1)
    
    # Initialize collector (will load NOTION_ACCESS_TOKEN from env automatically)
    try:
        collector = DataCollector(output_dir=output_dir)
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    
    # Collect data
    print(f"🚀 Starting collection for {len(database_ids)} databases")
    
    try:
        results = await collector.collect_multiple(database_ids, min_content_length)
        
        # Print summary
        print("\n" + "="*50)
        print("📊 COLLECTION SUMMARY")
        print("="*50)
        
        total_successful = sum(stats.successful for stats in results.values())
        total_failed = sum(stats.failed for stats in results.values())
        total_skipped = sum(stats.skipped for stats in results.values())
        
        print(f"✅ Successful: {total_successful}")
        print(f"❌ Failed: {total_failed}")
        print(f"⏭️  Skipped: {total_skipped}")
        
        # Print errors if any
        all_errors = []
        for stats in results.values():
            all_errors.extend(stats.errors)
        
        if all_errors:
            print(f"\n🚨 Errors ({len(all_errors)}):")
            for error in all_errors[:5]:  # Show first 5 errors
                print(f"  • {error}")
            if len(all_errors) > 5:
                print(f"  ... and {len(all_errors) - 5} more")
        
        print("="*50)
        
        if total_failed > 0:
            sys.exit(1)
        else:
            print("✅ Collection completed successfully!")
            
    except Exception as e:
        print(f"❌ Collection failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 