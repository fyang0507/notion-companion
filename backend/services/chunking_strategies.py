"""
Chunking Strategies

Implements the ArticleChunkingStrategy for semantic text chunking that:
- Respects hierarchical structure and logical flow
- Preserves semantic boundaries with proper overlap
- Handles headers, sections, and paragraphs intelligently
"""

import re
import tiktoken
from typing import List, Dict, Any, Tuple
from abc import ABC, abstractmethod
import logging

class ChunkingStrategy(ABC):
    """Base class for content-aware chunking strategies."""
    
    def __init__(self, max_tokens: int = 1000, overlap_tokens: int = 100):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self.logger = logging.getLogger(__name__)
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self.encoding.encode(text))
    
    @abstractmethod
    async def create_semantic_chunks(self, content: str, title: str) -> List[Dict[str, Any]]:
        """Create chunks respecting content-specific semantics."""
        pass
    
    def _create_chunk_with_metadata(self, content: str, index: int, section_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a chunk with standard metadata."""
        section_info = section_info or {}
        temp_id = f"temp_chunk_{index}"
        
        return {
            'temp_id': temp_id,
            'index': index,
            'content': content.strip(),
            'token_count': self.count_tokens(content),
            'section_title': section_info.get('title', ''),
            'section_level': section_info.get('level', 0),
            'hierarchy': section_info.get('hierarchy', []),
            'chunk_type': section_info.get('chunk_type', 'content')
        }

class ArticleChunkingStrategy(ChunkingStrategy):
    """Chunking strategy optimized for articles and formal documents."""
    
    async def create_semantic_chunks(self, content: str, title: str) -> List[Dict[str, Any]]:
        """Create chunks respecting article structure."""
        self.logger.info("Using article chunking strategy")
        
        # 1. Parse document structure (headers, sections)
        sections = self._parse_article_structure(content)
        
        # 2. Create chunks that respect semantic boundaries
        chunks = []
        chunk_index = 0
        
        for section in sections:
            section_chunks = self._chunk_section(section, title, chunk_index)
            chunks.extend(section_chunks)
            chunk_index += len(section_chunks)
        
        return chunks
    
    def _parse_article_structure(self, content: str) -> List[Dict[str, Any]]:
        """Parse article into hierarchical sections."""
        sections = []
        lines = content.split('\n')
        current_section = {
            'title': '',
            'content': '',
            'level': 0,
            'hierarchy': [],
            'start_line': 0
        }
        
        header_stack = []  # Track hierarchical headers
        
        for line_num, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Detect markdown headers
            header_match = re.match(r'^(#+)\s+(.+)$', line_stripped)
            if header_match:
                # Save previous section if it has content
                if current_section['content'].strip():
                    sections.append(current_section)
                
                # Parse header
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                
                # Update header stack for hierarchy
                header_stack = header_stack[:level-1]  # Remove deeper levels
                if len(header_stack) < level:
                    header_stack.extend([None] * (level - len(header_stack)))
                header_stack[level-1] = title
                
                # Build hierarchy path
                hierarchy = [h for h in header_stack if h is not None]
                
                # Start new section
                current_section = {
                    'title': title,
                    'content': '',
                    'level': level,
                    'hierarchy': hierarchy,
                    'start_line': line_num,
                    'chunk_type': 'header' if level <= 2 else 'content'
                }
            else:
                # Add content to current section
                current_section['content'] += line + '\n'
        
        # Add final section
        if current_section['content'].strip():
            sections.append(current_section)
        
        return sections
    
    def _chunk_section(self, section: Dict[str, Any], document_title: str, start_index: int) -> List[Dict[str, Any]]:
        """Chunk a section while preserving its context."""
        content = section['content'].strip()
        if not content:
            return []
        
        # Calculate available tokens (reserve space for title context)
        title_context = f"# {document_title}\n"
        if section['title']:
            title_context += f"## {section['title']}\n"
        
        title_tokens = self.count_tokens(title_context)
        available_tokens = self.max_tokens - title_tokens
        
        # If section fits in one chunk, return it
        content_tokens = self.count_tokens(content)
        if content_tokens <= available_tokens:
            chunk_content = title_context + content
            return [self._create_chunk_with_metadata(
                chunk_content, 
                start_index,
                {
                    'title': section['title'],
                    'level': section['level'],
                    'hierarchy': section['hierarchy'],
                    'chunk_type': section.get('chunk_type', 'content')
                }
            )]
        
        # Split large section into multiple chunks
        chunks = []
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        current_chunk = ""
        current_tokens = title_tokens
        
        for para in paragraphs:
            para_tokens = self.count_tokens(para)
            
            # If paragraph alone exceeds available space, split it further
            if para_tokens > available_tokens:
                # Save current chunk if it has content
                if current_chunk.strip():
                    chunk_content = title_context + current_chunk
                    chunks.append(self._create_chunk_with_metadata(
                        chunk_content,
                        start_index + len(chunks),
                        section
                    ))
                    current_chunk = ""
                    current_tokens = title_tokens
                
                # Split large paragraph by sentences
                sentences = self._split_paragraph_by_sentences(para, available_tokens)
                for sentence_group in sentences:
                    chunk_content = title_context + sentence_group
                    chunks.append(self._create_chunk_with_metadata(
                        chunk_content,
                        start_index + len(chunks),
                        section
                    ))
            
            # Check if adding this paragraph would exceed chunk size
            elif current_tokens + para_tokens > self.max_tokens:
                # Save current chunk
                chunk_content = title_context + current_chunk
                chunks.append(self._create_chunk_with_metadata(
                    chunk_content,
                    start_index + len(chunks),
                    section
                ))
                
                # Start new chunk with overlap
                overlap_content = self._get_overlap(current_chunk)
                current_chunk = overlap_content + "\n\n" + para if overlap_content else para
                current_tokens = title_tokens + self.count_tokens(current_chunk)
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
                current_tokens += para_tokens
        
        # Add final chunk if it has content
        if current_chunk.strip():
            chunk_content = title_context + current_chunk
            chunks.append(self._create_chunk_with_metadata(
                chunk_content,
                start_index + len(chunks),
                section
            ))
        
        return chunks
    
    def _split_paragraph_by_sentences(self, paragraph: str, max_tokens: int) -> List[str]:
        """Split a large paragraph by sentences."""
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            
            if sentence_tokens > max_tokens:
                # Split very long sentence by phrases or words
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # Split by commas or semicolons
                phrases = re.split(r'[,;]\s*', sentence)
                for phrase in phrases:
                    if self.count_tokens(current_chunk + phrase) > max_tokens:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = phrase
                    else:
                        current_chunk = current_chunk + ", " + phrase if current_chunk else phrase
            else:
                if self.count_tokens(current_chunk + " " + sentence) > max_tokens:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    current_chunk = current_chunk + " " + sentence if current_chunk else sentence
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _get_overlap(self, text: str) -> str:
        """Get overlap content from the end of current chunk."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        overlap = ""
        overlap_tokens = 0
        
        # Take sentences from the end until we reach overlap limit
        for sentence in reversed(sentences[-3:]):  # Max 3 sentences for overlap
            sentence_tokens = self.count_tokens(sentence)
            if overlap_tokens + sentence_tokens <= self.overlap_tokens:
                overlap = sentence + " " + overlap if overlap else sentence
                overlap_tokens += sentence_tokens
            else:
                break
        
        return overlap.strip()
