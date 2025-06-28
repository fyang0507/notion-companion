# LLM Configuration System

Centralized configuration management for all AI models and prompts in the Notion Companion webapp.

## Overview

The LLM Configuration System provides a single source of truth for:
- **Model Selection**: AI models for chat, embeddings, and summarization
- **Performance Settings**: Rate limiting, batch sizes, token limits
- **Vector Search**: Similarity thresholds, hybrid search weights, re-ranking
- **Prompt Templates**: Centralized prompt management for all LLM processes

## Architecture

```
backend/config/
├── models.toml           # Main configuration file
└── model_config.py       # Configuration manager
```

## Configuration Structure

### Key Sections in `models.toml`

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

[vector_search]
match_threshold = 0.1
match_count_default = 10
enable_context_enrichment = true
contextual_weight = 0.7
enable_reranking = true

[prompts.chat]
system_prompt = "You are a helpful AI assistant..."
context_template = "Here is relevant context: {context}"

[prompts.title_generation]
title_prompt = "Generate a concise title..."
max_words = 8

[prompts.summarization]
document_summary_prompt = "Create a comprehensive summary..."
default_max_length = 500
```

## Basic Usage

### Accessing Configuration

```python
from config.model_config import get_model_config

config = get_model_config()

# Get configurations
chat_config = config.get_chat_config()
vector_config = config.get_vector_search_config()
limits = config.get_limits_config()
```

### Using Prompts

```python
# Format prompts with dynamic context
system_prompt = config.format_chat_system_prompt(context="workspace content...")
title_prompt = config.format_title_prompt(conversation_text="...")
summary_prompt = config.format_document_summary_prompt(title="...", content="...")
```

### Service Integration

```python
class OpenAIService:
    def __init__(self):
        self.config = get_model_config()
    
    async def generate_response(self, message: str, context: str = None):
        chat_config = self.config.get_chat_config()
        system_prompt = self.config.format_chat_system_prompt(context=context)
        
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

## Vector Search Configuration

Key parameters for semantic search and hybrid search:

- **`match_threshold`**: Similarity threshold (0.0-1.0, default: 0.1)
- **`match_count_default`**: Default results to return (default: 10)
- **`enable_context_enrichment`**: Enable adjacent chunk context (default: true)
- **`contextual_weight`**: Weight for contextual embeddings (default: 0.7)
- **`enable_reranking`**: Enable result re-ranking (default: true)

## Active LLM Processes

Currently configured processes:
- **💬 Chat Responses**: Real-time user interactions with RAG context
- **🏷️ Title Generation**: Auto-generate chat session titles (8-word limit)
- **📝 Summaries**: Document and chat summaries for search optimization
- **📊 Embeddings**: Semantic embeddings for vector search
- **🔍 Document Processing**: Content extraction and chunking

## Deployment

### Development (Default)
- Uses `gpt-4o-mini` for cost efficiency
- Small batch sizes for faster iteration
- Conservative token limits

### Production
1. **Edit `models.toml` directly** before deployment
2. **Update models** for production quality:
   ```toml
   [models.chat]
   model = "gpt-4o"  # Better quality
   ```
3. **Increase performance settings**:
   ```toml
   [performance]
   embedding_batch_size = 100  # Higher throughput
   ```

## Troubleshooting

### Common Issues

**Configuration Not Loading**
```python
config = ModelConfigManager(config_path="path/to/models.toml")
```

**Token Limit Exceeded**
```toml
[limits]
max_chat_context_tokens = 20000  # Increase limit
```

**Debug Mode**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
config = ModelConfigManager()  # Shows debug info
```

### Testing Configuration

```bash
cd backend
python scripts/model_config_demo.py
```

## Adding New Features

1. **Add prompts to `models.toml`**:
   ```toml
   [prompts.new_feature]
   main_prompt = "Your prompt template..."
   ```

2. **Update service code**:
   ```python
   prompt = config.format_new_feature_prompt(data)
   ```

This centralized approach ensures consistency, maintainability, and easy deployment management across all LLM-powered features. 