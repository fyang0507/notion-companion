# Notion Sync Pipeline Specification

*Last Updated: 2025-07-16*

## Overview

The Notion synchronization pipeline transforms Notion content into a searchable knowledge base with Enhanced RAG (Retrieval-Augmented Generation) using Anthropic-style contextual retrieval.

## Architecture

### Core Components
- **NotionService** (`ingestion/services/notion_service.py`) - Notion API integration
- **DocumentProcessor** (`ingestion/services/document_processor.py`) - Processing orchestration
- **ContextualChunker** (`ingestion/services/contextual_chunker.py`) - Enhanced chunking
- **OpenAIService** (`ingestion/services/openai_service.py`) - AI integration
- **Database Layer** (`storage/database.py`) - Supabase storage

### Single Workspace Architecture
- **No workspace concept** - eliminated in v3.0
- **Database-centric** - individual Notion databases as primary units
- **Single token** - uses `NOTION_ACCESS_TOKEN` for access

## Pipeline Stages

### 1. Database Registration
```
Register Notion databases → Store access tokens → Track sync status
```

### 2. Content Extraction
```
Query database pages → Extract rich content → Handle multimedia → Process blocks
```

### 3. Content Processing
```
Determine document type → Apply chunking strategy → Generate contextual info
```

### 4. Embedding Generation
```
Create dual embeddings (content + contextual) → 70% contextual, 30% content weighting
```

### 5. Database Storage
```
Store documents → Create enhanced chunks → Maintain metadata relationships
```

## Enhanced RAG Features

### Contextual Retrieval
- **AI-generated context** for each chunk explaining document relationship
- **Dual embedding strategy** with weighted scoring (70/30 contextual/content)
- **Positional linking** via `prev_chunk_id`/`next_chunk_id` for context enrichment
- **Adjacent chunk retrieval** for richer search results

### Content-Aware Processing
- **Document Type Detection** - meeting notes, projects, documentation, bookmarks
- **Adaptive Chunking** - respects document hierarchy and semantic boundaries
- **Multimedia Support** - handles images, files, and media with URL references

## Database Schema

### Core Tables
- `notion_databases` - Database registry and access tokens
- `documents` - Full page content with dual embeddings
- `document_chunks` - Enhanced chunks with contextual fields
- `document_metadata` - Extracted metadata for filtering
- `multimedia_assets` - Images, files, and media

### Enhanced Schema Fields
- `chunk_context` - AI-generated contextual descriptions
- `chunk_summary` - Concise summaries of chunk content
- `contextual_embedding` - Context-aware vector embeddings
- `document_section` - Section hierarchy information

## Configuration System

### Centralized Configuration (`shared/config/models.toml`)
- **Model Selection** - configurable AI models for different tasks
- **Vector Search Parameters** - thresholds, weights, scoring factors
- **Performance Settings** - rate limiting, batch sizes, retry policies
- **Prompt Templates** - centralized prompt management

### Key Configuration Values
```toml
[vector_search]
match_threshold = 0.1              # Lowered from 0.7 for better recall
contextual_weight = 0.7           # Favor contextual embeddings
enable_context_enrichment = true  # Adjacent chunk retrieval
```

## Synchronization Methods

### Script-Based Sync
- **Manual execution** via `ingestion/scripts/sync_databases.py`
- **Configurable concurrency** with rate limiting
- **Dry-run mode** for testing

### Webhook-Based Updates
- **Real-time synchronization** via `api/routers/notion_webhook.py`
- **Event handling** for page creation, updates, deletion
- **Automatic processing** of updated content

## Performance Optimizations

### Rate Limiting
- **Notion API**: 2 requests/second with batch processing
- **OpenAI API**: Configurable delays (0.1s embeddings, 0.5s chat)
- **Vector operations**: IVFFlat indexes for similarity search

### Search Optimization
- **Threshold tuning** - lowered to 0.1 for better recall
- **Weighted scoring** - contextual embeddings prioritized
- **Context enrichment** - adjacent chunks for richer results

## Error Handling

### Fault Tolerance
- **Graceful degradation** - fallback strategies for AI failures
- **Retry logic** - configurable attempts with exponential backoff
- **Partial processing** - continues even if individual pages fail
- **Comprehensive logging** - structured logging for debugging

### Recovery Mechanisms
- **Database transactions** with rollback on errors
- **Fallback embedding** if contextual generation fails
- **Automatic cleanup** of partial sync states