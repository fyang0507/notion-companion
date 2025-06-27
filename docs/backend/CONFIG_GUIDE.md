# LLM Configuration System

Centralized configuration management for all AI models and prompts in the Notion Companion webapp.

## Overview

The LLM Configuration System provides a single source of truth for:
- **Model Selection**: Choose AI models for different tasks (chat, embeddings, summarization)
- **Model Parameters**: Configure temperature, max tokens, batch sizes, etc.
- **Prompt Templates**: Centralized prompt management for all LLM processes
- **Performance Settings**: Rate limiting, retries, and optimization parameters
- **Token Limits**: Processing boundaries for different operations

## Architecture

```
backend/config/
├── models.toml           # Main configuration file
├── model_config.py       # Configuration manager and data models
└── README.md            # This documentation
```

### Configuration Flow
1. **models.toml** defines all models, prompts, and settings
2. **ModelConfigManager** loads and validates configuration
3. Services use **get_model_config()** to access centralized settings
4. Prompts are formatted dynamically with context

## Configuration File Structure

### Basic Structure (`models.toml`)

```toml
[models.embedding]
model = "text-embedding-3-small"
dimensions = 1536
batch_size = 10

[models.chat]
model = "gpt-4o-mini"
max_tokens = 4096
temperature = 0.7

[models.summarization]
model = "gpt-4o-mini"
max_tokens = 800
temperature = 0.3

[limits]
max_embedding_tokens = 8000
max_summary_input_tokens = 20000
max_chat_context_tokens = 15000

[performance]
embedding_batch_size = 10
max_retries = 3
chat_delay_seconds = 0.5

[prompts.chat]
system_prompt = "You are a helpful AI assistant..."
context_template = "Here is relevant context: {context}"

[prompts.title_generation]
title_prompt = "Generate a concise title..."
max_words = 8
temperature_override = 0.3

[prompts.summarization]
document_summary_prompt = "Create a comprehensive summary..."
default_max_length = 500
```

## Usage Patterns

### Basic Configuration Access

```python
from config.model_config import get_model_config

# Get global config instance
config = get_model_config()

# Access model configurations
chat_config = config.get_chat_config()
embedding_config = config.get_embedding_config()
limits = config.get_limits_config()
```

### Prompt Management

```python
# Format prompts dynamically
chat_prompt = config.format_chat_system_prompt(
    context="User's workspace content..."
)

title_prompt = config.format_title_prompt(
    conversation_text="User: How to deploy? Assistant: ..."
)

summary_prompt = config.format_document_summary_prompt(
    title="Deployment Guide",
    content="This document explains..."
)
```

### Service Integration

```python
# In services/openai_service.py
from config.model_config import get_model_config

class OpenAIService:
    def __init__(self):
        self.config = get_model_config()
    
    async def generate_chat_response(self, message: str, context: str = None):
        chat_config = self.config.get_chat_config()
        system_prompt = self.config.format_chat_system_prompt(context=context)
        
        # Use centralized configuration
        response = await self.client.chat.completions.create(
            model=chat_config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            max_tokens=chat_config.max_tokens,
            temperature=chat_config.temperature
        )
        return response
```

## Deployment Strategy

### Development Configuration
The default configuration in `models.toml` is optimized for development:
- Uses cost-effective models (`gpt-4o-mini`)
- Small batch sizes for faster iteration
- Shorter delays between API calls
- Conservative token limits

### Production Deployment
For production deployment:
1. **Edit `models.toml` directly** before deployment
2. **Update model selections** to production-grade models:
   ```toml
   [models.chat]
   model = "gpt-4o"  # Better quality for production
   
   [models.summarization]
   model = "gpt-4o"  # Consistent model across features
   ```
3. **Adjust performance settings** for scale:
   ```toml
   [performance]
   embedding_batch_size = 100  # Higher throughput
   max_retries = 5             # More resilient
   ```
4. **Review token limits** for production workloads
5. **Deploy with updated configuration**

### Configuration Management Best Practices

1. **Version Control**: Keep `models.toml` in version control
2. **Backup**: Keep backup of working configurations
3. **Testing**: Test configuration changes in staging first
4. **Documentation**: Document any custom prompt modifications
5. **Monitoring**: Monitor token usage and model performance

## LLM-Enabled Processes

The system manages configuration for these active LLM processes:

