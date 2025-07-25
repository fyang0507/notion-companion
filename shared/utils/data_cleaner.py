"""
Data Cleaner Utility

Provides utilities for cleaning and resetting data in the database for experiments.
Supports selective clearing of different data types while preserving important records.
"""

import logging
from typing import Dict, Any, List, Optional
from storage.database import Database

logger = logging.getLogger(__name__)


class DataCleaner:
    """
    Utility for cleaning database data for experiments.
    
    This cleaner can:
    1. Clear document chunks while preserving documents
    2. Clear entire databases selectively
    3. Reset embedding data
    4. Provide safe cleanup for experiments
    """
    
    def __init__(self, database: Database):
        self.database = database
        logger.info("DataCleaner initialized")
    
    async def clear_document_chunks(self, 
                                  database_ids: Optional[List[str]] = None,
                                  confirm: bool = True) -> Dict[str, Any]:
        """
        Clear document chunks from specified databases.
        
        Args:
            database_ids: Optional list of database IDs to filter by
            confirm: Whether to require confirmation (set to False for automated scripts)
            
        Returns:
            Dictionary with clearing statistics
        """
        if confirm:
            logger.warning("⚠️  This will delete document chunks. This action cannot be undone.")
            response = input("Are you sure you want to continue? (yes/no): ")
            if response.lower() != 'yes':
                logger.info("Operation cancelled by user")
                return {'status': 'cancelled', 'chunks_deleted': 0}
        
        logger.info("🧹 Starting document chunks cleanup...")
        
        client = self.database.get_client()
        
        try:
            # Count existing chunks before deletion
            if database_ids:
                # First get document IDs, then count chunks
                docs_query = client.table('documents').select('id').in_('notion_database_id', database_ids).execute()
                if docs_query.data:
                    document_ids = [doc['id'] for doc in docs_query.data]
                    count_query = client.table('document_chunks').select('id', count='exact').in_('document_id', document_ids)
                else:
                    # No documents found, so no chunks to count
                    initial_count = 0
                    count_query = None
            else:
                count_query = client.table('document_chunks').select('id', count='exact')
            
            if count_query is not None:
                count_result = count_query.execute()
                initial_count = count_result.count if hasattr(count_result, 'count') else 0
            # initial_count is already set above for the None case
            
            logger.info(f"Found {initial_count} chunks to delete")
            
            # Perform deletion
            if database_ids:
                # Delete chunks from specific databases
                # First get document IDs that match the database filter
                docs_query = client.table('documents').select('id').in_('notion_database_id', database_ids).execute()
                
                if docs_query.data:
                    document_ids = [doc['id'] for doc in docs_query.data]
                    # Then get chunks from those documents
                    chunks_to_delete = client.table('document_chunks').select('id').in_('document_id', document_ids).execute()
                    
                    if chunks_to_delete.data:
                        chunk_ids = [chunk['id'] for chunk in chunks_to_delete.data]
                        delete_result = client.table('document_chunks').delete().in_('id', chunk_ids).execute()
                    else:
                        delete_result = None
                else:
                    delete_result = None
            else:
                # Delete all chunks (using a condition that matches all records)
                delete_result = client.table('document_chunks').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
            
            deleted_count = len(delete_result.data) if delete_result and delete_result.data else 0
            
            logger.info(f"✅ Successfully deleted {deleted_count} document chunks")
            
            return {
                'status': 'success',
                'chunks_deleted': deleted_count,
                'initial_count': initial_count,
                'database_ids_filtered': database_ids
            }
            
        except Exception as e:
            logger.error(f"❌ Error clearing document chunks: {e}")
            return {
                'status': 'error',
                'error_message': str(e),
                'chunks_deleted': 0
            }
    
    async def clear_documents_and_chunks(self, 
                                       database_ids: Optional[List[str]] = None,
                                       confirm: bool = True) -> Dict[str, Any]:
        """
        Clear both documents and their chunks from specified databases.
        
        Args:
            database_ids: Optional list of database IDs to filter by
            confirm: Whether to require confirmation
            
        Returns:
            Dictionary with clearing statistics
        """
        if confirm:
            logger.warning("⚠️  This will delete documents AND chunks. This action cannot be undone.")
            response = input("Are you sure you want to continue? (yes/no): ")
            if response.lower() != 'yes':
                logger.info("Operation cancelled by user")
                return {'status': 'cancelled', 'documents_deleted': 0, 'chunks_deleted': 0}
        
        logger.info("🧹 Starting documents and chunks cleanup...")
        
        client = self.database.get_client()
        
        try:
            # First, clear chunks (which will also cascade due to foreign keys)
            chunks_result = await self.clear_document_chunks(database_ids, confirm=False)
            
            # Then clear documents
            if database_ids:
                doc_delete_result = client.table('documents').delete().in_('notion_database_id', database_ids).execute()
            else:
                doc_delete_result = client.table('documents').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
            
            documents_deleted = len(doc_delete_result.data) if doc_delete_result.data else 0
            
            logger.info(f"✅ Successfully deleted {documents_deleted} documents")
            
            return {
                'status': 'success',
                'documents_deleted': documents_deleted,
                'chunks_deleted': chunks_result.get('chunks_deleted', 0),
                'database_ids_filtered': database_ids
            }
            
        except Exception as e:
            logger.error(f"❌ Error clearing documents and chunks: {e}")
            return {
                'status': 'error',
                'error_message': str(e),
                'documents_deleted': 0,
                'chunks_deleted': 0
            }
    
    
    async def clear_all_data(self, confirm: bool = True) -> Dict[str, Any]:
        """
        Clear ALL data for a completely fresh start.
        
        This clears all core tables in the correct order:
        1. document_chunks (references documents)
        2. document_metadata (references documents) 
        3. documents (references notion_databases)
        4. notion_databases (no dependencies)
        
        Args:
            confirm: Whether to require confirmation (set to False for automated scripts)
            
        Returns:
            Dictionary with clearing statistics
        """
        if confirm:
            logger.warning("⚠️  This will delete ALL data from core tables. This action cannot be undone.")
            logger.warning("   Tables: document_chunks, document_metadata, documents, notion_databases")
            response = input("Are you sure you want to continue? (yes/no): ")
            if response.lower() != 'yes':
                logger.info("Operation cancelled by user")
                return {'status': 'cancelled', 'tables_cleared': []}
        
        logger.info("🧹 Starting complete data clearing for fresh experiment...")
        
        client = self.database.get_client()
        tables_cleared = []
        total_records_deleted = 0
        
        try:
            # Clear in order that respects foreign key constraints
            # 1. Clear document_chunks first (references documents)
            logger.info("🧹 Clearing document_chunks...")
            chunks_result = client.table('document_chunks').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
            chunks_deleted = len(chunks_result.data) if chunks_result.data else 0
            logger.info(f"   ✅ Deleted {chunks_deleted} document chunks")
            tables_cleared.append('document_chunks')
            total_records_deleted += chunks_deleted
            
            # 2. Clear document_metadata (references documents)
            logger.info("🧹 Clearing document_metadata...")
            metadata_result = client.table('document_metadata').delete().neq('document_id', '00000000-0000-0000-0000-000000000000').execute()
            metadata_deleted = len(metadata_result.data) if metadata_result.data else 0
            logger.info(f"   ✅ Deleted {metadata_deleted} document metadata records")
            tables_cleared.append('document_metadata')
            total_records_deleted += metadata_deleted
            
            # 3. Clear documents (references notion_databases)
            logger.info("🧹 Clearing documents...")
            docs_result = client.table('documents').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
            docs_deleted = len(docs_result.data) if docs_result.data else 0
            logger.info(f"   ✅ Deleted {docs_deleted} documents")
            tables_cleared.append('documents')
            total_records_deleted += docs_deleted
            
            # 4. Clear notion_databases last (no dependencies)
            logger.info("🧹 Clearing notion_databases...")
            dbs_result = client.table('notion_databases').delete().neq('database_id', 'nonexistent').execute()
            dbs_deleted = len(dbs_result.data) if dbs_result.data else 0
            logger.info(f"   ✅ Deleted {dbs_deleted} database registrations")
            tables_cleared.append('notion_databases')
            total_records_deleted += dbs_deleted
            
            logger.info(f"🎉 Complete data clearing successful!")
            logger.info(f"📊 Total records deleted: {total_records_deleted}")
            logger.info(f"🗑️  Tables cleared: {', '.join(tables_cleared)}")
            
            return {
                'status': 'success', 
                'tables_cleared': tables_cleared,
                'total_records_deleted': total_records_deleted,
                'chunks_deleted': chunks_deleted,  # For backward compatibility
                'documents_deleted': docs_deleted,
                'databases_deleted': dbs_deleted,
                'metadata_deleted': metadata_deleted
            }
            
        except Exception as e:
            logger.error(f"❌ Error during complete data clearing: {e}")
            return {
                'status': 'error',
                'error_message': str(e),
                'tables_cleared': tables_cleared,
                'total_records_deleted': total_records_deleted
            }
    
    async def get_database_stats(self, database_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get statistics about data in the database.
        
        Args:
            database_ids: Optional list of database IDs to filter by
            
        Returns:
            Dictionary with database statistics
        """
        logger.info("📊 Gathering database statistics...")
        
        client = self.database.get_client()
        
        try:
            stats = {
                'timestamp': logger.info,
                'databases': {},
                'totals': {
                    'documents': 0,
                    'chunks': 0,
                    'documents_with_embeddings': 0,
                    'chunks_with_embeddings': 0
                }
            }
            
            # Get document counts
            if database_ids:
                doc_query = client.table('documents').select('notion_database_id', count='exact').in_('notion_database_id', database_ids)
            else:
                doc_query = client.table('documents').select('notion_database_id', count='exact')
            
            doc_result = doc_query.execute()
            total_docs = doc_result.count if hasattr(doc_result, 'count') else 0
            
            # Get chunk counts
            chunk_result = client.table('document_chunks').select('id', count='exact').execute()
            total_chunks = chunk_result.count if hasattr(chunk_result, 'count') else 0
            
            # Get embedding counts
            doc_with_embeddings = client.table('documents').select(
                'id', count='exact'
            ).not_.is_('content_embedding', 'null').execute()
            docs_with_emb = doc_with_embeddings.count if hasattr(doc_with_embeddings, 'count') else 0
            
            chunk_with_embeddings = client.table('document_chunks').select(
                'id', count='exact'
            ).not_.is_('embedding', 'null').execute()
            chunks_with_emb = chunk_with_embeddings.count if hasattr(chunk_with_embeddings, 'count') else 0
            
            stats['totals'] = {
                'documents': total_docs,
                'chunks': total_chunks,
                'documents_with_embeddings': docs_with_emb,
                'chunks_with_embeddings': chunks_with_emb
            }
            
            logger.info(f"📊 Stats: {total_docs} docs, {total_chunks} chunks, {docs_with_emb} doc embeddings, {chunks_with_emb} chunk embeddings")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error gathering database stats: {e}")
            return {
                'status': 'error',
                'error_message': str(e)
            }


def get_data_cleaner(database: Database) -> DataCleaner:
    """Factory function to create a data cleaner."""
    return DataCleaner(database)