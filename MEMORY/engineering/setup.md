# Development Setup

*Last Updated: 2025-07-21*

## Prerequisites

- Node.js 18+
- Python 3.8+
- Notion workspace with admin access

## Quick Start

### Installation
```bash
# Install all dependencies
pnpm install

# Python dependencies (root level)
uv sync
```

### Environment Configuration

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

## Development Commands

### Basic Development
- `pnpm run dev` - Frontend only (port 3000)
- `pnpm run backend` - Backend only (port 8000)
- `pnpm run dev:full` - Both frontend and backend concurrently

### Build & Quality
- `pnpm run build` - Build Next.js for production
- `pnpm run lint` - Run ESLint validation
- `pnpm run pre-commit-test` - **OPTIONAL: Full test suite before significant commits**

### Python Environment (uv Package Manager)
**CRITICAL: Always use uv for Python operations**
```bash
uv sync                          # Install dependencies
uv add package_name              # Add new dependency
uv add --dev package_name        # Add dev dependency
uv remove package_name           # Remove dependency
uv run python script.py          # Run Python scripts
```

### Database & Synchronization
```bash
# Sync Notion databases with enhanced contextual processing
uv run python ingestion/scripts/sync_databases.py

# Test sync configuration
uv run python ingestion/scripts/sync_databases.py --dry-run

# Test model configuration
uv run python shared/config/model_config.py
```

## Component Testing (No Backend Required)
```bash
# Database connectivity test (5 seconds)
uv run python -c "import asyncio; from storage.database import init_db; asyncio.run(init_db()); print('✓ DB OK')"
```

## Configuration Files

### Core Configuration
- `package.json` - Node.js dependencies and scripts
- `pyproject.toml` - Python dependencies with uv
- `shared/config/` - Centralized AI model and database configurations

### Schema Management
- `storage/schema/schema.sql` - Full database schema
- `storage/schema/drop_schema.sql` - Reset database schema