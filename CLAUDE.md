# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Notion Companion is a production-ready AI-powered knowledge assistant that connects to your primary Notion workspace, providing intelligent search and chat capabilities with real-time synchronization. It's a full-stack RAG (Retrieval-Augmented Generation) application optimized for single-user, multi-database workflows.

## Tech Stack

**Frontend**: Next.js 13.5.1 with App Router, TypeScript, Tailwind CSS, shadcn/ui components
**Backend**: FastAPI (Python with uv package manager), Supabase (PostgreSQL + pgvector), OpenAI integration
**Key Features**: **Enhanced RAG with Contextual Retrieval**, Anthropic-style chunk context generation, content-aware processing, adjacent chunk context enrichment, dual embedding strategy, streaming chat, Notion webhook synchronization, single workspace with multi-database filtering

## Development & Testing

### Basic Development Commands
- `npm run dev` - Frontend only (port 3000)
- `npm run backend` - Backend only (port 8000) 
- `npm run dev:full` - Both frontend and backend concurrently
- `make dev` - Alternative using Makefile
- `npm run build` - Build Next.js for production
- `npm run lint` - Run ESLint validation (ALWAYS run before committing)

### Backend Operations
- `cd backend && .venv/bin/python scripts/sync_databases.py` - Sync Notion databases with enhanced contextual processing
- `cd backend && .venv/bin/python scripts/sync_databases.py --dry-run` - Test sync configuration
- `cd backend && .venv/bin/python scripts/model_config_demo.py` - Test model configuration
- `cd backend && .venv/bin/python test_contextual_rag.py` - Test enhanced RAG components

### Python Environment Management
**IMPORTANT: Always use uv-managed virtual environment for Python operations**
- **Activate environment**: `cd backend && source .venv/bin/activate`
- **Direct execution**: Use `.venv/bin/python` instead of `python` or `python3`
- **Package management**: `uv add package_name` (not pip install)
- **All Python scripts**: Must run from backend directory with `.venv/bin/python path/to/script.py`

### Claude Code Testing Guidelines

**🚫 CRITICAL: NEVER start backend services in Claude Code**
- Commands with `&` cause 2-minute timeouts
- `npm run backend` doesn't persist in Claude Code environment

**✅ CORRECT TESTING WORKFLOW:**
1. Claude identifies need to test backend API
2. Claude asks: "Please start the backend with `npm run backend` so I can test [feature]"
3. User starts backend in their environment  
4. Claude runs curl tests against localhost:8000
5. Claude asks user to stop backend when testing is complete

**⚡ Fast Component Testing (No Backend Required):**
```bash
# Database connectivity test (5 seconds)
.venv/bin/python -c "import asyncio; from database import init_db; asyncio.run(init_db()); print('✓ DB OK')"

# OpenAI integration test (10 seconds)  
.venv/bin/python -c "import asyncio; from services.openai_service import get_openai_service; asyncio.run(get_openai_service().generate_embedding('test')); print('✓ OpenAI OK')"

# Vector search test (15 seconds)
.venv/bin/python -c "
import asyncio
from database import init_db, get_db
from services.openai_service import get_openai_service

async def test():
    await init_db()
    db = get_db()
    openai_service = get_openai_service()
    embedding = await openai_service.generate_embedding('test')
    results = db.vector_search_for_single_workspace(embedding.embedding, 0.1, 3)
    print(f'✓ Vector search: {len(results)} results')

asyncio.run(test())
"
```

**🧹 Process Management:**
- Always kill any background processes at the end of investigations
- Use `pkill -f uvicorn` or `pkill -f python` to clean up
- Component testing is preferred over full server testing for speed

### Logging & Debugging System
- **Log Files**: All logs in `logs/` directory with automatic rotation
  - `app.log` - General application logs (JSON structured)
  - `api.log` - API request/response logs with timing
  - `errors.log` - Error-level logs only
  - `performance.log` - Performance metrics and slow operations
- **Frontend Logging**: Persistent localStorage with `lib/logger.ts`
  - Use `<DebugLogs />` component to view/export frontend logs
  - Request correlation IDs link frontend/backend logs
- **Debugging Workflow**: Check log files first instead of restarting services

### Initial Setup
- `make install` - Install both Python (uv) and Node (pnpm) dependencies
- `make setup-env` - Create environment file template
- Deploy the SQL script from setup guide (`/setup` page) in Supabase
- Set `NOTION_ACCESS_TOKEN` in environment for single workspace
- **Note**: No workspace setup needed - uses single token for entire app

