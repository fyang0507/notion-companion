# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Notion Companion is a production-ready AI-powered knowledge assistant that connects to your primary Notion workspace, providing intelligent search and chat capabilities with real-time synchronization. It's a full-stack RAG (Retrieval-Augmented Generation) application optimized for single-user, multi-database workflows.

## Tech Stack

**Frontend**: Next.js 13.5.1 with App Router, TypeScript, Tailwind CSS, shadcn/ui components
**Backend**: FastAPI (Python with uv package manager), Supabase (PostgreSQL + pgvector), OpenAI integration
**Key Features**: Vector search, streaming chat, Notion webhook synchronization, single workspace with multi-database filtering

## Development & Testing

### Basic Development Commands
- `npm run dev` - Frontend only (port 3000)
- `npm run backend` - Backend only (port 8000) 
- `npm run dev:full` - Both frontend and backend concurrently
- `make dev` - Alternative using Makefile
- `npm run build` - Build Next.js for production
- `npm run lint` - Run ESLint validation (ALWAYS run before committing)

### Backend Operations
- `cd backend && .venv/bin/python scripts/sync_databases.py` - Sync Notion databases
- `cd backend && .venv/bin/python scripts/sync_databases.py --dry-run` - Test sync configuration
- `cd backend && .venv/bin/python scripts/model_config_demo.py` - Test model configuration

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
- Deploy `backend/schema.sql` in Supabase before first sync
- **See `backend/docs/SCHEMA_DEPLOYMENT_TODO.md` for missing database functions**

## Architecture Patterns

### Full-Stack Structure
- **Frontend**: `app/` directory uses Next.js App Router with static export
- **Backend**: `backend/` directory contains FastAPI application with routers and services
- **Components**: Extensive shadcn/ui component library in `components/ui/`
- **Shared Types**: TypeScript definitions in `types/` directory

### RAG Implementation
- Vector embeddings stored in Supabase pgvector
- Configurable OpenAI models via `backend/config/models.toml`
- AI document summarization for large documents (handles 30k+ tokens)
- Hybrid search: document-level (summaries) + chunk-level (detailed content)
- Intelligent chunking with semantic boundary preservation
- Server-Sent Events for streaming chat responses

### API Architecture
- FastAPI routers in `backend/routers/` for organized endpoints
- Service layer in `backend/services/` for business logic
- Pydantic models for request/response validation
- Main endpoints: `/api/chat` (streaming), `/api/search` (vector), `/api/notion/webhook`

### Database Schema
Enhanced V2 schema with hybrid metadata approach:
- Core tables: `workspaces`, `documents`, `document_chunks`, `document_metadata`, `database_schemas`
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
**Backend**: `OPENAI_API_KEY`, `NOTION_ACCESS_TOKEN`, plus Supabase credentials

### Model Configuration
Configure models in `backend/config/models.toml`:
- Set `ENVIRONMENT=development` for cheaper models in dev
- Set `ENVIRONMENT=production` for higher quality models in prod
- Modify model selections directly in the TOML file

## Recent Architecture Changes

### Single Workspace Model (v2.0)
The application has been simplified from a multi-workspace to a single workspace architecture:

- **Frontend**: Removed workspace selection complexity, now focuses on database-level filtering
- **Database**: Single workspace per user with multiple databases within that workspace
- **Filtering**: Chat and search filters now work at the database level rather than workspace level
- **Hooks**: `useNotionConnection` manages single workspace, `useNotionDatabases` handles database listing
- **UI**: Sidebar shows connected databases with document counts instead of multiple workspaces

### Key Components Updated
- `ChatInterface` - Now uses real database connections instead of placeholder data
- `ChatFilterBar` - Updated terminology from "workspaces" to "databases"
- `Sidebar` - Shows actual connected databases with real-time data
- Database queries - Fixed for single-user schema without user_id filtering

## Quality Guidelines

- Always run `npm run lint` before committing changes
- The application uses static export configuration, so ensure all features work without server-side rendering
- See `backend/docs/TESTING_BEST_PRACTICES.md` for detailed testing patterns

## Future Considerations

### Multi-Workspace Support
The current single workspace model could be extended to support multiple workspaces in the future:
- Add user_id back to workspace queries
- Restore workspace selection UI components  
- Update filtering logic to handle workspace + database combinations
- Consider workspace-level permissions and access controls

This simplified model was chosen for initial deployment and can be expanded based on user needs.

## Documentation References
- **Schema Deployment**: `backend/docs/SCHEMA_DEPLOYMENT_TODO.md` - Missing database functions
- **RAG Improvements**: `backend/docs/RAG_IMPROVEMENT_ROADMAP.md` - Future enhancements
- **Multimedia Strategy**: `backend/docs/MULTIMEDIA_STRATEGY.md` - Media handling plans