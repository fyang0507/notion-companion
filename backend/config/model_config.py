"""
Model Configuration Manager for Notion Companion

Centralized management of AI model configurations, providing a single source of truth
for model selection, parameters, and prompt templates.
"""

import os
import tomllib
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    model: str
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    dimensions: Optional[int] = None
    max_input_tokens: Optional[int] = None
    batch_size: Optional[int] = None

@dataclass
class LimitsConfig:
    """Token and processing limits."""
    max_embedding_tokens: int
    max_summary_input_tokens: int
    max_chat_context_tokens: int
    chunk_size_tokens: int
    chunk_overlap_tokens: int

@dataclass
class PerformanceConfig:
    """Performance and rate limiting settings."""
    embedding_batch_size: int
    embedding_delay_seconds: float
    chat_delay_seconds: float
    summarization_delay_seconds: float
    max_retries: int
    retry_delay_seconds: float

@dataclass
class ChatPromptsConfig:
    """Chat-related prompt configurations."""
    system_prompt: str
    streaming_system_prompt: str
    context_template: str

@dataclass
class TitleGenerationConfig:
    """Title generation prompt and settings."""
    title_prompt: str
    max_words: int
    temperature_override: float
    max_tokens_override: int

@dataclass
class SummarizationPromptsConfig:
    """Summarization prompts and settings."""
    document_summary_prompt: str
    chat_summary_prompt: str
    default_max_length: int
    chat_summary_max_tokens: int
    chat_summary_temperature: float
    chat_summary_max_chars: int

@dataclass
class DocumentProcessingPromptsConfig:
    """Document processing prompts (for future use)."""
    content_type_detection_prompt: str
    metadata_extraction_prompt: str

@dataclass
class SearchPromptsConfig:
    """Search enhancement prompts (for future use)."""
    query_expansion_prompt: str
    result_ranking_prompt: str

@dataclass
class PromptsConfig:
    """All prompt configurations."""
    chat: ChatPromptsConfig
    title_generation: TitleGenerationConfig
    summarization: SummarizationPromptsConfig
    document_processing: DocumentProcessingPromptsConfig
    search: SearchPromptsConfig

class ModelConfigManager:
    """Manages model configurations and prompts."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the model configuration manager.
        
        Args:
            config_path: Path to the models.toml file
        """
        if config_path is None:
            config_path = Path(__file__).parent / "models.toml"
        
        self.config_path = config_path
        self._config = None
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from TOML file."""
        try:
            with open(self.config_path, 'rb') as f:
                self._config = tomllib.load(f)
            logger.info(f"Loaded model configuration from {self.config_path}")
        except FileNotFoundError:
            logger.error(f"Model configuration file not found: {self.config_path}")
            raise
        except Exception as e:
            logger.error(f"Error loading model configuration: {e}")
            raise
    
    def _get_nested_value(self, path: str, default: Any = None) -> Any:
        """Get nested configuration value using dot notation."""
        keys = path.split('.')
        value = self._config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_embedding_config(self) -> ModelConfig:
        """Get embedding model configuration."""
        config_section = self._config.get("models", {}).get("embedding", {})
        
        return ModelConfig(
            model=config_section.get("model", "text-embedding-3-small"),
            dimensions=config_section.get("dimensions", 1536),
            max_input_tokens=config_section.get("max_input_tokens", 8191),
            batch_size=config_section.get("batch_size", 10)
        )
    
    def get_chat_config(self) -> ModelConfig:
        """Get chat model configuration."""
        config_section = self._config.get("models", {}).get("chat", {})
        
        return ModelConfig(
            model=config_section.get("model", "gpt-4o-mini"),
            max_tokens=config_section.get("max_tokens", 4096),
            temperature=config_section.get("temperature", 0.7)
        )
    
    def get_summarization_config(self) -> ModelConfig:
        """Get summarization model configuration."""
        config_section = self._config.get("models", {}).get("summarization", {})
        
        return ModelConfig(
            model=config_section.get("model", "gpt-4o-mini"),
            max_tokens=config_section.get("max_tokens", 800),
            temperature=config_section.get("temperature", 0.3)
        )
    
    def get_limits_config(self) -> LimitsConfig:
        """Get processing limits configuration."""
        limits = self._config.get("limits", {})
        
        return LimitsConfig(
            max_embedding_tokens=limits.get("max_embedding_tokens", 8000),
            max_summary_input_tokens=limits.get("max_summary_input_tokens", 20000),
            max_chat_context_tokens=limits.get("max_chat_context_tokens", 15000),
            chunk_size_tokens=limits.get("chunk_size_tokens", 1000),
            chunk_overlap_tokens=limits.get("chunk_overlap_tokens", 100)
        )
    
    def get_performance_config(self) -> PerformanceConfig:
        """Get performance and rate limiting configuration."""
        perf = self._config.get("performance", {})
        
        return PerformanceConfig(
            embedding_batch_size=perf.get("embedding_batch_size", 10),
            embedding_delay_seconds=perf.get("embedding_delay_seconds", 0.1),
            chat_delay_seconds=perf.get("chat_delay_seconds", 0.5),
            summarization_delay_seconds=perf.get("summarization_delay_seconds", 1.0),
            max_retries=perf.get("max_retries", 3),
            retry_delay_seconds=perf.get("retry_delay_seconds", 2.0)
        )
    
    def get_prompts_config(self) -> PromptsConfig:
        """Get all prompt configurations."""
        # Chat prompts
        chat_config = ChatPromptsConfig(
            system_prompt=self._get_nested_value(
                "prompts.chat.system_prompt",
                """You are a helpful AI assistant that answers questions based on the user's Notion workspace content. 
{context_section}

