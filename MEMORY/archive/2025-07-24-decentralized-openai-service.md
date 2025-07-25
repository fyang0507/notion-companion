# Decentralized OpenAI Service Architecture

*Task Type: Tech Debt Reduction & Refactoring*  
*Date: 2025-07-24*

## Summary
Refactored OpenAI service from centralized global configuration to decentralized parameter-based architecture to enable flexible experiment configuration without affecting production services.

## Problem Addressed
- OpenAI service was misplaced in `ingestion/services/` but used across entire codebase
- Tight coupling to `shared/config/models.toml` prevented experiment-specific parameter tuning
- Inflexible for benchmark experiments requiring different embedding models/dimensions
- Global singleton pattern prevented multiple configurations

## Solution Implemented
1. **New Decentralized Service** (`shared/services/openai_service.py`)
   - Stateless methods accepting config parameters per call
   - No global configuration dependency
   - Pure API wrapper focused on OpenAI interactions

2. **Enhanced Experiment Configuration** (`evaluation/config/benchmark.toml`)
   - Centralized embedding config: model, dimensions, batch_size, delays
   - Chat configuration for future evaluations
   - Clear parameter ownership per experiment

3. **Updated Components**
   - Benchmark runner uses experiment-specific config
   - RAG strategy accepts embedding config as parameter  
   - Legacy service preserved with deprecation markers

## Architecture Changes
```
BEFORE: Global Config → Singleton Service → All Consumers
AFTER: Per-Component Config → Stateless Service → Flexible Usage
```

## Key Files Modified
- `shared/services/openai_service.py` (new decentralized service)
- `evaluation/config/benchmark.toml` (enhanced config structure)
- `evaluation/scripts/run_benchmark_basic_rag.py` (updated to use new service)
- `rag/strategies/basic_similarity_strategy.py` (accepts config parameter)
- `ingestion/services/openai_service.py` (deprecated global config)

## Impact
- ✅ Experiment flexibility: Easy embedding parameter tuning per benchmark
- ✅ Production stability: Legacy services unchanged
- ✅ Clean architecture: Services handle API calls, runners handle config
- ✅ No global state: Multiple configurations can coexist
- ✅ Testing verified: Offline ingestion (364 chunks) and online evaluation successful

## Technical Debt Resolved
- Removed improper service placement in ingestion module
- Eliminated global configuration coupling
- Resolved singleton pattern limitations
- Enabled proper separation of concerns