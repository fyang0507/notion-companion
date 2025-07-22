# System Architecture

*Last Updated: 2025-07-21*

## Tech Stack

**Frontend**: Next.js 13.5.1 with App Router (static export), TypeScript, Tailwind CSS, shadcn/ui  
**Backend**: FastAPI (Python with uv), Supabase (PostgreSQL + pgvector)  
**AI Integration**: OpenAI (GPT, text-embedding), centralized TOML config
**Package Management**: pnpm (Node.js), uv (Python 3.12+ with pyproject.toml)  

## Modular Architecture

```
├── api/                    # FastAPI application
│   ├── main.py             # FastAPI app entry point
│   ├── models/             # Pydantic models
│   └── routers/            # API endpoints
├── storage/                # Database layer
│   ├── database.py         # Supabase client & operations
│   ├── interface.py        # Storage interface contract
│   └── schema/             # SQL schema files
├── ingestion/              # Document processing pipeline
│   ├── interface.py        # Ingestion interface contract
│   ├── services/           # Chunking, Notion API, OpenAI
│   └── scripts/            # Sync utilities
├── rag/                    # RAG search and chat services
│   ├── interface.py        # RAG interface contract
│   ├── services/           # Search & chat session services
│   └── strategies/         # Different retrieval strategies
├── shared/                 # Common utilities and config
│   ├── config/             # Centralized configuration
│   ├── logging/            # Logging configuration
│   └── utils/              # Shared utilities
├── evaluation/             # RAG evaluation framework
├── app/                    # Next.js frontend
├── components/             # React components + shadcn/ui
├── hooks/                  # Custom React hooks
└── start.py                # Backend startup script
```

## Database Schema (Single Workspace)
(subject to change with new experiments on chunking and retrieval strategies)

**Core Tables**: 
- `notion_databases` - Connected Notion databases registry
- `documents` - Notion pages with full content and metadata
- `document_chunks` - Enhanced with contextual retrieval support
- `document_metadata` - Extracted queryable fields
- `chat_sessions` - Persistent conversation management
- `chat_messages` - Messages with citations

**Enhanced RAG Schema**:
- `contextual_embedding` - Anthropic-style dual embedding strategy
- `chunk_context` - AI-generated contextual descriptions
- `prev_chunk_id`, `next_chunk_id` - Positional linking for context enrichment

## Service Architecture

**Frontend Services**: (not fully implemented, for future use)
- `hooks/use-auth.ts` - Authentication management
- `hooks/use-chat-sessions.ts` - Chat session state
- `hooks/use-metadata.ts` - Metadata filtering
- `hooks/use-notion-databases.ts` - Database state

**Backend Services**: (subject to change with new experiments on chunking and retrieval strategies)
- `rag/services/rag_search_service.py` - Unified search pipeline
- `rag/services/chat_session_service.py` - Chat session management
- `ingestion/services/openai_service.py` - OpenAI integration
- `ingestion/services/notion_service.py` - Notion API client
- `ingestion/services/contextual_chunker.py` - Enhanced chunking

## Configuration System

**Centralized TOML Configuration**:
- `shared/config/models.toml` - All AI model settings
- `shared/config/databases.toml` - Database configurations
- `shared/config/model_config.py` - Configuration loading
- Runtime flexibility without code deployment

## API Architecture

**Streaming Endpoints**:
- `POST /api/chat` - Server-sent events streaming
- `POST /api/search` - Enhanced contextual search
- `POST /api/notion/webhook` - Real-time synchronization
- `POST /api/metadata/...` - Metadata filtering

**Layer Pattern**: Router → Service → Database

## Interface-Based Design

Each module defines clear contracts:
- `storage/interface.py` - Database operations
- `ingestion/interface.py` - Document processing
- `rag/interface.py` - Search and chat services
- Loose coupling between modules through well-defined interfaces