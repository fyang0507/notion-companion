# Notion Companion Documentation

This directory contains comprehensive documentation for the Notion Companion project. All documentation has been consolidated here for easy access and maintenance.

## 📖 Documentation Index

### Development & Workflow
- **[Development Workflow](DEVELOPMENT_WORKFLOW.md)** - Complete guide to development practices, testing, and pre-commit workflows
- **[Contextual RAG Implementation](CONTEXTUAL_RAG_IMPLEMENTATION.md)** - Technical overview of the enhanced RAG system with Anthropic-style contextual retrieval
- **[RAG Improvement Roadmap](RAG_IMPROVEMENT_ROADMAP.md)** - Future enhancements and optimization plans
- **[TODO](TODO.md)** - Current development tasks and planned improvements

### Backend Documentation
- **[Backend Setup](backend/BACKEND_SETUP.md)** - Backend installation, configuration, and development setup
- **[Data Ingestion Pipeline](backend/DATA_INGESTION_PIPELINE.md)** - How data flows from Notion into the vector database
- **[Notion Sync User Guide](backend/NOTION_SYNC_USER_GUIDE.md)** - Guide for syncing and managing Notion databases
- **[Multimedia Strategy](backend/MULTIMEDIA_STRATEGY.md)** - Handling images, files, and multimedia content
- **[Chat Session Migration](backend/CHAT_SESSION_STATUS_MIGRATION.md)** - Database migration procedures for chat sessions
- **[Configuration Guide](backend/CONFIG_GUIDE.md)** - Model configuration and settings management

### Frontend Documentation
- **[Frontend docs coming soon]** - Frontend-specific documentation will be added here

## 🚀 Quick Start

1. **New Developers**: Start with [Development Workflow](DEVELOPMENT_WORKFLOW.md)
2. **Backend Setup**: Follow [Backend Setup](backend/BACKEND_SETUP.md)
3. **Understanding RAG**: Read [Contextual RAG Implementation](CONTEXTUAL_RAG_IMPLEMENTATION.md)

## 📁 Project Structure

The Notion Companion project follows this structure:

```
notion-companion/
├── docs/                    # 📚 All documentation (this folder)
├── app/                     # 🎨 Next.js frontend application
├── backend/                 # ⚙️ FastAPI backend services
├── components/              # 🧱 Reusable React components
├── hooks/                   # 🪝 Custom React hooks
├── lib/                     # 📚 Utility libraries
├── scripts/                 # 🔧 Development and test scripts
├── types/                   # 📝 TypeScript type definitions
├── CLAUDE.md               # 🤖 Claude Code project instructions
└── README.md               # 📖 Project overview
```

## 🧪 Testing & Quality

Before making any commits, always run:

```bash
pnpm run pre-commit-test
```

This ensures:
- ✅ TypeScript compilation passes
- ✅ ESLint validation passes
- ✅ Production build succeeds
- ✅ All pages generate correctly

See [Development Workflow](DEVELOPMENT_WORKFLOW.md) for detailed testing procedures.

## 🔗 External Resources

- **[Project Repository](https://github.com/your-org/notion-companion)** - Main GitHub repository
- **[Notion API Documentation](https://developers.notion.com/)** - Official Notion API docs
- **[OpenAI API Documentation](https://platform.openai.com/docs)** - OpenAI integration guide
- **[Supabase Documentation](https://supabase.com/docs)** - Database and vector search

## 📝 Contributing to Documentation

When adding new documentation:

1. **Place it in the appropriate subdirectory** (`backend/`, `frontend/`, or root `docs/`)
2. **Update this README.md** to include a link to your new documentation
3. **Use clear, descriptive filenames** (e.g., `FEATURE_NAME_GUIDE.md`)
4. **Include a brief description** in the Documentation Index section above
5. **Follow the established format** with clear headings and sections

## 🏗️ Architecture Overview

Notion Companion is a full-stack RAG (Retrieval-Augmented Generation) application:

- **Frontend**: Next.js 13.5.1 with App Router, TypeScript, Tailwind CSS
- **Backend**: FastAPI with Python, using uv package manager
- **Database**: Supabase (PostgreSQL + pgvector for similarity search)
- **AI Integration**: OpenAI for embeddings and chat completions
- **RAG Enhancement**: Anthropic-style contextual retrieval with context enrichment

For detailed technical information, see the individual documentation files listed above.

---

**Last Updated**: December 2024  
**Maintained By**: Development Team  
**Questions?** Check the [Development Workflow](DEVELOPMENT_WORKFLOW.md) or create an issue in the repository.