## Architecture Patterns

### Full-Stack Structure
- **Frontend**: `app/` directory uses Next.js App Router with static export
- **Backend**: `backend/` directory contains FastAPI application with routers and services
- **Components**: Extensive shadcn/ui component library in `components/ui/`
- **Shared Types**: TypeScript definitions in `types/` directory

### Enhanced RAG Implementation (v4.0) ✨
**Anthropic-Style Contextual Retrieval with Context Enrichment**
- **Contextual Retrieval**: Each chunk includes AI-generated context explaining how it relates to the document
- **Content-Aware Processing**: Different chunking strategies for articles vs reading notes vs documentation
- **Adjacent Chunk Context**: Search results include neighboring chunks for richer context
- **Dual Embedding Strategy**: Both content and contextual embeddings for enhanced relevance
- **Positional Linking**: Maintains document narrative flow through chunk relationships
- **Enhanced Search APIs**: `/api/search` (contextual) and `/api/search/hybrid` endpoints
- Vector embeddings stored in Supabase pgvector with contextual metadata
- Configurable OpenAI models via `backend/config/models.toml`
- AI document summarization for large documents (handles 30k+ tokens)
- Server-Sent Events for streaming chat responses

### API Architecture
- FastAPI routers in `backend/routers/` for organized endpoints
- Service layer in `backend/services/` for business logic
- Pydantic models for request/response validation
- Main endpoints: `/api/chat` (streaming), `/api/search` (enhanced contextual), `/api/search/hybrid` (documents + chunks), `/api/notion/webhook`

### Database Schema
Enhanced Single-Database Model (v4.0) with Contextual Retrieval:
- Core tables: `documents`, `document_chunks`, `document_metadata`, `database_schemas`
- **Enhanced `document_chunks`**: Added contextual retrieval fields:
  - `chunk_context` - AI-generated contextual description
  - `chunk_summary` - AI-generated chunk summary
  - `contextual_embedding` - Enhanced vector embedding with context
  - `prev_chunk_id`, `next_chunk_id` - Positional linking for context enrichment
  - `document_section`, `section_hierarchy` - Document structure awareness
- **New SQL Functions**: `match_contextual_chunks`, `get_chunk_with_context`, `hybrid_contextual_search`
- Multimedia support: `multimedia_assets`, `document_multimedia`
- Analytics: `search_analytics` for query tracking
- Database schema manager for automatic Notion database analysis
- Uses Supabase Auth for user management and pgvector for similarity search

### Frontend Patterns
- React components with TypeScript and Tailwind CSS
- Custom hooks for state management (`useAuth`, `useNotionConnection`, `useNotionDatabases`)
- Real-time data fetching with Supabase integration
- Database-level filtering in chat and search interfaces
- Theme switching via next-themes (system/light/dark)
- Responsive design with mobile-first approach

## Configuration

### Environment Variables
**Frontend**: `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
**Backend**: `OPENAI_API_KEY`, `NOTION_ACCESS_TOKEN` (single workspace token), plus Supabase credentials

### Model Configuration
**Centralized LLM Configuration**: All AI models and prompts are configured in `backend/config/models.toml`:
- **Model Selection**: Configure embedding, chat, and summarization models with alternatives
- **Token Limits**: Set conservative limits for different operations
- **Performance Settings**: Configure batch sizes, delays, and retry policies
- **Prompt Templates**: Centralized prompt management for all LLM interactions
- **Future Services**: When adding new LLM services, add configuration sections to `models.toml`

**Pattern for New LLM Services**: Follow the established structure:
```toml
[models.new_service]
model = "model-name"
max_tokens = 1000
temperature = 0.5

