#!/usr/bin/env python3
"""
Multi-Database Data Collection Script

Collects documents from multiple Notion databases and creates individual
database collection files (compatible with existing pipeline).

Usage:
    python collect_database.py --config config/database.toml
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config_loader import load_config
from services.data_collector import DataCollector

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MultiDatabaseCollector:
    """Collects documents from multiple Notion databases."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the multi-database collector."""
        self.config = config
        
        # Fail hard on missing required config
        self.output_dir = Path(config["collection"]["output_dir"])
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Collection settings
        self.min_content_length = config["collection"]["min_content_length"]
        self.timeout_per_db = config["collection"]["timeout_per_database"]
        
        # Database configurations
        self.database_configs = config["databases"]["database_configs"]
        
        logger.info(f"MultiDatabaseCollector initialized with {len(self.database_configs)} databases")
        logger.info(f"Output directory: {self.output_dir}")
    
    def get_database_config(self, database_id: str) -> Dict[str, Any]:
        """Get configuration for a specific database."""
        for db_config in self.database_configs:
            if db_config["database_id"] == database_id:
                return db_config
        raise ValueError(f"No configuration found for database: {database_id}")
    
    async def collect_database(self, database_id: str) -> Dict[str, Any]:
        """Collect documents from a single database."""
        db_config = self.get_database_config(database_id)
        database_name = db_config["name"]
        logger.info(f"📊 Collecting from database: {database_name} ({database_id})")
        
        # Create data collector for this database
        collector = DataCollector()
        
        try:
            # Collect documents using the existing DataCollector
            documents = await collector.collect_database(database_id=database_id)
            
            # Get collection stats
            collection_stats = collector.get_collection_stats()
            
            # Save the collection result directly
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            target_file = self.output_dir / f"{database_id}_{timestamp}.json"
            
            # Create our standardized format
            collection_result = {
                "database_id": database_id,
                "database_name": database_name,
                "database_config": db_config,
                "collected_at": datetime.now().isoformat(),
                "total_documents": len(documents),
                "documents": [doc.model_dump() for doc in documents],
                "collection_metadata": {
                    "min_content_length": self.min_content_length,
                    "collection_timestamp": timestamp
                },
                "collection_stats": collection_stats.model_dump()
            }
            
            # Save in our format
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(collection_result, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"✅ Collected {len(documents)} documents from {database_name}")
            logger.info(f"💾 Saved to: {target_file}")
            
            return collection_result
            
        except Exception as e:
            logger.error(f"❌ Failed to collect from database {database_name}: {str(e)}")
            return {
                "database_id": database_id,
                "database_name": database_name,
                "error": str(e),
                "collected_at": datetime.now().isoformat(),
                "total_documents": 0,
                "documents": []
            }
    
    async def collect_all_databases(self) -> List[Dict[str, Any]]:
        """Collect documents from all configured databases."""
        # Process all databases from config
        database_ids = [db["database_id"] for db in self.database_configs]
        
        logger.info(f"🚀 Starting multi-database collection for {len(database_ids)} databases")
        
        # Collect from each database - no merging, just individual files
        collection_results = []
        successful_databases = 0
        failed_databases = 0
        
        for database_id in database_ids:
            try:
                result = await self.collect_database(database_id)
                collection_results.append(result)
                
                if "error" not in result:
                    successful_databases += 1
                else:
                    failed_databases += 1
                    
            except Exception as e:
                logger.error(f"❌ Critical error collecting {database_id}: {str(e)}")
                collection_results.append({
                    "database_id": database_id,
                    "error": str(e),
                    "total_documents": 0
                })
                failed_databases += 1
        
        logger.info(f"✅ Multi-database collection completed")
        logger.info(f"📊 Processed {successful_databases}/{len(database_ids)} databases successfully")
        
        return collection_results
    
    def print_collection_summary(self, results: List[Dict[str, Any]]):
        """Print a summary of the collection results."""
        print("\n" + "="*60)
        print("📊 MULTI-DATABASE COLLECTION SUMMARY")
        print("="*60)
        
        total_databases = len(results)
        successful_databases = sum(1 for r in results if "error" not in r)
        total_documents = sum(r.get("total_documents", 0) for r in results if "error" not in r)
        
        print(f"✅ Collection completed successfully!")
        print(f"📂 Output directory: {self.output_dir}")
        print(f"📊 Databases: {successful_databases}/{total_databases} successful")
        print(f"📄 Total documents: {total_documents}")
        
        print("\n📋 Database Details:")
        for db_result in results:
            db_name = db_result.get("database_name", db_result.get("database_id", "unknown")[:8])
            doc_count = db_result.get("total_documents", 0)
            
            if "error" in db_result:
                print(f"  ❌ {db_name}: Error - {db_result['error']}")
            else:
                print(f"  ✅ {db_name}: {doc_count} documents")
        
        print("\n📁 Generated Files:")
        for db_result in results:
            if "error" not in db_result:
                timestamp = db_result.get("collection_metadata", {}).get("collection_timestamp", "unknown")
                db_id = db_result["database_id"]
                individual_file = f"{db_id}_{timestamp}.json"
                print(f"  • {individual_file}")
        
        print("\n🔄 Next Steps:")
        print("  1. Run chunking pipeline on individual database files with specific configs")
        print("  2. Run question generation on chunked results with specific configs")
        print("  3. Process each database separately using CLI commands")
        print("="*60)


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Collect documents from multiple Notion databases")
    parser.add_argument("--config", "-c", type=Path, 
                        default=Path(__file__).parent.parent / "config" / "database.toml",
                        help="Multi-database configuration file")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        default="INFO", help="Logging level")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    try:
        # Load configuration
        config = load_config(args.config)
        logger.info(f"Configuration loaded from: {args.config}")
        
        # Create collector
        collector = MultiDatabaseCollector(config)
        
        # Collect from all databases
        results = await collector.collect_all_databases()
        
        # Print summary
        collector.print_collection_summary(results)
        
    except Exception as e:
        logger.error(f"Multi-database collection failed: {str(e)}")
        print(f"\n❌ Collection failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())