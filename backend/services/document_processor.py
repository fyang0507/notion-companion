"""
Document Processor - Single Database Model

This webapp is designed to support ONLY ONE Notion workspace with multiple databases.
No workspace concept exists - all operations are per-database.
"""

from typing import List, Dict, Any, Tuple, Optional
import re
import tiktoken
from services.openai_service import OpenAIService
from services.database_schema_manager import DatabaseSchemaManager
from database import Database
from config.model_config import get_model_config
import asyncio
from datetime import datetime
import uuid
import logging

class DocumentProcessor:
    """
    Process documents from Notion databases.
    Single database model - no workspace concept.
    """
    
    def __init__(self, openai_service: OpenAIService, db: Database):
        self.openai_service = openai_service
        self.db = db
        self.schema_manager = DatabaseSchemaManager(db)
        self.model_config = get_model_config()
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self.logger = logging.getLogger(__name__)
        
        # Get chunking parameters from config
        limits_config = self.model_config.get_limits_config()
        self.max_chunk_tokens = limits_config.chunk_size_tokens
        self.chunk_overlap_tokens = limits_config.chunk_overlap_tokens
        self.min_chunk_tokens = 50
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self.encoding.encode(text))
    
    def chunk_text(self, text: str, title: str = "") -> List[Dict[str, Any]]:
        """Split text into chunks with overlap, preserving semantic boundaries."""
        if not text.strip():
            return []
        
        # First, split by major sections (double newlines)
        sections = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = ""
        current_tokens = 0
        chunk_index = 0
        
        # Add title context to first chunk if provided
        title_context = f"# {title}\n\n" if title else ""
        title_tokens = self.count_tokens(title_context)
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            section_tokens = self.count_tokens(section)
            
            # If section alone exceeds max tokens, split it further
            if section_tokens > self.max_chunk_tokens - title_tokens:
                # Save current chunk if it has content
                if current_chunk.strip():
                    chunk_content = title_context + current_chunk if chunk_index == 0 else current_chunk
                    chunks.append({
                        'index': chunk_index,
                        'content': chunk_content.strip(),
                        'token_count': self.count_tokens(chunk_content)
                    })
                    chunk_index += 1
                    current_chunk = ""
                    current_tokens = 0
                
                # Split large section by sentences or lines
                subsections = self._split_large_section(section, self.max_chunk_tokens - title_tokens)
                for subsection in subsections:
                    chunk_content = title_context + subsection if chunk_index == 0 else subsection
                    chunks.append({
                        'index': chunk_index,
                        'content': chunk_content.strip(),
                        'token_count': self.count_tokens(chunk_content)
                    })
                    chunk_index += 1
                    title_context = ""  # Only add title to first chunk
                
            else:
                # Check if adding this section would exceed chunk size
                potential_tokens = current_tokens + section_tokens + title_tokens
                
                if potential_tokens > self.max_chunk_tokens and current_chunk.strip():
                    # Save current chunk
                    chunk_content = title_context + current_chunk if chunk_index == 0 else current_chunk
                    chunks.append({
                        'index': chunk_index,
                        'content': chunk_content.strip(),
                        'token_count': self.count_tokens(chunk_content)
                    })
                    chunk_index += 1
                    
                    # Start new chunk with overlap
                    overlap_content = self._get_overlap(current_chunk)
                    current_chunk = overlap_content + "\n\n" + section if overlap_content else section
                    current_tokens = self.count_tokens(current_chunk)
                    title_context = ""  # Only add title to first chunk
                else:
                    # Add section to current chunk
                    if current_chunk:
                        current_chunk += "\n\n" + section
                    else:
                        current_chunk = section
                    current_tokens = potential_tokens
        
        # Add final chunk if it has content
        if current_chunk.strip():
            chunk_content = title_context + current_chunk if chunk_index == 0 else current_chunk
            if self.count_tokens(chunk_content) >= self.min_chunk_tokens:
                chunks.append({
                    'index': chunk_index,
                    'content': chunk_content.strip(),
                    'token_count': self.count_tokens(chunk_content)
                })
        
        return chunks
    
    def _split_large_section(self, section: str, max_tokens: int) -> List[str]:
        """Split a large section by sentences or lines."""
        # Try splitting by sentences first
        sentences = re.split(r'(?<=[.!?])\s+', section)
        
        subsections = []
        current_subsection = ""
        
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            
            if sentence_tokens > max_tokens:
                # If single sentence is too long, split by lines or words
                if current_subsection:
                    subsections.append(current_subsection.strip())
                    current_subsection = ""
                
                # Split very long sentence by lines
                lines = sentence.split('\n')
                for line in lines:
                    if self.count_tokens(current_subsection + line) > max_tokens:
                        if current_subsection:
                            subsections.append(current_subsection.strip())
                        current_subsection = line
                    else:
                        current_subsection = current_subsection + "\n" + line if current_subsection else line
            else:
                if self.count_tokens(current_subsection + " " + sentence) > max_tokens:
                    subsections.append(current_subsection.strip())
                    current_subsection = sentence
                else:
                    current_subsection = current_subsection + " " + sentence if current_subsection else sentence
        
        if current_subsection.strip():
            subsections.append(current_subsection.strip())
        
        return subsections
    
    def _get_overlap(self, text: str) -> str:
        """Get overlap content from the end of current chunk."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        overlap = ""
        overlap_tokens = 0
        
        # Take sentences from the end until we reach overlap limit
        for sentence in reversed(sentences[-3:]):  # Max 3 sentences for overlap
            sentence_tokens = self.count_tokens(sentence)
            if overlap_tokens + sentence_tokens <= self.chunk_overlap_tokens:
                overlap = sentence + " " + overlap if overlap else sentence
                overlap_tokens += sentence_tokens
            else:
                break
        
        return overlap.strip()
    
    async def process_document(self, 
                             database_id: str,
                             page_data: Dict[str, Any],
                             content: str,
                             title: str,
                             multimedia_refs: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a single document: chunk it, generate embeddings, extract metadata, and store.
        Single database model - no workspace concept.
        """
        notion_page_id = page_data.get("id")
        notion_database_id = page_data.get("parent", {}).get("database_id", database_id)
        multimedia_refs = multimedia_refs or []
        
        self.logger.info(f"Processing document {notion_page_id} from database {database_id}")
        
        # Extract metadata using schema manager
        try:
            extracted_metadata_records = await self.schema_manager.extract_document_metadata(
                notion_page_id, page_data, database_id
            )
        except Exception as e:
            self.logger.warning(f"Failed to extract metadata for {notion_page_id}: {str(e)}")
            extracted_metadata_records = []
        
        # Check if document is small enough to store as single document
        content_tokens = self.count_tokens(content)
        title_tokens = self.count_tokens(title)
        
        # Determine if we need chunking based on embedding token limits
        limits_config = self.model_config.get_limits_config()
        max_embedding_tokens = limits_config.max_embedding_tokens
        full_content_for_embedding = f"{title}\n{content}"
        full_content_tokens = self.count_tokens(full_content_for_embedding)
        
        # Generate title embedding (always safe)
        title_embedding_response = await self.openai_service.generate_embedding(title)
        
        # Generate content embedding (use summary for large documents)
        content_embedding_response = None
        summary_embedding = None
        document_summary = None
        
        if full_content_tokens <= max_embedding_tokens:
            # Small document: use full content for embedding
            content_embedding_response = await self.openai_service.generate_embedding(full_content_for_embedding)
        else:
            # Large document: generate summary and use for embedding
            self.logger.info(f"Document {notion_page_id} is large ({full_content_tokens} tokens), generating summary for embedding")
            
            try:
                document_summary = await self.openai_service.generate_document_summary(title, content)
                self.logger.info(f"Generated summary for {notion_page_id}: {len(document_summary)} chars")
                
                # Use summary for both content and summary embeddings
                summary_for_embedding = f"{title}\n{document_summary}"
                content_embedding_response = await self.openai_service.generate_embedding(summary_for_embedding)
                summary_embedding = content_embedding_response.embedding  # Same embedding for both
                
            except Exception as e:
                self.logger.error(f"Failed to generate summary for {notion_page_id}: {str(e)}")
                # Fallback: truncate content for embedding
                truncated_content = content[:4000]  # Conservative truncation
                fallback_content = f"{title}\n{truncated_content}..."
                content_embedding_response = await self.openai_service.generate_embedding(fallback_content)
        
        # Prepare extracted metadata as JSONB
        extracted_metadata = {}
        for metadata_record in extracted_metadata_records:
            field_name = metadata_record['field_name']
            raw_value = metadata_record['raw_value']
            extracted_metadata[field_name] = raw_value
        
        # Determine content type
        content_type = self._determine_content_type(title, content, page_data)
        
        # Create main document record (no workspace_id)
        document_id = str(uuid.uuid4())
        document_data = {
            'id': document_id,
            'database_id': database_id,
            'notion_page_id': notion_page_id,
            'notion_database_id': notion_database_id,
            'title': title,
            'content': content,
            'title_embedding': title_embedding_response.embedding,
            'content_embedding': content_embedding_response.embedding,
            'summary_embedding': summary_embedding,
            'page_url': f"https://www.notion.so/{notion_page_id.replace('-', '')}",
            'parent_page_id': page_data.get('parent', {}).get('page_id'),
            'notion_created_time': page_data.get('created_time'),
            'notion_last_edited_time': page_data.get('last_edited_time'),
            'content_type': content_type,
            'content_length': len(content),
            'token_count': content_tokens,
            'notion_properties': page_data.get('properties', {}),
            'extracted_metadata': extracted_metadata,
            'has_multimedia': len(multimedia_refs) > 0,
            'multimedia_refs': multimedia_refs,
            'processing_status': 'processing'
        }
        
        # Add summary to document_data if generated
        if document_summary:
            document_data['document_summary'] = document_summary
            document_data['extracted_metadata']['ai_generated_summary'] = document_summary
        
        if content_tokens <= self.max_chunk_tokens:
            # Store as single document without chunking
            document_data.update({
                'is_chunked': False,
                'chunk_count': 0,
                'processing_status': 'completed'
            })
            
            # Store document
            self._store_document(document_data)
            
            # Store metadata records
            for metadata_record in extracted_metadata_records:
                metadata_record['document_id'] = document_id
                self._store_document_metadata(metadata_record)
            
            self.logger.info(f"Stored document {notion_page_id} as single document")
            return {'document_id': document_id, 'chunks_created': 0}
        
        else:
            # Chunk the document
            chunks = self.chunk_text(content, title)
            
            if not chunks:
                raise ValueError(f"No valid chunks generated for page {notion_page_id}")
            
            document_data.update({
                'is_chunked': True,
                'chunk_count': len(chunks),
                'processing_status': 'completed'
            })
            
            # Store main document
            self._store_document(document_data)
            
            # Store metadata records
            for metadata_record in extracted_metadata_records:
                metadata_record['document_id'] = document_id
                self._store_document_metadata(metadata_record)
            
            # Generate and store chunks
            await self._store_document_chunks(document_id, chunks, title)
            
            self.logger.info(f"Stored document {notion_page_id} with {len(chunks)} chunks")
            return {'document_id': document_id, 'chunks_created': len(chunks)}
    
    def _determine_content_type(self, title: str, content: str, page_data: Dict[str, Any]) -> str:
        """Determine the content type based on title, content, and properties."""
        title_lower = title.lower()
        content_lower = content.lower()
        
        # Check for meeting notes
        if any(keyword in title_lower for keyword in ['meeting', 'standup', 'sync', 'call']):
            return 'meeting'
        
        # Check for project documents
        if any(keyword in title_lower for keyword in ['project', 'initiative', 'roadmap']):
            return 'project'
        
        # Check for documentation
        if any(keyword in title_lower for keyword in ['doc', 'guide', 'manual', 'howto', 'readme']):
            return 'documentation'
        
        # Check for notes
        if any(keyword in title_lower for keyword in ['note', 'notes', 'journal', 'diary']):
            return 'note'
        
        # Check for bookmarks/references
        if any(keyword in content_lower for keyword in ['http', 'https', 'www.']):
            return 'bookmark'
        
        # Default
        return 'document'
    
    def _store_document(self, document_data: Dict[str, Any]) -> None:
        """Store document in the database."""
        try:
            self.db.client.table('documents').upsert(document_data).execute()
        except Exception as e:
            self.logger.error(f"Failed to store document {document_data['notion_page_id']}: {str(e)}")
            raise
    
    def _store_document_metadata(self, metadata_record: Dict[str, Any]) -> None:
        """Store document metadata record."""
        try:
            self.db.client.table('document_metadata').upsert(metadata_record).execute()
        except Exception as e:
            self.logger.error(f"Failed to store metadata for document {metadata_record['document_id']}: {str(e)}")
            raise
    
    async def _store_document_chunks(self, document_id: str, chunks: List[Dict[str, Any]], title: str) -> None:
        """Generate embeddings and store document chunks."""
        chunk_data_list = []
        
        for chunk in chunks:
            try:
                embedding_response = await self.openai_service.generate_embedding(chunk['content'])
                
                chunk_data = {
                    'id': str(uuid.uuid4()),
                    'document_id': document_id,
                    'chunk_index': chunk['index'],
                    'content': chunk['content'],
                    'embedding': embedding_response.embedding,
                    'token_count': chunk['token_count'],
                    'content_type': 'text'  # Default for now
                }
                chunk_data_list.append(chunk_data)
                
                # Add small delay to avoid rate limits
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Failed to process chunk {chunk['index']} for document {document_id}: {str(e)}")
                continue
        
        # Store chunks in database
        if chunk_data_list:
            try:
                self.db.client.table('document_chunks').upsert(chunk_data_list).execute()
            except Exception as e:
                self.logger.error(f"Failed to store chunks for document {document_id}: {str(e)}")
                raise
    
    async def update_document(self, 
                             database_id: str,
                             page_data: Dict[str, Any],
                             content: str,
                             title: str,
                             multimedia_refs: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Update an existing document (delete old chunks and create new ones).
        Single database model - no workspace concept.
        """
        notion_page_id = page_data.get("id")
        
        try:
            # Delete existing document and related data
            self._delete_document_cascade(notion_page_id)
            
            # Process as new document
            return await self.process_document(database_id, page_data, content, title, multimedia_refs)
        except Exception as e:
            self.logger.error(f"Failed to update document {notion_page_id}: {str(e)}")
            raise
    
    def _delete_document_cascade(self, notion_page_id: str) -> None:
        """Delete document and all related records."""
        try:
            # Get document ID first
            response = self.db.client.table('documents').select('id').eq('notion_page_id', notion_page_id).execute()
            
            if response.data:
                document_id = response.data[0]['id']
                
                # Delete chunks (cascades automatically due to foreign key)
                self.db.client.table('document_chunks').delete().eq('document_id', document_id).execute()
                
                # Delete metadata (cascades automatically due to foreign key)
                self.db.client.table('document_metadata').delete().eq('document_id', document_id).execute()
                
                # Delete document
                self.db.client.table('documents').delete().eq('id', document_id).execute()
                
                self.logger.info(f"Deleted document and related data for {notion_page_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to delete document {notion_page_id}: {str(e)}")
            raise
    
    async def process_database_pages(self, 
                                   database_id: str,
                                   notion_service,
                                   batch_size: int = 10) -> Dict[str, Any]:
        """
        Process all pages from a specific Notion database.
        Single database model - no workspace concept.
        """
        try:
            self.logger.info(f"Processing database {database_id}")
            
            # Analyze database schema first
            try:
                schema_record = await self.schema_manager.analyze_database_schema(
                    database_id, notion_service
                )
                self.logger.info(f"Schema analyzed for database {database_id}")
            except Exception as e:
                self.logger.warning(f"Failed to analyze schema for {database_id}: {str(e)}")
                # Continue processing without schema analysis
            
            # Get all pages from database
            pages = await notion_service.get_database_pages(database_id)
            
            results = {
                'database_id': database_id,
                'total_pages': len(pages),
                'processed_pages': 0,
                'failed_pages': 0,
                'errors': []
            }
            
            # Process pages in batches
            for i in range(0, len(pages), batch_size):
                batch = pages[i:i + batch_size]
                
                for page in batch:
                    try:
                        # Skip archived pages
                        if page.get('archived', False):
                            continue
                        
                        # Extract page content and multimedia references
                        content, multimedia_refs = await notion_service.get_page_content_with_multimedia(page['id'])
                        title = notion_service.extract_title_from_page(page)
                        
                        # Process the document
                        result = await self.process_document(
                            database_id, page, content, title, multimedia_refs
                        )
                        results['processed_pages'] += 1
                        
                        self.logger.debug(f"Processed page {page['id']}: {result}")
                        
                    except Exception as e:
                        results['failed_pages'] += 1
                        error_info = {
                            'page_id': page.get('id'),
                            'title': notion_service.extract_title_from_page(page),
                            'error': str(e)
                        }
                        results['errors'].append(error_info)
                        self.logger.error(f"Failed to process page {page.get('id')}: {str(e)}")
                
                # Add delay between batches to respect rate limits
                await asyncio.sleep(1)
            
            return results
        
        except Exception as e:
            self.logger.error(f"Failed to process database {database_id}: {str(e)}")
            raise Exception(f"Failed to process database pages: {str(e)}")
    
    async def process_databases(self, 
                              database_configs: List[Dict[str, Any]],
                              notion_service,
                              batch_size: int = 10) -> Dict[str, Any]:
        """
        Process multiple databases.
        Single database model - no workspace concept.
        """
        try:
            overall_results = {
                'total_databases': len(database_configs),
                'processed_databases': 0,
                'failed_databases': 0,
                'database_results': [],
                'errors': []
            }
            
            for config in database_configs:
                database_id = config['database_id']
                database_name = config.get('name', 'Unknown')
                
                try:
                    self.logger.info(f"Processing database: {database_name} ({database_id})")
                    
                    # Process this database
                    sync_settings = config.get('sync_settings', {})
                    db_batch_size = sync_settings.get('batch_size', batch_size)
                    
                    db_results = await self.process_database_pages(
                        database_id, notion_service, db_batch_size
                    )
                    
                    overall_results['database_results'].append({
                        'database_name': database_name,
                        'database_id': database_id,
                        'results': db_results
                    })
                    overall_results['processed_databases'] += 1
                    
                    # Add delay between databases
                    rate_limit_delay = sync_settings.get('rate_limit_delay', 1.0)
                    await asyncio.sleep(rate_limit_delay)
                    
                except Exception as e:
                    overall_results['failed_databases'] += 1
                    error_info = {
                        'database_name': database_name,
                        'database_id': database_id,
                        'error': str(e)
                    }
                    overall_results['errors'].append(error_info)
                    self.logger.error(f"Failed to process database {database_name}: {str(e)}")
            
            return overall_results
        
        except Exception as e:
            self.logger.error(f"Failed to process databases: {str(e)}")
            raise

def get_document_processor(openai_service: OpenAIService, db: Database) -> DocumentProcessor:
    """Factory function to create DocumentProcessor instance."""
    return DocumentProcessor(openai_service, db)