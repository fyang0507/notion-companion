#!/usr/bin/env python3
"""
Notion Database Sync Script - Updated for simplified schema
Syncs Notion databases to the new schema without workspace concept.

Usage:
    python sync_databases.py --config config/databases.toml
    python sync_databases.py --database-id <notion_database_id>
    python sync_databases.py --dry-run

Environment variables required:
    NOTION_ACCESS_TOKEN - Your Notion integration token
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
load_dotenv(dotenv_path="../../.env")

from storage.database import get_db, init_db
from ingestion.services.notion_service import NotionService
from ingestion.services.openai_service import get_openai_service
from ingestion.services.document_processor import get_document_processor
from storage.database_schema_manager import get_schema_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('../logs/sync.log')
    ]
)
logger = logging.getLogger(__name__)


class DatabaseSyncConfig:
    """Configuration for a single database sync in simplified schema."""
    
    def __init__(self, config_dict: Dict[str, Any]):
        self.name = config_dict.get('name', 'Unnamed Database')
        self.database_id = config_dict.get('database_id', '')
        self.description = config_dict.get('description', '')
        
        # Sync settings
        sync_settings = config_dict.get('sync_settings', {})
        self.full_sync = sync_settings.get('full_sync', False)
        self.page_limit = sync_settings.get('page_limit', None)
        self.chunk_content = sync_settings.get('chunk_content', True)
        self.generate_embeddings = sync_settings.get('generate_embeddings', True)
        
        # Processing settings
        processing = config_dict.get('processing', {})
        self.skip_empty_pages = processing.get('skip_empty_pages', True)
        self.min_content_length = processing.get('min_content_length', 50)
        self.extract_metadata = processing.get('extract_metadata', True)
        
        # Rate limiting
        rate_limiting = config_dict.get('rate_limiting', {})
        self.requests_per_second = rate_limiting.get('requests_per_second', 2)
        self.batch_size = rate_limiting.get('batch_size', 10)
        
    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        if not self.database_id:
            logger.error(f"Database '{self.name}' missing database_id")
            return False
        return True


class NotionDatabaseSyncer:
    """Main syncer class for simplified schema."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.db = None
        self.notion_service = None
        self.openai_service = None
        self.document_processor = None
        self.schema_manager = None
        
        # Stats
        self.stats = {
            'databases_processed': 0,
            'pages_processed': 0,
            'pages_updated': 0,
            'pages_created': 0,
            'pages_skipped': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
    
    async def initialize(self):
        """Initialize all services."""
        logger.info("Initializing services for simplified schema...")
        
        try:
            # Initialize database
            await init_db()
            self.db = get_db()
            
            # Initialize schema manager
            self.schema_manager = get_schema_manager(self.db)
            
            # Initialize Notion service
            notion_token = os.getenv("NOTION_ACCESS_TOKEN")
            if not notion_token:
                raise ValueError("NOTION_ACCESS_TOKEN environment variable is required")
            
            self.notion_service = NotionService(notion_token)
            
            # Initialize OpenAI service
            self.openai_service = get_openai_service()
            
            # Initialize document processor
            self.document_processor = get_document_processor(self.openai_service, self.db)
            
            logger.info("✅ All services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise
    
    async def sync_database(self, config: DatabaseSyncConfig) -> Dict[str, Any]:
        """Sync a single Notion database."""
        if not config.is_valid():
            return {'success': False, 'error': 'Invalid configuration'}
        
        logger.info(f"🔄 Starting sync for database: {config.name} ({config.database_id})")
        
        sync_stats = {
            'database_id': config.database_id,
            'database_name': config.name,
            'pages_processed': 0,
            'pages_created': 0,
            'pages_updated': 0,
            'pages_skipped': 0,
            'errors': 0,
            'start_time': datetime.now(),
            'success': False
        }
        
        try:
            # 1. Register or update the notion database record
            await self._register_notion_database(config)
            
            # 2. Query all pages in the database
            logger.info(f"📄 Querying pages from database: {config.name}")
            pages = await self.notion_service.get_database_pages(config.database_id)
            
            # Apply page limit if specified
            if config.page_limit:
                pages = pages[:config.page_limit]
            
            logger.info(f"Found {len(pages)} pages to process")
            
            # 4. Process pages in batches
            for i in range(0, len(pages), config.batch_size):
                batch = pages[i:i + config.batch_size]
                logger.info(f"Processing batch {i // config.batch_size + 1} ({len(batch)} pages)")
                
                for page in batch:
                    try:
                        result = await self._process_page(page, config)
                        
                        if result['action'] == 'created':
                            sync_stats['pages_created'] += 1
                        elif result['action'] == 'updated':
                            sync_stats['pages_updated'] += 1
                        elif result['action'] == 'skipped':
                            sync_stats['pages_skipped'] += 1
                        
                        sync_stats['pages_processed'] += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing page {page.get('id', 'unknown')}: {e}")
                        sync_stats['errors'] += 1
                        continue
                
                # Rate limiting between batches
                if i + config.batch_size < len(pages):
                    await asyncio.sleep(1.0 / config.requests_per_second)
            
            # 5. Update database sync timestamp
            if not self.dry_run:
                self.db.update_database_sync_time(config.database_id)
            
            sync_stats['success'] = True
            sync_stats['end_time'] = datetime.now()
            
            logger.info(f"✅ Completed sync for {config.name}: "
                       f"{sync_stats['pages_created']} created, "
                       f"{sync_stats['pages_updated']} updated, "
                       f"{sync_stats['pages_skipped']} skipped, "
                       f"{sync_stats['errors']} errors")
            
            return sync_stats
            
        except Exception as e:
            logger.error(f"❌ Failed to sync database {config.name}: {e}")
            sync_stats['error'] = str(e)
            sync_stats['end_time'] = datetime.now()
            return sync_stats
    
    async def _register_notion_database(self, config: DatabaseSyncConfig):
        """Register or update the notion database in our system."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would register database: {config.name}")
            return
        
        # Get Notion access token
        notion_token = os.getenv("NOTION_ACCESS_TOKEN")
        
        database_data = {
            'database_id': config.database_id,
            'database_name': config.name,
            'notion_access_token': notion_token,  # In production, this should be encrypted
            'notion_schema': {},  # Will be populated with actual schema
            'field_definitions': {},
            'queryable_fields': {},
            'is_active': True,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        try:
            # For now, we'll use basic info since we don't have a get_database method
            # This can be enhanced later to fetch actual database schema
            logger.info(f"Using basic database info for {config.name}")
        
        except Exception as e:
            logger.warning(f"Could not fetch database schema: {e}")
        
        # Upsert the database record
        result = self.db.upsert_notion_database(database_data)
        logger.info(f"📝 Registered database: {config.name} ({config.database_id})")
        return result
    
    async def _process_page(self, page: Dict[str, Any], config: DatabaseSyncConfig) -> Dict[str, str]:
        """Process a single page from Notion."""
        page_id = page['id']
        
        try:
            # Check if page already exists
            existing_doc = self.db.get_document_by_notion_page_id(page_id)
            
            # Get page content
            page_content = await self.notion_service.get_page_content(page_id)
            
            if not page_content or len(page_content.strip()) < config.min_content_length:
                if config.skip_empty_pages:
                    logger.debug(f"Skipping empty page: {page_id}")
                    return {'action': 'skipped', 'reason': 'empty_content'}
            
            # Extract title
            title = self._extract_page_title(page)
            
            # Check if update is needed
            if existing_doc:
                last_edited = page.get('last_edited_time')
                existing_last_edited = existing_doc.get('last_edited_time')
                
                if last_edited and existing_last_edited:
                    if last_edited <= existing_last_edited and not config.full_sync:
                        logger.debug(f"Page not modified, skipping: {title}")
                        return {'action': 'skipped', 'reason': 'not_modified'}
            
            if self.dry_run:
                action = 'updated' if existing_doc else 'created'
                logger.info(f"[DRY RUN] Would {action} page: {title}")
                return {'action': action}
            
            # Process the page
            await self._save_page_to_database(page, page_content, config)
            
            action = 'updated' if existing_doc else 'created'
            logger.debug(f"Page {action}: {title}")
            return {'action': action}
            
        except Exception as e:
            logger.error(f"Error processing page {page_id}: {e}")
            raise
    
    async def _save_page_to_database(self, page: Dict[str, Any], content: str, config: DatabaseSyncConfig):
        """Save a page and its content to the database."""
        page_id = page['id']
        title = self._extract_page_title(page)
        
        # Prepare document data
        document_data = {
            'notion_page_id': page_id,
            'notion_database_id': config.database_id,
            'notion_database_id_ref': config.database_id,
            'title': title,
            'content': content,
            'content_type': 'page',
            'created_time': page.get('created_time'),
            'last_edited_time': page.get('last_edited_time'),
            'created_by': page.get('created_by', {}).get('id'),
            'last_edited_by': page.get('last_edited_by', {}).get('id'),
            'page_url': page.get('url'),
            'notion_properties': page.get('properties', {}),
            'extracted_metadata': self._extract_basic_metadata(page),
            'indexed_at': datetime.utcnow().isoformat()
        }
        
        # Generate embeddings if configured
        if config.generate_embeddings:
            try:
                embedding_text = f"{title}\n\n{content}"
                embedding_response = await self.openai_service.generate_embedding(embedding_text)
                document_data['content_embedding'] = embedding_response.embedding
                document_data['token_count'] = embedding_response.tokens
                
                logger.debug(f"Generated embedding for: {title} ({embedding_response.tokens} tokens)")
                
            except Exception as e:
                logger.warning(f"Failed to generate embedding for {title}: {e}")
        
        # Save document
        document = self.db.upsert_document(document_data)
        document_id = document['id']
        
        # Process chunks if configured
        if config.chunk_content and len(content) > 1000:  # Only chunk longer content
            await self._process_document_chunks(document_id, title, content, config)
        
        # Save metadata using schema manager
        if config.extract_metadata:
            try:
                metadata = await self.schema_manager.extract_document_metadata(
                    document_id, page, config.database_id
                )
                if metadata:
                    # Convert to the expected format for the simplified schema
                    metadata_record = {
                        'document_id': document_id,
                        'notion_database_id': config.database_id,
                        'extracted_fields': metadata
                    }
                    self.db.upsert_document_metadata(metadata_record)
            except Exception as e:
                logger.warning(f"Failed to extract metadata for {document_id}: {e}")
        
        logger.debug(f"Saved document: {title} ({document_id})")
    
    async def _process_document_chunks(self, document_id: str, title: str, content: str, config: DatabaseSyncConfig):
        """Process document into chunks with embeddings."""
        try:
            # Delete existing chunks
            self.db.delete_document_chunks(document_id)
            
            # Generate chunks using contextual chunker
            contextual_chunks = await self.document_processor.contextual_chunker.chunk_with_context(
                content=content,
                title=title,
                page_data={}
            )
            # Extract just the content for compatibility with existing chunk processing logic
            chunks = [chunk['content'] for chunk in contextual_chunks]
            
            chunks_data = []
            for i, chunk_content in enumerate(chunks):
                chunk_data = {
                    'document_id': document_id,
                    'content': chunk_content,
                    'chunk_order': i,
                    'chunk_metadata': {'section': i}
                }
                
                # Generate chunk embedding
                if config.generate_embeddings:
                    try:
                        embedding_response = await self.openai_service.generate_embedding(chunk_content)
                        chunk_data['embedding'] = embedding_response.embedding
                    except Exception as e:
                        logger.warning(f"Failed to generate chunk embedding: {e}")
                
                chunks_data.append(chunk_data)
            
            # Save chunks
            if chunks_data:
                self.db.upsert_document_chunks(chunks_data)
                logger.debug(f"Created {len(chunks_data)} chunks for document {document_id}")
                
        except Exception as e:
            logger.error(f"Failed to process chunks for document {document_id}: {e}")
    
    def _extract_page_title(self, page: Dict[str, Any]) -> str:
        """Extract title from page properties."""
        properties = page.get('properties', {})
        
        # Try common title field names
        for field_name in ['Name', 'Title', 'title', 'name']:
            if field_name in properties:
                prop = properties[field_name]
                if prop.get('type') == 'title' and prop.get('title'):
                    return prop['title'][0].get('plain_text', 'Untitled')
        
        return 'Untitled'
    
    def _extract_basic_metadata(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """Extract basic metadata for document storage (simplified)."""
        properties = page.get('properties', {})
        metadata = {}
        
        # Extract only essential fields for document.extracted_metadata
        # Complex metadata extraction is now handled by DatabaseSchemaManager
        for prop_name, prop_value in properties.items():
            prop_type = prop_value.get('type')
            
            if prop_type == 'select' and prop_value.get('select'):
                metadata[prop_name] = prop_value['select']['name']
            elif prop_type == 'multi_select':
                metadata[prop_name] = [item['name'] for item in prop_value.get('multi_select', [])]
            elif prop_type == 'date' and prop_value.get('date'):
                metadata[prop_name] = prop_value['date']['start']
            elif prop_type == 'number' and prop_value.get('number') is not None:
                metadata[prop_name] = prop_value['number']
            elif prop_type == 'checkbox':
                metadata[prop_name] = prop_value.get('checkbox', False)
        
        return metadata
    
    async def run_sync(self, configs: List[DatabaseSyncConfig]) -> Dict[str, Any]:
        """Run sync for multiple databases."""
        self.stats['start_time'] = datetime.now()
        
        logger.info(f"🚀 Starting sync for {len(configs)} databases")
        
        database_results = []
        
        for config in configs:
            try:
                result = await self.sync_database(config)
                database_results.append(result)
                
                # Update global stats
                self.stats['databases_processed'] += 1
                self.stats['pages_processed'] += result.get('pages_processed', 0)
                self.stats['pages_created'] += result.get('pages_created', 0)
                self.stats['pages_updated'] += result.get('pages_updated', 0)
                self.stats['pages_skipped'] += result.get('pages_skipped', 0)
                self.stats['errors'] += result.get('errors', 0)
                
            except Exception as e:
                logger.error(f"Failed to sync database {config.name}: {e}")
                self.stats['errors'] += 1
                database_results.append({
                    'database_id': config.database_id,
                    'database_name': config.name,
                    'success': False,
                    'error': str(e)
                })
        
        self.stats['end_time'] = datetime.now()
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        logger.info(f"🎉 Sync completed in {duration:.1f}s:")
        logger.info(f"   Databases: {self.stats['databases_processed']}")
        logger.info(f"   Pages: {self.stats['pages_processed']} processed")
        logger.info(f"   Created: {self.stats['pages_created']}")
        logger.info(f"   Updated: {self.stats['pages_updated']}")
        logger.info(f"   Skipped: {self.stats['pages_skipped']}")
        logger.info(f"   Errors: {self.stats['errors']}")
        
        return {
            'success': True,
            'stats': self.stats,
            'database_results': database_results
        }


def load_config(config_path: str) -> List[DatabaseSyncConfig]:
    """Load sync configuration from TOML file."""
    try:
        with open(config_path, 'rb') as f:
            config_data = tomllib.load(f)
        
        configs = []
        for db_config in config_data.get('databases', []):
            config = DatabaseSyncConfig(db_config)
            if config.is_valid():
                configs.append(config)
            else:
                logger.error(f"Invalid configuration for database: {config.name}")
        
        return configs
        
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        return []


def create_single_database_config(database_id: str) -> DatabaseSyncConfig:
    """Create a config for a single database ID, checking config file first."""
    # First try to find the database in the config file
    default_config_path = Path(__file__).parent.parent / 'config' / 'databases.toml'
    
    if default_config_path.exists():
        try:
            with open(default_config_path, 'rb') as f:
                config_data = tomllib.load(f)
            
            # Look for matching database_id in config
            for db_config in config_data.get('databases', []):
                if db_config.get('database_id') == database_id:
                    logger.info(f"Found database config for {database_id}: {db_config.get('name')}")
                    return DatabaseSyncConfig(db_config)
        except Exception as e:
            logger.warning(f"Could not load config file: {e}")
    
    # Fallback to generic config if not found in config file
    logger.warning(f"Using generic config for database {database_id} - consider adding it to databases.toml")
    config_dict = {
        'name': f'Database {database_id[:8]}',
        'database_id': database_id,
        'description': 'Single database sync',
        'sync_settings': {
            'full_sync': False,
            'chunk_content': True,
            'generate_embeddings': True
        },
        'processing': {
            'skip_empty_pages': True,
            'min_content_length': 50,
            'extract_metadata': True
        },
        'rate_limiting': {
            'requests_per_second': 2,
            'batch_size': 10
        }
    }
    
    return DatabaseSyncConfig(config_dict)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Sync Notion databases to simplified schema')
    parser.add_argument('--config', help='Path to TOML configuration file')
    parser.add_argument('--database-id', help='Single database ID to sync')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without making them')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Determine configuration
    configs = []
    
    if args.config:
        configs = load_config(args.config)
    elif args.database_id:
        configs = [create_single_database_config(args.database_id)]
    else:
        # Try to load default config
        default_config_path = Path(__file__).parent.parent / 'config' / 'databases.toml'
        if default_config_path.exists():
            logger.info(f"Loading default configuration from {default_config_path}")
            configs = load_config(str(default_config_path))
        else:
            logger.error("No configuration provided. Use --config or --database-id, or create config/databases.toml")
            sys.exit(1)
    
    if not configs:
        logger.error("No valid database configurations found")
        sys.exit(1)
    
    # Run sync
    syncer = NotionDatabaseSyncer(dry_run=args.dry_run)
    
    try:
        await syncer.initialize()
        result = await syncer.run_sync(configs)
        
        if result['success']:
            logger.info("✅ All sync operations completed successfully")
            sys.exit(0)
        else:
            logger.error("❌ Some sync operations failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Sync failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())