"""
Contextual Chunker - Anthropic-style Contextual Retrieval

Implements contextual retrieval by generating contextual information for each chunk,
explaining how it relates to the overall document and what specific topics it covers.
"""

import asyncio
from typing import List, Dict, Any
import logging
from ingestion.services.openai_service import OpenAIService
from ingestion.services.chunking_strategies import ArticleChunkingStrategy

class ContextualChunker:
    """Anthropic-style contextual retrieval chunking."""
    
    def __init__(self, openai_service: OpenAIService, max_tokens: int = 1000, overlap_tokens: int = 100):
        self.openai_service = openai_service
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.logger = logging.getLogger(__name__)
        
        # Use ArticleChunkingStrategy as the universal chunking strategy
        self.chunking_strategy = ArticleChunkingStrategy(max_tokens, overlap_tokens)
    
    async def chunk_with_context(self, content: str, title: str, page_data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Enhanced chunking with contextual summaries and positional linking.
        
        Args:
            content: Document content to chunk
            title: Document title
            page_data: Notion page metadata
            
        Returns:
            List of enhanced chunks with contextual information
        """
        page_data = page_data or {}
        
        try:
            self.logger.info(f"Processing document with ArticleChunkingStrategy")
            
            # Generate base chunks using ArticleChunkingStrategy
            base_chunks = await self.chunking_strategy.create_semantic_chunks(content, title)
            
            if not base_chunks:
                self.logger.warning(f"No chunks generated for document: {title}")
                return []
            
            # Generate document summary for context generation
            document_summary = await self._generate_document_summary(title, content)
            
            # Generate contextual information for each chunk
            contextual_chunks = await self._add_contextual_information(
                base_chunks, title, document_summary
            )
            
            # Link adjacent chunks for context enrichment
            linked_chunks = self._link_adjacent_chunks(contextual_chunks)
            
            self.logger.info(f"Generated {len(linked_chunks)} contextual chunks for '{title}'")
            return linked_chunks
            
        except Exception as e:
            self.logger.error(f"Error in contextual chunking for '{title}': {str(e)}")
            raise
    
    async def _generate_document_summary(self, title: str, content: str) -> str:
        """Generate a concise summary of the entire document."""
        try:
            # Truncate content if too long for summarization
            max_content_length = 4000  # Conservative limit for summarization
            if len(content) > max_content_length:
                content_for_summary = content[:max_content_length] + "..."
            else:
                content_for_summary = content
            
            summary_prompt = f"""
Provide a concise 2-3 sentence summary of this document that captures its main purpose and key topics:

Title: {title}

Content: {content_for_summary}

Summary:"""

            response = await self.openai_service.generate_chat_response(
                messages=[{"role": "user", "content": summary_prompt}]
            )
            
            return response.content.strip()
            
        except Exception as e:
            self.logger.warning(f"Failed to generate document summary: {str(e)}")
            return f"Document about {title}"
    
    async def _add_contextual_information(self, chunks: List[Dict[str, Any]], title: str, 
                                        document_summary: str) -> List[Dict[str, Any]]:
        """Add contextual information to each chunk."""
        contextual_chunks = []
        
        # Process chunks in batches to avoid rate limits
        batch_size = 3
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            # Generate contextual information for this batch
            batch_tasks = []
            for chunk in batch:
                task = self._generate_chunk_contextual_info(
                    chunk, title, document_summary
                )
                batch_tasks.append(task)
            
            # Execute batch concurrently
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process results
            for chunk, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    self.logger.error(f"Failed to generate context for chunk {chunk['index']}: {str(result)}")
                    # Fallback to basic chunk without enhanced context
                    contextual_chunks.append({
                        **chunk,
                        'chunk_context': f"This section is part of the document '{title}'.",
                        'chunk_summary': f"Content from {title}",
                        'contextual_content': chunk['content']
                    })
                else:
                    contextual_chunks.append(result)
            
            # Small delay between batches to respect rate limits
            if i + batch_size < len(chunks):
                await asyncio.sleep(0.5)
        
        return contextual_chunks
    
    async def _generate_chunk_contextual_info(self, chunk: Dict[str, Any], title: str, 
                                            document_summary: str) -> Dict[str, Any]:
        """Generate Anthropic-style contextual information for a single chunk."""
        try:
            # 1. Generate chunk context (how this chunk relates to the document)
            chunk_context = await self._generate_chunk_context(
                chunk, title, document_summary
            )
            
            # 2. Generate chunk summary (what this chunk is about)
            chunk_summary = await self._generate_chunk_summary(chunk['content'])
            
            # 3. Create contextual content (context + original content)
            contextual_content = f"{chunk_context}\n\n{chunk['content']}"
            
            return {
                **chunk,
                'chunk_context': chunk_context,
                'chunk_summary': chunk_summary,
                'contextual_content': contextual_content,
                'content_type': 'content' # Universal content type
            }
            
        except Exception as e:
            self.logger.error(f"Error generating contextual info for chunk {chunk['index']}: {str(e)}")
            # Return chunk with basic context
            return {
                **chunk,
                'chunk_context': f"This section discusses content related to {title}.",
                'chunk_summary': "Document content",
                'contextual_content': chunk['content']
            }
    
    async def _generate_chunk_context(self, chunk: Dict[str, Any], title: str, 
                                     document_summary: str) -> str:
        """Generate contextual description of how this chunk relates to the document."""
        
        # Build context prompt based on available information
        section_info = ""
        if chunk.get('section_title'):
            section_info = f"Section: {chunk['section_title']}\n"
        
        hierarchy_info = ""
        if chunk.get('hierarchy'):
            hierarchy_path = " > ".join(chunk['hierarchy'])
            hierarchy_info = f"Document path: {hierarchy_path}\n"
        
        # Universal context prompt for all content types
        context_prompt = f"""Document: {title}
{hierarchy_info}{section_info}Document Summary: {document_summary}

Generate a brief 1-2 sentence context explaining:
1. How this content relates to the overall document
2. What specific aspect or topic this section covers

Chunk Content: {chunk['content'][:500]}...

Context:"""
        
        try:
            response = await self.openai_service.generate_chat_response(
                messages=[{"role": "user", "content": context_prompt}]
            )
            
            return response.content.strip()
            
        except Exception as e:
            self.logger.warning(f"Failed to generate chunk context: {str(e)}")
            return f"This section is part of '{title}' and discusses {chunk.get('section_title', 'related content')}."
    
    async def _generate_chunk_summary(self, chunk_content: str) -> str:
        """Generate a concise summary of what the chunk is about."""
        
        # Truncate content for summary generation
        content_for_summary = chunk_content[:800] if len(chunk_content) > 800 else chunk_content
        
        summary_prompt = f"""Summarize the main point or key idea of this text in one clear sentence:

{content_for_summary}

Summary:"""
        
        try:
            response = await self.openai_service.generate_chat_response(
                messages=[{"role": "user", "content": summary_prompt}]
            )
            
            return response.content.strip()
            
        except Exception as e:
            self.logger.warning(f"Failed to generate chunk summary: {str(e)}")
            # Fallback: use first sentence or line
            first_line = chunk_content.split('\n')[0].strip()
            if len(first_line) > 100:
                first_line = first_line[:100] + "..."
            return first_line or "Document content"
    
    def _link_adjacent_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add positional linking between adjacent chunks for context enrichment."""
        
        for i, chunk in enumerate(chunks):
            # Add references to adjacent chunks
            chunk['prev_chunk_ref'] = chunks[i-1]['temp_id'] if i > 0 else None
            chunk['next_chunk_ref'] = chunks[i+1]['temp_id'] if i < len(chunks)-1 else None
            
            # Add positional metadata
            chunk['chunk_position'] = {
                'index': i,
                'total_chunks': len(chunks),
                'is_first': i == 0,
                'is_last': i == len(chunks) - 1,
                'relative_position': round(i / max(len(chunks) - 1, 1), 2)  # 0.0 to 1.0
            }
        
        return chunks
    
    async def generate_chunk_embeddings(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate both content and contextual embeddings for chunks."""
        
        for chunk in chunks:
            try:
                # Generate content embedding (original approach)
                content_embedding = await self.openai_service.generate_embedding(chunk['content'])
                chunk['content_embedding_response'] = content_embedding
                
                # Generate contextual embedding (enhanced approach)
                contextual_embedding = await self.openai_service.generate_embedding(chunk['contextual_content'])
                chunk['contextual_embedding_response'] = contextual_embedding
                
                # Small delay to respect rate limits
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Failed to generate embeddings for chunk {chunk['index']}: {str(e)}")
                # Continue without embeddings for this chunk
                continue
        
        return chunks