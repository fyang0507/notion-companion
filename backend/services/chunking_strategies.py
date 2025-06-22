"""
Content-Aware Chunking Strategies

Implements different chunking strategies optimized for specific content types:
- Articles: Respects hierarchical structure and logical flow
- Reading Notes: Groups related notes and preserves context
- Documentation: Maintains procedural steps and reference structure
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

class ReadingNotesChunkingStrategy(ChunkingStrategy):
    """Chunking strategy optimized for reading notes and highlights."""
    
    async def create_semantic_chunks(self, content: str, title: str) -> List[Dict[str, Any]]:
        """Create chunks optimized for note-taking patterns."""
        self.logger.info("Using reading notes chunking strategy")
        
        # 1. Identify note structures (bullet points, numbered lists, highlights)
        note_blocks = self._parse_note_structure(content)
        
        # 2. Group related notes into semantic chunks
        chunks = self._group_notes_semantically(note_blocks, title)
        
        return chunks
    
    def _parse_note_structure(self, content: str) -> List[Dict[str, Any]]:
        """Parse notes into structured blocks."""
        blocks = []
        lines = content.split('\n')
        current_block = {
            'type': 'paragraph',
            'content': '',
            'indent_level': 0,
            'line_number': 0
        }
        
        for line_num, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            
            # Detect different note patterns
            list_match = re.match(r'^(\s*)[-*+]\s+(.+)$', line)
            number_match = re.match(r'^(\s*)\d+\.\s+(.+)$', line)
            quote_match = re.match(r'^(\s*)>\s+(.+)$', line)
            header_match = re.match(r'^(#+)\s+(.+)$', stripped)
            
            if header_match:
                # Save previous block
                if current_block['content'].strip():
                    blocks.append(current_block)
                
                # Create header block
                level = len(header_match.group(1))
                current_block = {
                    'type': 'header',
                    'content': header_match.group(2),
                    'indent_level': 0,
                    'header_level': level,
                    'line_number': line_num
                }
                
            elif list_match or number_match:
                # Save previous block
                if current_block['content'].strip() and current_block['type'] != 'list_item':
                    blocks.append(current_block)
                
                # Parse list item
                if list_match:
                    indent = len(list_match.group(1))
                    content = list_match.group(2)
                else:
                    indent = len(number_match.group(1))
                    content = number_match.group(2)
                
                current_block = {
                    'type': 'list_item',
                    'content': content,
                    'indent_level': indent // 2,  # Assume 2-space indents
                    'original_line': line,
                    'line_number': line_num
                }
                
            elif quote_match:
                # Save previous block
                if current_block['content'].strip() and current_block['type'] != 'quote':
                    blocks.append(current_block)
                
                # Parse quote
                indent = len(quote_match.group(1))
                content = quote_match.group(2)
                
                current_block = {
                    'type': 'quote',
                    'content': content,
                    'indent_level': indent // 2,
                    'line_number': line_num
                }
                
            else:
                # Regular paragraph line
                if current_block['type'] not in ['paragraph']:
                    blocks.append(current_block)
                    current_block = {
                        'type': 'paragraph',
                        'content': '',
                        'indent_level': 0,
                        'line_number': line_num
                    }
                
                current_block['content'] += line + '\n'
        
        # Add final block
        if current_block['content'].strip():
            blocks.append(current_block)
        
        return blocks
    
    def _group_notes_semantically(self, blocks: List[Dict[str, Any]], title: str) -> List[Dict[str, Any]]:
        """Group note blocks into semantic chunks."""
        chunks = []
        current_group = []
        current_tokens = 0
        
        # Add title context
        title_context = f"# {title}\n\n"
        title_tokens = self.count_tokens(title_context)
        
        for block in blocks:
            block_tokens = self.count_tokens(block['content'])
            
            # Check if this block starts a new semantic group
            should_start_new_chunk = (
                current_tokens + block_tokens > self.max_tokens or
                (block['type'] == 'header' and current_group) or
                self._is_semantic_boundary(block, current_group)
            )
            
            if should_start_new_chunk and current_group:
                # Create chunk from current group
                chunk_content = self._combine_blocks_to_content(current_group, title_context)
                chunks.append(self._create_chunk_with_metadata(
                    chunk_content,
                    len(chunks),
                    {
                        'title': self._extract_group_title(current_group),
                        'chunk_type': self._determine_group_type(current_group)
                    }
                ))
                
                # Start new group
                current_group = [block]
                current_tokens = title_tokens + block_tokens
            else:
                # Add to current group
                current_group.append(block)
                current_tokens += block_tokens
        
        # Add final chunk
        if current_group:
            chunk_content = self._combine_blocks_to_content(current_group, title_context)
            chunks.append(self._create_chunk_with_metadata(
                chunk_content,
                len(chunks),
                {
                    'title': self._extract_group_title(current_group),
                    'chunk_type': self._determine_group_type(current_group)
                }
            ))
        
        return chunks
    
    def _is_semantic_boundary(self, block: Dict[str, Any], current_group: List[Dict[str, Any]]) -> bool:
        """Determine if this block represents a semantic boundary."""
        if not current_group:
            return False
        
        # Headers always start new semantic groups
        if block['type'] == 'header':
            return True
        
        # Quotes often represent separate thoughts
        if block['type'] == 'quote' and current_group[-1]['type'] != 'quote':
            return True
        
        # Change in list indentation level
        if (block['type'] == 'list_item' and 
            current_group[-1]['type'] == 'list_item' and
            abs(block['indent_level'] - current_group[-1]['indent_level']) > 1):
            return True
        
        return False
    
    def _combine_blocks_to_content(self, blocks: List[Dict[str, Any]], title_context: str) -> str:
        """Combine note blocks into readable content."""
        content_parts = [title_context.strip()]
        
        for block in blocks:
            if block['type'] == 'header':
                content_parts.append(f"{'#' * (block.get('header_level', 2) + 1)} {block['content']}")
            elif block['type'] == 'list_item':
                indent = '  ' * block['indent_level']
                content_parts.append(f"{indent}- {block['content']}")
            elif block['type'] == 'quote':
                indent = '  ' * block['indent_level']
                content_parts.append(f"{indent}> {block['content']}")
            else:
                content_parts.append(block['content'].strip())
        
        return '\n\n'.join(content_parts)
    
    def _extract_group_title(self, blocks: List[Dict[str, Any]]) -> str:
        """Extract a title for the block group."""
        # Look for header blocks first
        for block in blocks:
            if block['type'] == 'header':
                return block['content']
        
        # Use first list item or quote as title
        for block in blocks:
            if block['type'] in ['list_item', 'quote']:
                title = block['content'][:50]  # Truncate long titles
                if len(block['content']) > 50:
                    title += "..."
                return title
        
        # Use first paragraph
        for block in blocks:
            if block['type'] == 'paragraph':
                lines = block['content'].strip().split('\n')
                return lines[0][:50] + ("..." if len(lines[0]) > 50 else "")
        
        return "Note Group"
    
    def _determine_group_type(self, blocks: List[Dict[str, Any]]) -> str:
        """Determine the semantic type of the block group."""
        block_types = [block['type'] for block in blocks]
        
        if 'header' in block_types:
            return 'section'
        elif 'quote' in block_types:
            return 'highlight'
        elif 'list_item' in block_types:
            return 'notes'
        else:
            return 'content'

class DocumentationChunkingStrategy(ChunkingStrategy):
    """Chunking strategy for technical documentation."""
    
    async def create_semantic_chunks(self, content: str, title: str) -> List[Dict[str, Any]]:
        """Create chunks optimized for documentation (procedures, references)."""
        self.logger.info("Using documentation chunking strategy")
        
        # For now, use article strategy with documentation-specific tweaks
        article_strategy = ArticleChunkingStrategy(self.max_tokens, self.overlap_tokens)
        chunks = await article_strategy.create_semantic_chunks(content, title)
        
        # Add documentation-specific metadata
        for chunk in chunks:
            chunk['chunk_type'] = 'documentation'
            
            # Detect code blocks and procedures
            if '```' in chunk['content'] or '`' in chunk['content']:
                chunk['has_code'] = True
            
            # Detect step-by-step procedures
            if re.search(r'\d+\.\s', chunk['content']):
                chunk['has_procedure'] = True
        
        return chunks