Guidelines:
- Be concise and helpful
- Reference specific documents when possible
- If you're not sure about something, say so
- Format responses in markdown when appropriate"""
            ),
            streaming_system_prompt=self._get_nested_value(
                "prompts.chat.streaming_system_prompt",
                """You are a helpful AI assistant that answers questions based on the user's Notion workspace content. 
{context_section}"""
            ),
            context_template=self._get_nested_value(
                "prompts.chat.context_template",
                "Here is relevant context from their workspace: {context}"
            )
        )
        
        # Title generation
        title_config = TitleGenerationConfig(
            title_prompt=self._get_nested_value(
                "prompts.title_generation.title_prompt",
                """Based on this conversation, generate a concise, descriptive title that captures the main topic or question being discussed. 

Guidelines:
- Maximum {max_words} words
- Be specific and descriptive
- Focus on the main topic/question
- Use clear, simple language
- No quotes or special formatting
- No articles (a, an, the) unless essential

Conversation:
{conversation_text}

Title ({max_words} words max):"""
            ),
            max_words=self._get_nested_value("prompts.title_generation.max_words", 8),
            temperature_override=self._get_nested_value("prompts.title_generation.temperature_override", 0.3),
            max_tokens_override=self._get_nested_value("prompts.title_generation.max_tokens_override", 20)
        )
        
        # Summarization prompts
        summarization_config = SummarizationPromptsConfig(
            document_summary_prompt=self._get_nested_value(
                "prompts.summarization.document_summary_prompt",
                """Please create a comprehensive but concise summary of this document that captures:
1. Main topics and key points
2. Important concepts and themes  
3. Essential information and takeaways
4. Context and purpose

The summary should be roughly {max_length} words and be optimized for semantic search.

Title: {title}

Content:
{content}

Summary:"""
            ),
            chat_summary_prompt=self._get_nested_value(
                "prompts.summarization.chat_summary_prompt",
                """Generate a concise 1-2 sentence summary of this conversation. Focus on the main topic and key points discussed.

Conversation:
{conversation_text}

