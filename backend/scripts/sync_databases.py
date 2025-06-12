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
            response = await self.db.client.table('workspaces').select('id').eq(
                'name', 'Default Workspace'
            ).execute()
            
            if response.data:
                return response.data[0]['id']
            
            # Create default workspace
            workspace_data = {
                'id': str(uuid.uuid4()),
                'user_id': '00000000-0000-0000-0000-000000000000',  # Default user for script
                'notion_workspace_id': f"default_workspace_{uuid.uuid4()}",
                'name': 'Default Workspace',
                'access_token': self.access_token,  # In production, encrypt this
                'is_active': True
            }
            
            result = await self.db.client.table('workspaces').insert(workspace_data).execute()
            workspace_id = result.data[0]['id']
            
            self.logger.info(f"Created default workspace ({workspace_id})")
            return workspace_id
            
        except Exception as e:
            self.logger.error(f"Failed to get/create default workspace: {str(e)}")
            raise
    
    async def sync_database(self, db_config: DatabaseSyncConfig) -> Dict[str, Any]:
        """Sync a single Notion database."""
        self.logger.info(f"Starting sync for database: {db_config.name}")
        
        start_time = time.time()
        result = {
            'name': db_config.name,
            'database_id': db_config.database_id,
            'status': 'started',
            'total_pages': 0,
            'processed_pages': 0,
            'failed_pages': 0,
            'errors': [],
            'start_time': start_time,
            'end_time': None,
            'duration': None
        }
        
        try:
            # Use the default workspace for all databases
            if not self.workspace_id:
                self.workspace_id = await self.get_or_create_default_workspace()
            workspace_id = self.workspace_id
            
            # Get database pages
            self.logger.info(f"Fetching pages from database: {db_config.database_id}")
            pages = await self.notion_service.get_database_pages(db_config.database_id)
            
            # Apply filters
            filtered_pages = self._apply_filters(pages, db_config.filters)
            result['total_pages'] = len(filtered_pages)
            
            self.logger.info(f"Found {len(filtered_pages)} pages to process in {db_config.name}")
            
            # Process pages in batches
            for i in range(0, len(filtered_pages), db_config.batch_size):
                batch = filtered_pages[i:i + db_config.batch_size]
                
                for page in batch:
                    try:
                        # Skip archived pages
                        if page.get('archived', False):
                            continue
                        
                        # Extract content
                        content = await self.notion_service.get_page_content(page['id'])
                        title = self.notion_service.extract_title_from_page(page)
                        
                        # Update document processor settings for this database
                        if hasattr(self.document_processor, 'max_chunk_tokens'):
                            self.document_processor.max_chunk_tokens = db_config.chunk_size
                            self.document_processor.chunk_overlap_tokens = db_config.chunk_overlap
                        
                        # Process the document
                        if db_config.enable_chunking:
                            await self.document_processor.process_document(
                                workspace_id, page, content, title
                            )
                        else:
                            # Process as single document without chunking
                            await self._process_single_document(
                                workspace_id, page, content, title
                            )
                        
                        result['processed_pages'] += 1
                        
                        if result['processed_pages'] % 10 == 0:
                            self.logger.info(
                                f"{db_config.name}: Processed {result['processed_pages']}/{result['total_pages']} pages"
                            )
                    
                    except Exception as e:
                        result['failed_pages'] += 1
                        error_msg = f"Failed to process page {page.get('id', 'unknown')}: {str(e)}"
                        result['errors'].append(error_msg)
                        self.logger.error(error_msg)
                
                # Rate limiting between batches
                await asyncio.sleep(db_config.rate_limit_delay)
            
            result['status'] = 'completed'
            self.logger.info(f"Completed sync for {db_config.name}: {result['processed_pages']} processed, {result['failed_pages']} failed")
        
        except Exception as e:
            result['status'] = 'failed'
            error_msg = f"Database sync failed for {db_config.name}: {str(e)}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        finally:
            result['end_time'] = time.time()
            result['duration'] = result['end_time'] - result['start_time']
        
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
    
    async def _process_single_document(self, workspace_id: str, page_data: Dict[str, Any], 
                                     content: str, title: str) -> Dict[str, Any]:
        """Process a single document without chunking."""
        notion_page_id = page_data.get("id")
        
        # Generate embedding for the full document
        embedding_response = await self.openai_service.generate_embedding(f"{title}\n{content}")
        
        document_data = {
            'id': str(uuid.uuid4()),
            'workspace_id': workspace_id,
            'notion_page_id': notion_page_id,
            'title': title,
            'content': content,
            'embedding': embedding_response.embedding,
            'metadata': {
                'token_count': self.document_processor.count_tokens(content),
                'chunk_count': 1,
                'last_edited_time': page_data.get('last_edited_time'),
                'properties': page_data.get('properties', {}),
                'is_chunked': False
            },
            'last_edited_time': page_data.get('last_edited_time'),
            'page_url': f"https://www.notion.so/{notion_page_id.replace('-', '')}",
            'parent_page_id': page_data.get('parent', {}).get('page_id'),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        return await self.db.upsert_document(document_data)
    
    async def sync_all_databases(self) -> Dict[str, Any]:
        """Sync all databases concurrently."""
        self.logger.info(f"Starting sync for {len(self.database_configs)} databases")
        self.start_time = time.time()
        
        # Create semaphore to limit concurrent database syncs
        semaphore = asyncio.Semaphore(self.global_config.concurrent_databases)
        
        async def sync_with_semaphore(db_config):
            async with semaphore:
                return await self.sync_database(db_config)
        
        # Start all database syncs concurrently
        tasks = [sync_with_semaphore(db_config) for db_config in self.database_configs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        summary = {
            'total_databases': len(self.database_configs),
            'successful_databases': 0,
            'failed_databases': 0,
            'total_pages': 0,
            'total_processed': 0,
            'total_failed': 0,
            'start_time': self.start_time,
            'end_time': time.time(),
            'databases': []
        }
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Handle exception
                error_result = {
                    'name': self.database_configs[i].name,
                    'status': 'error',
                    'error': str(result)
                }
                summary['databases'].append(error_result)
                summary['failed_databases'] += 1
            else:
                summary['databases'].append(result)
                if result['status'] == 'completed':
                    summary['successful_databases'] += 1
                else:
                    summary['failed_databases'] += 1
                
                summary['total_pages'] += result['total_pages']
                summary['total_processed'] += result['processed_pages']
                summary['total_failed'] += result['failed_pages']
        
        summary['duration'] = summary['end_time'] - summary['start_time']
        
        self.logger.info(f"Sync completed: {summary['successful_databases']}/{summary['total_databases']} databases successful")
        self.logger.info(f"Total: {summary['total_processed']} processed, {summary['total_failed']} failed pages")
        self.logger.info(f"Duration: {summary['duration']:.2f} seconds")
        
        return summary


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