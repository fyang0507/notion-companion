# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Notion Companion is a production-ready AI-powered knowledge assistant that connects to Notion workspaces, providing intelligent search and chat capabilities with real-time synchronization. It's a full-stack RAG (Retrieval-Augmented Generation) application.

## Tech Stack

**Frontend**: Next.js 13.5.1 with App Router, TypeScript, Tailwind CSS, shadcn/ui components
**Backend**: FastAPI (Python with uv package manager), Supabase (PostgreSQL + pgvector), OpenAI integration
**Key Features**: Vector search, streaming chat, Notion webhook synchronization, multi-workspace support

## Development Commands

### Start Development
- `npm run dev` - Frontend only (port 3000)
- `npm run backend` - Backend only (port 8000) 
- `npm run dev:full` - Both frontend and backend concurrently
- `make dev` - Alternative using Makefile

### Backend Operations
- `cd backend && .venv/bin/python scripts/sync_databases.py` - Sync Notion databases
- `cd backend && .venv/bin/python scripts/sync_databases.py --dry-run` - Test sync configuration
- `cd backend && .venv/bin/python scripts/model_config_demo.py` - Test model configuration

### Build & Lint
- `npm run build` - Build Next.js for production
- `npm run lint` - Run ESLint validation

### Setup
- `make install` - Install both Python (uv) and Node (pnpm) dependencies
- `make setup-env` - Create environment file template
- Deploy `backend/schema.sql` in Supabase before first sync

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
- Custom hooks for state management (`useAuth`, `useToast`)
- Theme switching via next-themes (system/light/dark)
- Responsive design with mobile-first approach

## Environment Setup

Frontend requires: `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
Backend requires: `OPENAI_API_KEY`, `NOTION_ACCESS_TOKEN`, plus Supabase credentials

### Model Configuration
Configure models in `backend/config/models.toml`:
- Set `ENVIRONMENT=development` for cheaper models in dev
- Set `ENVIRONMENT=production` for higher quality models in prod
- Modify model selections directly in the TOML file

## Testing & Quality

Always run `npm run lint` before committing changes.
The application uses static export configuration, so ensure all features work without server-side rendering.