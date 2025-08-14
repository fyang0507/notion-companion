# Engineering Documentation

*Last Updated: 2025-08-13*

---

## System Architecture

### Tech Stack

**Frontend**: Next.js 13.5.1 with App Router (static export), TypeScript, Tailwind CSS, shadcn/ui  
**Backend**: FastAPI (Python with uv), Supabase (PostgreSQL + pgvector)  
**AI Integration**: OpenAI (GPT, text-embedding), centralized TOML config
**Package Management**: pnpm (Node.js), uv (Python >3.12 with pyproject.toml)  

### Modular Architecture

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
│   ├── factory.py          # Chunking strategy factory
│   ├── services/           # Chunking, Notion API
│   └── scripts/            # Sync utilities
├── rag/                    # RAG search and chat services
│   ├── interface.py        # RAG interface contract
│   ├── factory.py          # Retrieval strategy factory
│   ├── services/           # Search & chat session services
│   └── strategies/         # Different retrieval strategies
├── shared/                 # Common utilities and config
│   ├── config/             # Centralized configuration
│   ├── logging/            # Logging configuration
│   ├── services/           # Shared services (OpenAI)
│   └── utils/              # Shared utilities (token counter, supabase data cleaner)
├── evaluation/             # RAG evaluation framework
│   ├── config/              # Evaluation configuration files
│   ├── models/              # Pydantic models for evaluation
│   ├── scripts/             # Evaluation automation scripts
│   ├── services/            # Core evaluation services
│   └── utils/               # Evaluation utilities
├── app/                    # Next.js frontend
├── components/             # React components + shadcn/ui
├── hooks/                  # Custom React hooks
└── start.py                # Backend startup script
```

### Database Schema (Single Workspace)
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

### Service Architecture

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

### Configuration System

**Configuration System Design**:
- **Design Principle**: Config-driven architecture for runtime flexibility
- **Current Status**: `shared/config/` contains legacy files (not used) that need future updates
- **Active Configuration**: Uses TOML files in `evaluation/config/` and direct environment variables
- **Future Goal**: Centralized TOML configuration system for all modules

### API Architecture

**Streaming Endpoints**:
- `POST /api/chat` - Server-sent events streaming
- `POST /api/search` - Enhanced contextual search
- `POST /api/notion/webhook` - Real-time synchronization
- `POST /api/metadata/...` - Metadata filtering

**Layer Pattern**: Router → Service → Database

### Interface-Based Design

Each module defines clear contracts:
- `storage/interface.py` - Database operations
- `ingestion/interface.py` - Document processing
- `rag/interface.py` - Search and chat services
- Loose coupling between modules through well-defined interfaces

---

## Development Setup

### Prerequisites

- Node.js 18+
- Python >3.12
- Notion workspace with admin access

### Quick Start

#### Installation
```bash
# Install all dependencies
pnpm install

# Python dependencies (root level)
uv sync
```

#### Environment Configuration

**Frontend Environment** (`.env.local`):
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

**Backend Environment** (`.env`):
```bash
OPENAI_API_KEY=your_openai_api_key
NOTION_ACCESS_TOKEN=your_notion_token
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

**Environment Loading**:
- Frontend: Next.js automatically loads `.env.local` variables prefixed with `NEXT_PUBLIC_`
- Backend: FastAPI loads `.env` using python-dotenv at startup
- Configuration validation occurs at application boot with clear error messages

### Development Commands

#### Basic Development
- `pnpm run dev` - Frontend only (port 3000)
- `pnpm run backend` - Backend only (port 8000)
- `pnpm run dev:full` - Both frontend and backend concurrently

#### Build & Quality
- `pnpm run build` - Build Next.js for production
- `pnpm run lint` - Run ESLint validation
- `pnpm run pre-commit-test` - **OPTIONAL: Full test suite before significant commits**

#### Python Environment (uv Package Manager)
**CRITICAL: Always use uv for Python operations**
```bash
uv sync                          # Install dependencies
uv add package_name              # Add new dependency
uv add --dev package_name        # Add dev dependency
uv remove package_name           # Remove dependency
uv run python script.py          # Run Python scripts
```

#### Database & Synchronization
```bash
# Sync Notion databases with enhanced contextual processing
uv run python ingestion/scripts/sync_databases.py

# Test sync configuration
uv run python ingestion/scripts/sync_databases.py --dry-run

# Test model configuration
uv run python shared/config/model_config.py
```

### Component Testing (No Backend Required)
```bash
# Database connectivity test (5 seconds)
uv run python -c "import asyncio; from storage.database import init_db; asyncio.run(init_db()); print('✓ DB OK')"
```

### Configuration Files

#### Core Configuration
- `package.json` - Node.js dependencies and scripts
- `pyproject.toml` - Python dependencies with uv
- `shared/config/` - Centralized AI model and database configurations

#### Schema Management
- `storage/schema/schema.sql` - Full database schema
- `storage/schema/drop_schema.sql` - Reset database schema

---

## Coding Standards & SOPs

### Best Practices
- Retrieve latest doc before writing code: when working with external libraries that are in active development (e.g. `openai`, `supabase`), use Context7 MCP or perform online search to read the latest documentation or analysis the bugs before writing code
- Parameterization: Ensure that no silent defaults are set up. Set up `.toml` files for configuration if there are multiple parameters. Do not over-use default keyword arguments with default values. Do not use `.get('key', 'default')` (unless the key is optional and a default none/null value is expected), instead use bracket notation and fail hard when the key is not found. 
- When raising exceptions, raise the entire traceback
- Use `TODO, FIXME, XXX` for comments

### Preferred Tools
- Use pnpm for frontend, uv for backend
- Use `load_dotenv()` for environment loading
- Use `loguru` for backend logging
- Use built-in `tomllib` for TOML parsing (Python 3.11+)
- Use `seaborn` for statistical visualizations (if applicable), use `pandas` for data parsing (e.g. csv reading)

### Evaluation System

**Framework Overview**:
- Comprehensive RAG evaluation pipeline for testing different chunking and retrieval strategies
- Automated question generation from documents
- Self-verification system for QA pair quality
- Interactive visualization of evaluation results

**Key Components**:
- `evaluation/models/` - Pydantic models (Document, QuestionAnswerPair, CollectionStats)
- `evaluation/services/` - Core services (question_generator, retrieval_evaluator, qa_self_verifier)
- `evaluation/scripts/` - Automation (run_evaluation.py, interactive_visualization.py)
- `evaluation/config/` - TOML configurations for different evaluation strategies

**Evaluation Workflow**:
1. Data collection from Notion databases
2. Question generation using AI models
3. QA pair verification and quality assessment
4. Retrieval evaluation across different strategies
5. Interactive result visualization and analysis

### Testing Guidelines

**🚫 CRITICAL: NEVER start backend services silently**
**✅ CORRECT WORKFLOW:**
1. Ask user to start backend with `pnpm run backend`
2. Run curl tests against localhost:8000
3. Ask user to stop backend when testing is complete