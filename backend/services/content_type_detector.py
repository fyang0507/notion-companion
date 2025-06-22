"""
Content Type Detector - Enhanced content classification for contextual chunking

This module detects document types (articles vs reading notes) to enable
content-aware chunking strategies for better RAG performance.
"""

import re
from typing import Dict, Any
import logging

class ContentTypeDetector:
    """Detect document types for specialized chunking strategies."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def detect_content_type(self, title: str, content: str, page_data: Dict[str, Any]) -> str:
        """
        Enhanced content type detection for articles vs reading notes.
        
        Args:
            title: Document title
            content: Document content
            page_data: Notion page metadata
            
        Returns:
            Content type: 'article', 'reading_notes', 'documentation', 'note', etc.
        """
        title_lower = title.lower()
        content_lower = content.lower()
        
        # Reading notes patterns - explicit indicators
        reading_note_indicators = [
            'reading notes', 'book notes', 'article notes', 'summary of',
            'notes on', 'thoughts on', 'highlights from', 'takeaways from',
            'key points', 'insights from', 'learnings from', 'reflection on'
        ]
        
        # Article patterns - academic/structured content indicators
        article_indicators = [
            'introduction', 'abstract', 'conclusion', 'methodology',
            'background', 'literature review', 'discussion', 'results',
            'findings', 'analysis', 'study', 'research', 'investigation'
        ]
        
        # Documentation patterns
        documentation_indicators = [
            'documentation', 'guide', 'manual', 'howto', 'readme', 'setup',
            'installation', 'configuration', 'api reference', 'tutorial'
        ]
        
        # Check title patterns first (most reliable)
        if any(indicator in title_lower for indicator in reading_note_indicators):
            self.logger.debug(f"Detected reading notes from title: {title}")
            return 'reading_notes'
        
        if any(indicator in title_lower for indicator in documentation_indicators):
            self.logger.debug(f"Detected documentation from title: {title}")
            return 'documentation'
        
        # Analyze content structure for more nuanced detection
        content_metrics = self._analyze_content_structure(content)
        
        # Check for article patterns in content
        article_keywords_count = sum(1 for indicator in article_indicators 
                                   if indicator in content_lower)
        
        if article_keywords_count >= 2:
            self.logger.debug(f"Detected article from content keywords: {article_keywords_count}")
            return 'article'
        
        # Analyze structural patterns
        if self._is_reading_notes_structure(content_metrics):
            self.logger.debug(f"Detected reading notes from structure: {content_metrics}")
            return 'reading_notes'
        
        if self._is_article_structure(content_metrics):
            self.logger.debug(f"Detected article from structure: {content_metrics}")
            return 'article'
        
        # Check for other specific types
        if self._is_meeting_notes(title_lower, content_lower):
            return 'meeting'
        
        if self._is_project_document(title_lower, content_lower):
            return 'project'
        
        # Default classification based on content length and structure
        if len(content) > 3000 and content_metrics['header_count'] >= 3:
            self.logger.debug(f"Defaulting to article for long structured content")
            return 'article'
        elif content_metrics['list_ratio'] > 0.3:
            self.logger.debug(f"Defaulting to reading notes for list-heavy content")
            return 'reading_notes'
        
        # Final fallback
        self.logger.debug(f"Defaulting to document type")
        return 'document'
    
    def _analyze_content_structure(self, content: str) -> Dict[str, Any]:
        """Analyze the structural patterns in content."""
        lines = content.split('\n')
        total_lines = len([line for line in lines if line.strip()])
        
        # Count different structural elements
        header_count = len(re.findall(r'^#+\s', content, re.MULTILINE))
        bullet_points = len(re.findall(r'^\s*[-*+]\s', content, re.MULTILINE))
        numbered_lists = len(re.findall(r'^\s*\d+\.\s', content, re.MULTILINE))
        
        # Quote/highlight patterns (common in reading notes)
        quotes = len(re.findall(r'^>\s', content, re.MULTILINE))
        highlights = len(re.findall(r'\*\*[^*]+\*\*', content))  # Bold text
        
        # Code blocks (common in technical documentation)
        code_blocks = len(re.findall(r'```[\s\S]*?```', content))
        inline_code = len(re.findall(r'`[^`]+`', content))
        
        # URL/link patterns
        urls = len(re.findall(r'https?://\S+', content))
        
        # Calculate ratios
        list_items = bullet_points + numbered_lists
        list_ratio = list_items / max(total_lines, 1)
        header_ratio = header_count / max(total_lines, 1)
        quote_ratio = quotes / max(total_lines, 1)
        
        return {
            'total_lines': total_lines,
            'header_count': header_count,
            'bullet_points': bullet_points,
            'numbered_lists': numbered_lists,
            'quotes': quotes,
            'highlights': highlights,
            'code_blocks': code_blocks,
            'inline_code': inline_code,
            'urls': urls,
            'list_ratio': list_ratio,
            'header_ratio': header_ratio,
            'quote_ratio': quote_ratio,
            'list_items': list_items
        }
    
    def _is_reading_notes_structure(self, metrics: Dict[str, Any]) -> bool:
        """Determine if structure indicates reading notes."""
        # Reading notes typically have:
        # - High ratio of list items (bullet points, numbered lists)
        # - Quotes/highlights for key passages
        # - Less formal structure than articles
        
        return (
            metrics['list_ratio'] > 0.2 or  # 20%+ list items
            metrics['quote_ratio'] > 0.1 or  # 10%+ quotes
            metrics['highlights'] > 3 or    # Multiple highlights
            (metrics['list_items'] > 5 and metrics['header_count'] < 3)  # Many lists, few headers
        )
    
    def _is_article_structure(self, metrics: Dict[str, Any]) -> bool:
        """Determine if structure indicates formal article."""
        # Articles typically have:
        # - Multiple headers for section organization
        # - Lower ratio of list items
        # - More prose-heavy content
        
        return (
            metrics['header_count'] >= 3 and  # Multiple sections
            metrics['list_ratio'] < 0.3 and   # Not list-heavy
            metrics['total_lines'] > 20       # Substantial content
        )
    
    def _is_meeting_notes(self, title_lower: str, content_lower: str) -> bool:
        """Detect meeting notes."""
        meeting_keywords = ['meeting', 'standup', 'sync', 'call', 'conference']
        return any(keyword in title_lower for keyword in meeting_keywords)
    
    def _is_project_document(self, title_lower: str, content_lower: str) -> bool:
        """Detect project documents."""
        project_keywords = ['project', 'initiative', 'roadmap', 'plan', 'strategy']
        return any(keyword in title_lower for keyword in project_keywords)
    
    def get_chunking_strategy_for_type(self, content_type: str) -> str:
        """Get the appropriate chunking strategy for a content type."""
        strategy_mapping = {
            'article': 'article_chunking',
            'reading_notes': 'reading_notes_chunking',
            'documentation': 'documentation_chunking',
            'meeting': 'meeting_notes_chunking',
            'project': 'article_chunking',  # Use article strategy for project docs
            'note': 'reading_notes_chunking',  # Use reading notes strategy for general notes
            'document': 'article_chunking'  # Default to article strategy
        }
        
        return strategy_mapping.get(content_type, 'article_chunking')