### Currently Active
- **💬 Chat Responses**: Real-time user interactions with RAG context
- **🏷️ Title Generation**: Auto-generate chat session titles (8-word limit)
- **📝 Chat Summaries**: Summarize conversations for history (150 char limit)
- **📄 Document Summaries**: Summarize Notion pages for embeddings (500 words)
- **📊 Embeddings**: Generate semantic embeddings for search
- **🔍 Document Processing**: Extract and chunk content from Notion

### Future-Ready (Commented Out)
- **🔍 Query Expansion**: Enhance search queries with synonyms
- **📊 Result Ranking**: Re-rank search results by relevance
- **🏷️ Content Classification**: Classify document types automatically
- **📊 Metadata Extraction**: Extract structured data from documents

## Configuration Classes

### Core Data Models

```python
@dataclass
class ModelConfig:
    model: str
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    dimensions: Optional[int] = None
    batch_size: Optional[int] = None

@dataclass
class ChatPromptsConfig:
    system_prompt: str
    streaming_system_prompt: str
    context_template: str

@dataclass
class TitleGenerationConfig:
    title_prompt: str
    max_words: int
    temperature_override: float
    max_tokens_override: int
```

### Configuration Manager

```python
class ModelConfigManager:
    def get_embedding_config() -> ModelConfig
    def get_chat_config() -> ModelConfig
    def get_summarization_config() -> ModelConfig
    def get_limits_config() -> LimitsConfig
    def get_performance_config() -> PerformanceConfig
    def get_prompts_config() -> PromptsConfig
    
    def format_chat_system_prompt(context: str = None) -> str
    def format_title_prompt(conversation_text: str) -> str
    def format_document_summary_prompt(title: str, content: str) -> str
    def format_chat_summary_prompt(conversation_text: str) -> str
```

## Examples and Testing

### Running Demos

```bash
# Basic configuration demo
cd backend
python scripts/model_config_demo.py

# Comprehensive system demo
python scripts/llm_config_demo.py
```

### Example Output

```
🤖 Model Configuration Demo
========================================

📋 Model Configurations:
-------------------------
🔤 Embedding: text-embedding-3-small
   - Dimensions: 1536
   - Batch Size: 10
💬 Chat: gpt-4o-mini
   - Max Tokens: 4096
   - Temperature: 0.7
📝 Summarization: gpt-4o-mini
   - Max Tokens: 800
   - Temperature: 0.3
```

## Performance Considerations

### Token Management
- **Embedding Tokens**: Limited to 8,000 per operation
- **Chat Context**: Maximum 15,000 tokens including history
- **Summary Input**: Up to 20,000 tokens per document
- **Chunking**: 1,000 token chunks with 100 token overlap

### Rate Limiting
- **Embedding Delay**: 0.1s between calls (development)
- **Chat Delay**: 0.5s between completions (development)
- **Batch Processing**: 10 embeddings per batch (development)
- **Retries**: Maximum 3 attempts with 2s delay

### Cost Optimization
- Development uses `gpt-4o-mini` for cost efficiency
- Batch processing reduces API call overhead
- Conservative token limits prevent runaway costs
- Configurable delays prevent rate limit violations

## Troubleshooting

### Common Issues

1. **Configuration Not Loading**
   ```python
   # Check file path
   config = ModelConfigManager(config_path="path/to/models.toml")
   ```

2. **Missing Prompt Values**
   ```python
   # Fallback defaults are provided automatically
   prompts = config.get_prompts_config()
   ```

3. **Model Not Found**
   ```toml
   # Verify model names in models.toml
   [models.chat]
   model = "gpt-4o-mini"  # Correct model name
   ```

4. **Token Limit Exceeded**
   ```toml
   # Adjust limits in configuration
   [limits]
   max_chat_context_tokens = 20000  # Increase limit
   ```

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

config = ModelConfigManager()  # Will show debug info
```

## Migration Guide

### From Hardcoded Prompts

1. **Identify hardcoded prompts** in services
2. **Move prompts to `models.toml`** under appropriate sections
3. **Update service code** to use `config.format_*_prompt()` methods
4. **Test with demo scripts** to verify integration
5. **Deploy with confidence**

### Adding New LLM Features

1. **Add prompts to `models.toml`**:
   ```toml
   [prompts.new_feature]
   main_prompt = "Your prompt template here..."
   ```

2. **Update `PromptsConfig`** dataclass in `model_config.py`
3. **Add formatting method** to `ModelConfigManager`
4. **Use in service**:
   ```python
   prompt = config.format_new_feature_prompt(data)
   ```

This centralized approach ensures consistency, maintainability, and easy deployment management across all LLM-powered features in the Notion Companion. 