[prompts.new_service]
system_prompt = "Your prompt template here with {placeholders}"
```

## Recent Architecture Changes

### Complete Workspace Concept Removal (v3.0) - December 2024
**MAJOR OVERHAUL**: Completely eliminated workspace concept from entire codebase:

#### ✅ **Design Decision**
After implementing a single workspace model (v2.0), we discovered lingering workspace_id references throughout the codebase. The decision was made to **completely remove the workspace concept** and redesign the application to support **ONLY ONE Notion workspace** with multiple databases.

#### 🔄 **What Changed (Commits: `012b3cc`, `f7f0ab5`)**

**Backend Complete Rewrite:**
- **`notion_webhook.py`**: Now uses `NOTION_ACCESS_TOKEN` from environment instead of workspace lookup
- **`bootstrap.py`**: Removed `workspace_id` parameters, operates directly on database configs
- **`document_processor.py`**: Removed all `workspace_id` parameters and method signatures
- **`database_schema_manager.py`**: Removed workspace storage, operates per-database only

**Database Schema Overhaul:**
- **DELETED**: `workspaces` table completely removed
- **REMOVED**: All `workspace_id` columns from all tables
- **UPDATED**: Vector search functions now take `database_ids[]` instead of `workspace_id`
- **NEW**: RLS policies updated for single-user, multi-database model

**Frontend Simplification:**
- **TypeScript types**: Completely rewritten to remove workspace references
- **Setup guide**: Updated with single-workspace warnings and new SQL schema
- **Environment**: Changed from workspace selection to single `NOTION_ACCESS_TOKEN`

#### 🎯 **Current Architecture (v3.0)**
- **Single Token**: Uses one `NOTION_ACCESS_TOKEN` for the entire application
- **Database-Centric**: All operations filter by `database_id`, never by workspace
- **No Workspace Tables**: Zero workspace management in database
- **Explicit Documentation**: Every file clearly states "ONLY ONE workspace"

#### 📋 **Migration Path**
- Old multi-workspace data needs manual database migration
- Environment variables changed from workspace configs to single token
- API endpoints now expect database IDs instead of workspace IDs

### Legacy Single Workspace Model (v2.0) - Deprecated
The previous v2.0 approach attempted to simplify multi-workspace to single workspace but retained workspace infrastructure. This has been completely superseded by v3.0's no-workspace model.

### Enhanced RAG with Contextual Retrieval (v4.0) - June 2025
**MAJOR ENHANCEMENT**: Implemented state-of-the-art RAG with Anthropic-style contextual retrieval and context enrichment:

#### ✅ **Key Enhancements**
- **Anthropic-Style Contextual Retrieval**: Each chunk includes AI-generated contextual descriptions explaining how it relates to the overall document
- **Content-Aware Processing**: Automatic detection and specialized chunking strategies for articles vs reading notes vs documentation
- **Adjacent Chunk Context Enrichment**: Search results include neighboring chunks for richer understanding
- **Dual Embedding Strategy**: Both content and contextual embeddings with weighted scoring (70% contextual, 30% content)
- **Positional Linking**: Maintains document narrative flow through prev/next chunk relationships

#### 🔄 **What Was Implemented**

**New Services:**
- **`content_type_detector.py`**: Detects document types using structural analysis
- **`chunking_strategies.py`**: Content-aware chunking (ArticleChunkingStrategy, ReadingNotesChunkingStrategy)
- **`contextual_chunker.py`**: Anthropic-style contextual retrieval with AI-generated context and summaries
- **`contextual_search_engine.py`**: Enhanced search with context enrichment and adjacent chunk retrieval

**Enhanced Database Schema:**
- **Enhanced `document_chunks`**: Added 9 new columns for contextual retrieval and positional linking
- **New SQL Functions**: `match_contextual_chunks`, `get_chunk_with_context`, `hybrid_contextual_search`
- **Contextual Metadata**: Chunk context, summaries, section hierarchy, and positional relationships

**Enhanced APIs:**
- **`/api/search`**: Enhanced with contextual retrieval and enriched metadata
- **`/api/search/hybrid`**: New endpoint combining documents and contextual chunks
- **Rich Response Metadata**: Context type, enrichment status, similarity scores, adjacent chunk info

#### 🎯 **Architecture (v4.0)**
- **Content-Type Aware**: Automatic detection of articles vs reading notes with appropriate processing
- **Contextual Embeddings**: Dual embedding strategy for better semantic understanding
- **Context Enrichment**: Adjacent chunks retrieved for fuller context during search
- **Enhanced Search Quality**: Weighted scoring with contextual understanding (70/30 split)
- **Preserved Narrative**: Document flow maintained through positional chunk linking

#### 📊 **Performance Improvements**
- **Better Relevance**: Contextual embeddings capture document relationships more accurately
- **Richer Results**: Adjacent chunks provide fuller understanding of search matches
- **Content Awareness**: Appropriate handling of different document types improves chunking quality
- **Enhanced Citations**: Rich metadata enables better result provenance and context understanding

#### 🧪 **Testing & Validation**
- **Component Tests**: All new services tested independently (`test_contextual_rag.py`)
- **Integration Tests**: Full pipeline validated with real Notion content
- **API Tests**: Enhanced search endpoints verified with contextual responses
- **Performance Tests**: Embedding generation and search quality validated

## Quality Guidelines

- Always run `npm run lint` before committing changes
- The application uses static export configuration, so ensure all features work without server-side rendering
- See `backend/docs/TESTING_BEST_PRACTICES.md` for detailed testing patterns

## Debugging Methodology

### 🐛 Efficient Backend API Debugging (Learned from Chat Sessions Bug)

**When encountering API errors (especially 404s), follow this systematic approach:**

#### 1. **Error Triage (First 2 minutes)**
- **Don't assume** 404 = routing issue
- **Test endpoints directly** with curl to see actual error responses
- **Differentiate** between:
  - True 404 (endpoint doesn't exist) 
  - 404 with custom message (endpoint exists, business logic fails)
  - 500 errors (server/database issues)

#### 2. **Trace the Data Flow (Next 5 minutes)**
```
Frontend → API Router → Business Logic → Database → Response
```
**Quick tests at each layer:**
- ✅ Router: `curl -X GET /health` (is server responding?)
- ✅ Endpoint: `curl -X GET /api/target-endpoint` (does route exist?)
- ✅ Database: Check if data operations actually work

#### 3. **Database Layer First for Data Issues**
**When seeing data-related errors, immediately check:**
- Are database methods actually implemented?
- Are they using the right APIs (SQL vs ORM vs API)?
- Test with simple queries first
- Check for silent failures (`return []` instead of throwing errors)

#### 4. **Architecture Consistency Check**
**Look for mixed patterns that cause issues:**
- Raw SQL + ORM calls in same codebase
- Missing database schema vs code expectations  
- Default values not being set properly

#### 5. **Component Isolation Testing**
**Test each piece independently:**
```bash
# Test database directly
curl -X POST /api/sessions/ -d '{"title": "test"}'

