# Recent Changes

*Last Updated: 2025-07-29*

## 2025-07-29 - Factory Pattern Refactoring for RAG Benchmark System

• **Config-Driven Strategy Selection** - Replaced hard-coded factory functions with registry-based factory pattern for chunking and retrieval strategies
• **Modular Strategy Management** - Created ChunkingStrategyFactory and RetrievalStrategyFactory classes with pluggable architectures 
• **Enhanced Configuration Structure** - Extended benchmark.toml with [strategies.chunking] and [strategies.retrieval] sections for declarative strategy selection

## 2025-07-24 - Interactive Evaluation Results Dashboard

• **Streamlit + Plotly Visualization** - Built interactive web dashboard for exploring aggregated evaluation results with multi-select filtering
• **Complete Metadata Exposure** - All evaluation parameters (QA models, embedding models, rouge thresholds, chunking config) available as toggle filters
• **Dynamic Line Charts** - Precision, recall, ndcg metrics vs K-values with MRR values displayed as metric cards

## 2025-07-24 - Retrieval Metrics and end-to-end evaluation pipeline for benchmark experiments

• Metrics (precision@k, recall@k, NDCG@k, MRR) now fully config-driven, multi-chunk aware, and support flexible similarity thresholds
• Built and verified end-to-end evaluation pipeline for benchmark experiments

## 2025-07-24 - Centralized Token Counting Utility

• **Shared Token Counter** - Created shared/utils/token_counter.py with tiktoken-based token counting for consistent calculations across all modules

## 2025-07-24 - Decentralized OpenAI Service Architecture

• **Service Decentralization** - Moved OpenAI service from ingestion/services/ to shared/services/ with stateless, config-agnostic design
• **Experiment-Specific Configuration** - Enabled flexible embedding parameter tuning (model, dimensions, batch_size) via benchmark.toml without affecting global config
• **Global Config Elimination** - Removed dependency on shared/config/models.toml for benchmark experiments, each component now owns its configuration

## 2025-07-23 - RAG Pipeline Architecture Clean Slate

• **Concrete Implementation Removal** - Removed all concrete implementations from ingestion/, rag/, and storage/ modules to create clean experimental foundation

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