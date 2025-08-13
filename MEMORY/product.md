# Product Documentation

*Last Updated: 2025-08-13*

---

## Product Overview

### Vision

Notion Companion is an open-source alternative to Notion AI, providing intelligent search and chat capabilities with agentic RAG technology optimized for single-user, multi-database workflows.

### Core Value Proposition

#### Open-Source Notion AI Alternative
- **Cost-Effective**: Eliminate recurring Notion AI subscription costs, pay only for API usage
- **Privacy-First**: Keep your data in your own infrastructure
- **Transparent**: Full control over AI models, prompts, and processing logic

#### Customizable Agentic RAG with Advanced Retrieval
- Experiment with different embedding, retrieval, and processing strategies and configurations
- Built-in Evaluation Framework to help choose the best

### Target Users

Intelligent individuals seeking a powerful, customizable alternative to Notion AI with full control over their data and AI processing pipeline.

---

## Product Decisions

- **Single Workspace Only** - Focus on one primary Notion workspace with multiple databases
- **Single User** - Individual tool, not team collaboration, no authentication, log-in management
- **Minimal Code-level Testing** - limited testing and CI/CD, rely on live testing
- **Evaluation-driven** - Experiment with different embedding, retrieval, and processing strategies and configurations to find the best one

---

## Product Roadmap

### [WIP] v0.7 Experiments
- Experiment with different embedding, retrieval, and processing strategies and configurations

### [DONE] v0.6 Set up memory system
- Unify memory system under MEMORY module for coding agents (Cursor, Claude Code)

### [DONE] v0.5 Backend restructure
- Separate monolithic backend into ingestion, storage, rag, and api modules

### [DONE] v0.4 Set up evaluation system
- Generate evaluation dataset

### [DONE] v0.3 Codebase overhaul
- BE overhaul: unify taxonomy, single workspace schema redesign
- FE enhancement: MVP metadata filtering, recent chat section, chat conclusion and resume capability

### [DONE] v0.2 MVP using real data
- Switch backend to Python FastAPI
- Add Notion database sync with Notion API, Supabase
- Basic end-to-end RAG pipeline

### [DONE] v0.1 Prototyped with Bolt
- Basic webapp interfaces with mock ups