# Test specific operations
curl -X POST /api/sessions/{id}/messages -d '{"content": "test"}'

# Check what's actually in database
curl -X GET /api/sessions/recent
```

#### 🎯 Red Flags to Check Immediately

1. **"Silent Failures"**: Methods that catch exceptions and return empty results
2. **Mixed Architecture**: SQL queries + API calls in same codebase
3. **Missing Status Fields**: Default values not being set in database operations
4. **Unimplemented Methods**: Placeholder methods that look functional but aren't

#### ⚡ Time-Saving Commands

```bash
# Quick endpoint existence check
curl -I http://localhost:8000/api/endpoint

# Quick data verification
curl -X GET http://localhost:8000/api/endpoint | jq

# Database connection test
curl -X GET http://localhost:8000/health
```

**Key Learning**: Always **test the actual data flow** rather than **assuming where the problem is**. The chat sessions bug was caused by `execute_query()` returning empty results for unsupported queries, not routing issues.

## Future Considerations

### Potential Multi-Workspace Support (v4.0+)
The current no-workspace model (v3.0) could theoretically be extended to support multiple workspaces in the future, but this would require significant architectural changes:

**⚠️ IMPORTANT**: The workspace concept was completely removed in v3.0 for good reasons:
- Simplified codebase maintenance
- Reduced complexity in filtering and permissions
- Better performance with direct database-level operations
- Clearer user experience with single workspace focus

**If multi-workspace support is needed in the future:**
- Add `workspaces` table back to database schema
- Restore `workspace_id` columns to relevant tables
- Update all vector search functions to accept workspace filtering
- Rebuild frontend workspace selection UI
- Implement workspace-level permissions and access controls
- Update environment configuration to handle multiple tokens

**Recommendation**: Only implement multi-workspace if there is clear user demand, as the current single-workspace model significantly simplifies the application architecture and user experience.

## Documentation References
- **Setup Guide**: Visit `/setup` page for complete database schema and environment setup
- **RAG Improvements**: `backend/docs/RAG_IMPROVEMENT_ROADMAP.md` - Future enhancements
- **Multimedia Strategy**: `backend/docs/MULTIMEDIA_STRATEGY.md` - Media handling plans
- **Architecture History**: See this file's "Recent Architecture Changes" section for v3.0 workspace removal details