# RAG Evaluation Pipeline Technical Specification

*Last Updated: 2025-07-24*

## Architecture Overview

The evaluation system consists of modular services orchestrated through configurable scripts, supporting both online (Supabase) and offline evaluation modes.

### Component Stack
```
Orchestration: run_benchmark_basic_rag.py
├── Data Pipeline: collect_database.py → chunking.py
├── QA Generation: generate_questions.py → verify_qa_pairs.py  
├── Evaluation: retrieval_evaluator.py
└── Services: question_generator.py, qa_self_verifier.py
```

## How To Use

### Quick Start - Full Pipeline (qa data available)
```bash
cd evaluation/

# Complete end-to-end benchmark
python scripts/run_benchmark_basic_rag.py --full --qa-data data/verified_qa.json

# Individual steps
python scripts/run_benchmark_basic_rag.py --clear-data    # Clean slate
python scripts/run_benchmark_basic_rag.py --ingest       # Data processing
python scripts/run_benchmark_basic_rag.py --evaluate --qa-data data/verified_qa.json
```

### QA Dataset Preparation
```bash
# Step 1: Collect data from Notion databases
python scripts/collect_database.py --config config/database.toml

# Step 2: Chunk documents into manageable pieces
python scripts/chunking.py --config config/chunking.toml

# Step 3: Generate questions from chunks
python scripts/generate_questions.py --config config/question_generation.toml

# Step 4: Self-verify QA pairs quality
python scripts/verify_qa_pairs.py --input data/generated_qa.json --output data/verified_qa.json
```

## Configuration Deep Dive

### Evaluation Metrics (`benchmark.toml`)
```toml
[evaluation]
k_values = [1, 3, 5, 10]                    # Top-K retrieval evaluation
metrics = ["precision", "recall", "mrr", "ndcg"]  # IR metrics to compute
rouge_threshold = 0.25                      # Answer relevance threshold
```

### Multilingual Chunking (`chunking.toml`)
- **Sentence Splitter**: Unicode punctuation detection for Chinese/English/French
- **Quote Handling**: Supports ASCII quotes, Chinese quotes (「」), French guillemets (« »)
- **Semantic Merging**: Cosine similarity-based chunk combination with token limits

### Question Generation (`question_generation.toml`)
- **Adaptive Question Count**: Token-based heuristics (1-3 questions per chunk based on length)
- **Content Filtering**: Excludes headers, short questions, and low-token chunks
- **Rate Limiting**: Built-in retry logic for OpenAI API 429 errors

## Key Technical Features

### Self-Verification Pipeline
Expands chunk context iteratively until token limit, re-answers questions, validates using Rouge-L ≥0.9 threshold with custom Chinese+English tokenization.

### Retrieval Evaluation
Multi-chunk aware metrics using Rouge-L similarity between retrieved chunks and ground truth answers, supporting flexible similarity thresholds.

### Caching System
Sentence-level embedding persistence enables 100% cache hit rates during parameter tuning, reducing API costs and iteration time by 5-10x.

## Output Format

Evaluation generates structured JSON reports with aggregated metrics:
```json
{
  "precision@1": 0.85, "recall@10": 0.92, "mrr": 0.76, "ndcg@5": 0.81,
  "config": {...}, "timestamp": "2025-07-24T...", 
  "individual_results": [...], "retrieval_snapshot": [...]
}
```

Results include per-question breakdowns and retrieval snapshots for detailed analysis and cross-configuration comparison. 