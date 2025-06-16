#!/usr/bin/env python3
"""
Notion Database Sync Script

This script connects to multiple Notion databases simultaneously and syncs them
to the local database with chunking and embeddings.

Usage:
    python sync_databases.py --config config/databases.toml
    python sync_databases.py --config config/databases.toml --dry-run

Note: The Notion access token is read from the NOTION_ACCESS_TOKEN environment variable
or from a .env file in the backend directory.
"""

import argparse
import asyncio
import logging
import os
import sys
import time
import uuid
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

from database import get_db, init_db
from services.notion_service import NotionService
from services.openai_service import get_openai_service
from services.document_processor import get_document_processor


class DatabaseSyncConfig:
    """Configuration for a single database sync."""
    
    def __init__(self, config_dict: Dict[str, Any]):
        self.name = config_dict.get('name', 'Unnamed Database')
        self.database_id = config_dict.get('database_id', '')
        self.description = config_dict.get('description', '')
        
        # Sync settings
        sync_settings = config_dict.get('sync_settings', {})
        self.batch_size = sync_settings.get('batch_size', 10)
        self.rate_limit_delay = sync_settings.get('rate_limit_delay', 1.0)
        self.max_retries = sync_settings.get('max_retries', 3)
        
        # Filters
        self.filters = config_dict.get('filters', {})
        
        # Processing settings
        processing = config_dict.get('processing', {})
        self.chunk_size = processing.get('chunk_size', 1000)
        self.chunk_overlap = processing.get('chunk_overlap', 100)
        self.enable_chunking = processing.get('enable_chunking', True)


class GlobalSyncConfig:
    """Global configuration settings."""
    
    def __init__(self, config_dict: Dict[str, Any]):
        global_settings = config_dict.get('global_settings', {})
        
        self.concurrent_databases = global_settings.get('concurrent_databases', 3)
        self.default_batch_size = global_settings.get('default_batch_size', 10)
        self.default_rate_limit_delay = global_settings.get('default_rate_limit_delay', 1.0)
        self.default_max_retries = global_settings.get('default_max_retries', 3)
        
        self.embedding_model = global_settings.get('embedding_model', 'text-embedding-3-small')
        self.embedding_batch_size = global_settings.get('embedding_batch_size', 100)
        
        self.log_level = global_settings.get('log_level', 'INFO')
        self.log_file = global_settings.get('log_file', 'database_sync.log')
        
        self.supabase_batch_size = global_settings.get('supabase_batch_size', 50)