Summary (max 150 characters):"""
            ),
            default_max_length=self._get_nested_value("prompts.summarization.default_max_length", 500),
            chat_summary_max_tokens=self._get_nested_value("prompts.summarization.chat_summary_max_tokens", 40),
            chat_summary_temperature=self._get_nested_value("prompts.summarization.chat_summary_temperature", 0.3),
            chat_summary_max_chars=self._get_nested_value("prompts.summarization.chat_summary_max_chars", 150)
        )
        
        # Document processing prompts (fallback defaults for commented-out sections)
        doc_processing_config = DocumentProcessingPromptsConfig(
            content_type_detection_prompt=self._get_nested_value(
                "prompts.document_processing.content_type_detection_prompt",
                """Analyze this document and classify its content type. Consider the title, structure, and content.

Title: {title}
Content: {content}

Classify as one of: documentation, meeting_notes, project_plan, knowledge_base, reference, other

Content Type:"""
            ),
            metadata_extraction_prompt=self._get_nested_value(
                "prompts.document_processing.metadata_extraction_prompt",
                """Extract key metadata from this document that would be useful for search and organization.

Title: {title}
Content: {content}

Extract:
- Key topics (comma-separated)
- Main categories (comma-separated)
- Priority level (high/medium/low)
- Document type (technical/business/personal/other)

Metadata:"""
            )
        )
        
        # Search prompts (fallback defaults for commented-out sections)
        search_config = SearchPromptsConfig(
            query_expansion_prompt=self._get_nested_value(
                "prompts.search.query_expansion_prompt",
                """Expand this search query to improve semantic search results. Consider synonyms, related terms, and different phrasings.

Original query: {query}

Expanded query suggestions (comma-separated):"""
            ),
            result_ranking_prompt=self._get_nested_value(
                "prompts.search.result_ranking_prompt",
                """Given this search query and these results, rank them by relevance and provide a brief explanation.

Query: {query}

Results:
{results}

Ranked results with explanations:"""
            )
        )
        
        return PromptsConfig(
            chat=chat_config,
            title_generation=title_config,
            summarization=summarization_config,
            document_processing=doc_processing_config,
            search=search_config
        )
    
    def format_chat_system_prompt(self, context: Optional[str] = None, use_streaming: bool = False) -> str:
        """Format chat system prompt with context."""
        prompts = self.get_prompts_config()
        
        # Choose appropriate system prompt
        if use_streaming:
            system_prompt = prompts.chat.streaming_system_prompt
        else:
            system_prompt = prompts.chat.system_prompt
        
        # Format context section
        if context:
            context_section = prompts.chat.context_template.format(context=context)
        else:
            context_section = ""
        
        return system_prompt.format(context_section=context_section)
    
    def format_title_prompt(self, conversation_text: str, max_words: Optional[int] = None) -> str:
        """Format title generation prompt."""
        prompts = self.get_prompts_config()
        words_limit = max_words or prompts.title_generation.max_words
        
        return prompts.title_generation.title_prompt.format(
            conversation_text=conversation_text,
            max_words=words_limit
        )
    
    def format_document_summary_prompt(self, title: str, content: str, max_length: Optional[int] = None) -> str:
        """Format document summarization prompt."""
        prompts = self.get_prompts_config()
        length_limit = max_length or prompts.summarization.default_max_length
        
        return prompts.summarization.document_summary_prompt.format(
            title=title,
            content=content,
            max_length=length_limit
        )
    
    def format_chat_summary_prompt(self, conversation_text: str) -> str:
        """Format chat summarization prompt."""
        prompts = self.get_prompts_config()
        
        return prompts.summarization.chat_summary_prompt.format(
            conversation_text=conversation_text
        )
    
    def reload_config(self) -> None:
        """Reload configuration from file."""
        self._load_config()
        logger.info("Model configuration reloaded")

# Global instance
_model_config_manager = None

def get_model_config() -> ModelConfigManager:
    """Get the global model configuration manager instance."""
    global _model_config_manager
    if _model_config_manager is None:
        _model_config_manager = ModelConfigManager()
    return _model_config_manager

def set_model_config(config_manager: ModelConfigManager) -> None:
    """Set the global model configuration manager instance."""
    global _model_config_manager
    _model_config_manager = config_manager