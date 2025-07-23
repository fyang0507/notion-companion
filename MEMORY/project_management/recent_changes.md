# Recent Changes

*Last Updated: 2025-07-23*

## 2025-07-23 - QA Self-Verification System for Evaluation Quality Assurance

• **Self-Verification Pipeline** - Implemented LLM-based verification: re-answers questions using expanded document context, compares via Rouge-L scoring (≥0.9 threshold)
• **Multilingual Rouge Scoring** - Custom tokenizer handling Chinese characters + English words for accurate Rouge-L calculation in mixed-language content
• **Chunk Context Expansion** - Smart growth strategy: starts from answer chunk, adds surrounding chunks alternately until token limit (respects gpt-4.1 context window)

## 2025-07-22 - Simple Rate Limit Retry Logic for Evaluation Pipeline

• **OpenAI API Rate Limit Handling** - Simple retry logic: wait 1 minute on 429 errors, max 3 attempts during batch question generation and QA pair verification

## 2025-07-16 - Memory System Migration

• **MEMORY/ Structure Created** - Implemented role-based documentation system replacing scattered docs
• **Product Documentation** - Created overview.md, roadmap.md, decisions.md with human-managed approach
• **Engineering Documentation** - Bootstrapped architecture.md, setup.md, standards.md from existing sources

## Backend Restructuring Complete

• **Modular 4-Module Architecture** - Migrated from monolithic to modular structure (ingestion, storage, rag, api)
• **Strategy Pattern Implementation** - Pluggable retrieval strategies with dynamic registration
• **Experiment Framework** - A/B testing and benchmarking capabilities with loose coupling

## Evaluation Pipeline Setup

• **Comprehensive Evaluation Framework** - Built system for RAG retrieval performance assessment
• **Question Generation System** - Multi-language support with content filtering and batch processing
• **Retrieval Evaluation System** - Standard IR metrics (Recall@K, Precision@K, MRR, NDCG) with API integration

---

*Note: Changes older than 30 days should be archived periodically*