class DatabaseSyncer:
    """Handles syncing of multiple Notion databases."""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        
        # Get access token from environment
        self.access_token = os.getenv('NOTION_ACCESS_TOKEN')
        if not self.access_token:
            raise ValueError(
                "NOTION_ACCESS_TOKEN environment variable not found. "
                "Set it in your environment or add it to a .env file."
            )
        
        # Load configuration
        with open(config_path, 'rb') as f:
            config_data = tomllib.load(f)
        
        self.global_config = GlobalSyncConfig(config_data)
        self.database_configs = [
            DatabaseSyncConfig(db_config) 
            for db_config in config_data.get('databases', [])
        ]
        
        # Initialize services
        self.db = None
        self.openai_service = None
        self.document_processor = None
        self.notion_service = None
        
        # Single workspace for this application
        self.workspace_id = None
        
        # Tracking
        self.sync_results = {}
        self.start_time = None
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = getattr(logging, self.global_config.log_level.upper(), logging.INFO)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.global_config.log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    async def initialize_services(self):
        """Initialize all required services."""
        self.logger.info("Initializing services...")
        
        # Initialize database
        await init_db()
        self.db = get_db()
        
        # Initialize OpenAI service
        self.openai_service = get_openai_service()
        
        # Initialize document processor
        self.document_processor = get_document_processor(self.openai_service, self.db)
        
        # Initialize Notion service
        self.notion_service = NotionService(self.access_token)
        
        self.logger.info("Services initialized successfully")
    
    async def get_or_create_default_workspace(self) -> str:
        """Get the default workspace for this single-user application."""
        try:
            # Check if default workspace exists
            response = self.db.client.table('workspaces').select('id').eq(
                'name', 'Default Workspace'
            ).execute()
            
            if response.data:
                return response.data[0]['id']
            
            # Create default workspace
            workspace_data = {
                'id': str(uuid.uuid4()),
                'name': 'Default Workspace',
                'notion_access_token': self.access_token,  # In production, encrypt this
                'is_active': True
            }
            
            result = self.db.client.table('workspaces').insert(workspace_data).execute()
            workspace_id = result.data[0]['id']
            
            self.logger.info(f"Created default workspace ({workspace_id})")
            return workspace_id
            
        except Exception as e:
            self.logger.error(f"Failed to get/create default workspace: {str(e)}")
            raise
    
    async def sync_database(self, db_config: DatabaseSyncConfig) -> Dict[str, Any]:
        """Sync a single Notion database using the new schema."""
        self.logger.info(f"Starting sync for database: {db_config.name}")
        
        start_time = time.time()
        
        try:
            # Use the default workspace for all databases
            if not self.workspace_id:
                self.workspace_id = await self.get_or_create_default_workspace()
            workspace_id = self.workspace_id
            
            # Update document processor settings for this database
            if hasattr(self.document_processor, 'max_chunk_tokens'):
                self.document_processor.max_chunk_tokens = db_config.chunk_size
                self.document_processor.chunk_overlap_tokens = db_config.chunk_overlap
            
            # Use the new document processor method
            result = await self.document_processor.process_database_pages(
                workspace_id, 
                db_config.database_id, 
                self.notion_service, 
                db_config.batch_size
            )
            
            # Add timing and config information
            result.update({
                'name': db_config.name,
                'status': 'completed',
                'start_time': start_time,
                'end_time': time.time(),
                'duration': time.time() - start_time
            })
            
            self.logger.info(f"Completed sync for {db_config.name}: {result['processed_pages']} processed, {result['failed_pages']} failed")
        
        except Exception as e:
            result = {
                'name': db_config.name,
                'database_id': db_config.database_id,
                'status': 'failed',
                'total_pages': 0,
                'processed_pages': 0,
                'failed_pages': 0,
                'errors': [f"Database sync failed: {str(e)}"],
                'start_time': start_time,
                'end_time': time.time(),
                'duration': time.time() - start_time
            }
            self.logger.error(f"Database sync failed for {db_config.name}: {str(e)}")
        
        return result
    
    def _apply_filters(self, pages: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply filters to the list of pages."""
        if not filters:
            return pages
        
        filtered_pages = []
        
        for page in pages:
            include_page = True
            
            # Check archived filter
            if 'archived' in filters:
                if page.get('archived', False) != filters['archived']:
                    include_page = False
                    continue
            
            # Check property filters
            properties = page.get('properties', {})
            for filter_key, filter_value in filters.items():
                if filter_key == 'archived':
                    continue  # Already handled above
                
                # Check if property exists and matches filter
                if filter_key in properties:
                    prop_data = properties[filter_key]
                    prop_type = prop_data.get('type')
                    
                    if prop_type == 'select' and prop_data.get('select'):
                        if prop_data['select'].get('name') != filter_value:
                            include_page = False
                            break
                    elif prop_type == 'status' and prop_data.get('status'):
                        if prop_data['status'].get('name') != filter_value:
                            include_page = False
                            break
                    # Add more property type checks as needed
            
            if include_page:
                filtered_pages.append(page)
        
        return filtered_pages
    
    async def sync_all_databases(self) -> Dict[str, Any]:
        """Sync all databases using the new document processor approach."""
        self.logger.info(f"Starting sync for {len(self.database_configs)} databases")
        self.start_time = time.time()
        
        try:
            # Use the default workspace for all databases
            if not self.workspace_id:
                self.workspace_id = await self.get_or_create_default_workspace()
            workspace_id = self.workspace_id
            
            # Convert database configs to the format expected by document processor
            database_configs = []
            for db_config in self.database_configs:
                database_configs.append({
                    'name': db_config.name,
                    'database_id': db_config.database_id,
                    'description': db_config.description,
                    'sync_settings': {
                        'batch_size': db_config.batch_size,
                        'rate_limit_delay': db_config.rate_limit_delay,
                        'max_retries': db_config.max_retries
                    }
                })
            
            # Use the new document processor method
            results = await self.document_processor.process_workspace_databases(
                workspace_id, 
                database_configs, 
                self.notion_service,
                self.global_config.default_batch_size
            )
            
            # Add timing information
            results.update({
                'start_time': self.start_time,
                'end_time': time.time(),
                'duration': time.time() - self.start_time
            })
            
            # Calculate summary statistics
            total_pages = sum(db_result['results']['total_pages'] for db_result in results['database_results'])
            total_processed = sum(db_result['results']['processed_pages'] for db_result in results['database_results'])
            total_failed = sum(db_result['results']['failed_pages'] for db_result in results['database_results'])
            
            results.update({
                'total_pages': total_pages,
                'total_processed': total_processed,
                'total_failed': total_failed,
                'successful_databases': results['processed_databases'],
                'failed_databases': results['failed_databases']
            })
            
            self.logger.info(f"Sync completed: {results['successful_databases']}/{results['total_databases']} databases successful")
            self.logger.info(f"Total: {results['total_processed']} processed, {results['total_failed']} failed pages")
            self.logger.info(f"Duration: {results['duration']:.2f} seconds")
            
            return results
        
        except Exception as e:
            self.logger.error(f"Sync failed: {str(e)}")
            return {
                'total_databases': len(self.database_configs),
                'successful_databases': 0,
                'failed_databases': len(self.database_configs),
                'total_pages': 0,
                'total_processed': 0,
                'total_failed': 0,
                'start_time': self.start_time,
                'end_time': time.time(),
                'duration': time.time() - self.start_time,
                'database_results': [],
                'errors': [str(e)]
            }


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Sync multiple Notion databases')
    parser.add_argument(
        '--config', 
        default='config/databases.toml',
        help='Path to TOML config file (default: config/databases.toml)'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true', 
        help='Dry run - validate config but don\'t sync'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize syncer (token comes from environment/dotenv)
        syncer = DatabaseSyncer(args.config)
        
        if args.dry_run:
            print(f"Dry run: Would sync {len(syncer.database_configs)} databases")
            for db_config in syncer.database_configs:
                print(f"  - {db_config.name} ({db_config.database_id})")
            return
        
        # Initialize services
        await syncer.initialize_services()
        
        # Run sync
        results = await syncer.sync_all_databases()
        
        # Print summary
        print("\n" + "="*50)
        print("SYNC SUMMARY")
        print("="*50)
        print(f"Databases: {results['successful_databases']}/{results['total_databases']} successful")
        print(f"Pages: {results['total_processed']} processed, {results['total_failed']} failed")
        print(f"Duration: {results['duration']:.2f} seconds")
        
        # Exit with error code if any database failed
        if results['failed_databases'] > 0:
            sys.exit(1)
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())