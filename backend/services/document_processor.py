from typing import List, Dict, Any, Tuple, Optional
import re
import tiktoken
from services.openai_service import OpenAIService
from database import Database
import asyncio
from datetime import datetime
import uuid

class DocumentProcessor:
    def __init__(self, openai_service: OpenAIService, db: Database):
        self.openai_service = openai_service
        self.db = db
        self.encoding = tiktoken.get_encoding("cl100k_base")  # For text-embedding-3-small
        
        # Chunking parameters
        self.max_chunk_tokens = 1000  # Leave room for metadata
        self.chunk_overlap_tokens = 100
        self.min_chunk_tokens = 50
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self.encoding.encode(text))
    
    def chunk_text(self, text: str, title: str = "") -> List[Dict[str, Any]]:
        """
        Split text into chunks with overlap, preserving semantic boundaries.
        """
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
                             workspace_id: str,
                             page_data: Dict[str, Any],
                             content: str,
                             title: str) -> Dict[str, Any]:
        """
        Process a single document: chunk it, generate embeddings, and store.
        """
        notion_page_id = page_data.get("id")
        
        # Check if document is small enough to store as single document
        content_tokens = self.count_tokens(content)
        
        if content_tokens <= self.max_chunk_tokens:
            # Store as single document
            embedding_response = await self.openai_service.generate_embedding(f"{title}\n{content}")
            
            document_data = {
                'id': str(uuid.uuid4()),
                'workspace_id': workspace_id,
                'notion_page_id': notion_page_id,
                'title': title,
                'content': content,
                'embedding': embedding_response.embedding,
                'metadata': {
                    'token_count': content_tokens,
                    'chunk_count': 1,
                    'last_edited_time': page_data.get('last_edited_time'),
                    'properties': page_data.get('properties', {}),
                },
                'last_edited_time': page_data.get('last_edited_time'),
                'page_url': f"https://www.notion.so/{notion_page_id.replace('-', '')}",
                'parent_page_id': page_data.get('parent', {}).get('page_id'),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            return await self.db.upsert_document(document_data)
        
        else:
            # Chunk the document
            chunks = self.chunk_text(content, title)
            
            if not chunks:
                raise ValueError(f"No valid chunks generated for page {notion_page_id}")
            
            # Create main document record
            document_data = {
                'id': str(uuid.uuid4()),
                'workspace_id': workspace_id,
                'notion_page_id': notion_page_id,
                'title': title,
                'content': content[:2000] + "..." if len(content) > 2000 else content,  # Truncated preview
                'embedding': None,  # No embedding for chunked documents
                'metadata': {
                    'token_count': content_tokens,
                    'chunk_count': len(chunks),
                    'last_edited_time': page_data.get('last_edited_time'),
                    'properties': page_data.get('properties', {}),
                    'is_chunked': True
                },
                'last_edited_time': page_data.get('last_edited_time'),
                'page_url': f"https://www.notion.so/{notion_page_id.replace('-', '')}",
                'parent_page_id': page_data.get('parent', {}).get('page_id'),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            document_result = await self.db.upsert_document(document_data)
            document_id = document_result[0]['id']
            
            # Generate embeddings for chunks in batches
            chunk_data_list = []
            
            for chunk in chunks:
                embedding_response = await self.openai_service.generate_embedding(chunk['content'])
                
                chunk_data = {
                    'id': str(uuid.uuid4()),
                    'document_id': document_id,
                    'chunk_index': chunk['index'],
                    'content': chunk['content'],
                    'embedding': embedding_response.embedding,
                    'token_count': chunk['token_count']
                }
                chunk_data_list.append(chunk_data)
                
                # Add small delay to avoid rate limits
                await asyncio.sleep(0.1)
            
            # Store chunks in database
            await self.db.upsert_document_chunks(chunk_data_list)
            
            return document_result
    
    async def update_document(self, 
                             workspace_id: str,
                             page_data: Dict[str, Any],
                             content: str,
                             title: str) -> Dict[str, Any]:
        """
        Update an existing document (delete old chunks and create new ones).
        """
        notion_page_id = page_data.get("id")
        
        # Delete existing document and chunks
        await self.db.delete_document(notion_page_id)
        
        # Process as new document
        return await self.process_document(workspace_id, page_data, content, title)
    
    async def process_workspace_pages(self, 
                                    workspace_id: str,
                                    access_token: str,
                                    batch_size: int = 10) -> Dict[str, Any]:
        """
        Process all pages in a workspace with batching for rate limiting.
        """
        from services.notion_service import NotionService
        notion_service = NotionService(access_token)
        
        try:
            # Get all pages from workspace
            pages = await notion_service.search_pages()
            
            results = {
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
                        
                        # Extract page content
                        content = await notion_service.get_page_content(page['id'])
                        title = notion_service.extract_title_from_page(page)
                        
                        # Process the document
                        await self.process_document(workspace_id, page, content, title)
                        results['processed_pages'] += 1
                        
                    except Exception as e:
                        results['failed_pages'] += 1
                        results['errors'].append({
                            'page_id': page.get('id'),
                            'title': notion_service.extract_title_from_page(page),
                            'error': str(e)
                        })
                
                # Add delay between batches to respect rate limits
                await asyncio.sleep(1)
            
            # Update workspace sync timestamp
            await self.db.update_workspace_sync_time(workspace_id)
            
            return results
        
        except Exception as e:
            raise Exception(f"Failed to process workspace pages: {str(e)}")

def get_document_processor(openai_service: OpenAIService, db: Database) -> DocumentProcessor:
    """Factory function to create DocumentProcessor instance."""
    return DocumentProcessor(openai_service, db)