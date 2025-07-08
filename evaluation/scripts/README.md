# Document Chunking Scripts

This directory contains scripts to convert downloaded documents into chunks using the multilingual chunker, with advanced caching capabilities for fast parameter tuning.

## Files

- `chunk_documents.py` - Original script that processes JSON documents and creates chunks
- `chunk_documents_cached.py` - **Enhanced script with sentence-level embedding caching**
- `tune_chunking_params.py` - **Parameter tuning script for Step 3 optimization**
- `test_chunking.py` - Test script to verify the chunking functionality works
- `view_chunks.py` - Utility script to view generated chunks without large embeddings

## Three-Step Evaluation Workflow

### Step 1: Download Data ✅
Download documents from Notion and save offline copies (already completed).

```bash
# Data is available in evaluation/data/*.json
ls data/
# 768446a113_20250707_135150.json
```

### Step 2: Sentence-Level Embedding Caching ⚡
Build a cache of sentence-level embeddings to speed up parameter tuning.

```bash
cd evaluation

# Option A: Precompute sentence embeddings only (recommended for Step 3 prep)
python scripts/chunk_documents_cached.py --precompute

# Option B: Normal chunking with caching
python scripts/chunk_documents_cached.py

# Check cache status
python scripts/chunk_documents_cached.py --cache-info
```

**Cache Performance**: After precomputation, you'll have ~914 sentence embeddings cached (38MB) with 100% hit rate on subsequent runs.

### Step 3: Fast Parameter Tuning 🚀
Experiment with different chunk merging parameters using cached embeddings.

```bash
cd evaluation

# Quick comparison of different configurations
python scripts/tune_chunking_params.py --compare

# Full parameter sweep (tests multiple combinations)
python scripts/tune_chunking_params.py

# Test single configuration
python scripts/tune_chunking_params.py --single-test
```

**Speed Improvement**: Parameter tuning is 5-10x faster with caching since sentence embeddings are reused across experiments.

## Caching System Features

### Sentence Embedding Cache
- **File-based persistence**: `data/cache/sentence_embeddings.json`
- **In-memory acceleration**: Fast lookup during processing
- **Content-based hashing**: Sentences are cached by content hash for reuse across documents
- **Statistics tracking**: Cache hit/miss rates and performance metrics

### Cache Management
```bash
# View cache information
python scripts/chunk_documents_cached.py --cache-info

# Clear cache (start fresh)
python scripts/chunk_documents_cached.py --clear-cache

# Precompute embeddings for all documents
python scripts/chunk_documents_cached.py --precompute
```

### Cache Benefits
1. **Development Speed**: No need to regenerate embeddings when tuning parameters
2. **Cost Savings**: Reduces API calls to embedding services
3. **Consistency**: Same embeddings used across parameter experiments
4. **Scalability**: Cache persists across sessions and can be shared

## Parameter Tuning Examples

### Configuration Comparison Results
```
Configuration | Chunks | Avg Size | Merge Ratio | Cache Hit
Conservative  |   920  |   49.4   |    1.00     |   100.0%
Moderate      |   233  |  197.6   |    0.25     |   100.0%  
Aggressive    |   155  |  297.5   |    0.17     |   100.0%
Base          |   920  |   49.4   |    1.00     |   100.0%
```

**Key Metrics Explained**:
- **Merge Ratio**: chunks/sentences (lower = more merging)
- **Avg Size**: Average tokens per chunk
- **Cache Hit**: Percentage of embeddings loaded from cache

### Parameter Effects
- **similarity_threshold**: Higher values (0.8) = less merging, more chunks
- **max_merge_distance**: How many sentences ahead to consider for merging  
- **max_chunk_size**: Maximum tokens per chunk (hard limit)

## Configuration

The chunking behavior is controlled by `config/chunking_config.toml`:

- **Sentence splitting**: Handles Chinese, English, and French punctuation
- **Quote handling**: Properly manages various quotation mark types
- **Semantic merging**: Groups similar adjacent sentences
- **Token limits**: Ensures chunks don't exceed token limits

Configuration is loaded using the `ConfigLoader` class from `utils/config_loader.py`, which provides:
- Configuration validation and caching
- Automatic path resolution for config files
- Type-safe configuration loading

## Output Format

The chunking script generates JSON files with the following structure:

```json
{
  "metadata": {
    "total_chunks": 920,
    "created_at": "2025-07-08T09:40:07.245820",
    "config": { ... },
    "cache_info": {
      "cached_sentences": 914,
      "cache_file_size_mb": 37.94,
      "stats": {
        "total_cache_hits": 920,
        "hit_rate": 1.0
      }
    }
  },
  "chunks": [
    {
      "document_id": "1559782c-4f4a-802b-8407-c97358344f2a",
      "document_title": "高善文国投证券2025年度投资策略会：2025年可能是一个重要的转折点",
      "chunk_id": "1559782c-4f4a-802b-8407-c97358344f2a_chunk_0",
      "content": "# 2025年可能是一个重要的转折点...",
      "start_sentence": 0,
      "end_sentence": 0,
      "embedding": [0.123, 0.456, ...],
      "context_before": "",
      "context_after": "",
      "token_count": 157,
      "created_at": "2025-07-08T09:40:07.245820"
    }
  ]
}
```

## Performance Results

### Baseline (Step 2 Complete)
- **Total documents**: 3
- **Total sentences**: 920 (914 unique)
- **Cache size**: 37.9 MB
- **Processing time**: ~2 seconds for precomputation

### Parameter Tuning (Step 3)
- **Cache hit rate**: 100% (after precomputation)
- **Speed improvement**: 5-10x faster than regenerating embeddings
- **Parameter space**: Can test dozens of configurations in seconds
- **Cost savings**: Zero embedding API calls during tuning

## Features

The multilingual chunker with caching provides:

1. **Robust sentence boundary detection** for Chinese, English, and French
2. **Intelligent quotation mark handling** for various quote types
3. **Semantic similarity merging** of adjacent sentences
4. **Token-aware chunk sizing** to respect model limits
5. **Context preservation** with before/after context
6. **Full embedding generation** for similarity search
7. **Comprehensive metadata** tracking
8. **🆕 Sentence-level embedding caching** for fast parameter tuning
9. **🆕 Advanced parameter sweep capabilities** with statistical analysis
10. **🆕 Configuration comparison tools** for optimization

## Dependencies

- `tiktoken` - Token counting and encoding
- `numpy` - Numerical operations  
- `tomllib` - Configuration file parsing
- Standard Python libraries (json, logging, asyncio, etc.)

## Workflow Recommendations

### For Development & Testing
1. Use `--precompute` to build the sentence embedding cache
2. Use `tune_chunking_params.py --compare` to test different configurations
3. Use `--cache-info` to monitor cache performance
4. Clear cache with `--clear-cache` when changing embedding models

### For Production Evaluation
1. Run full parameter sweep with `tune_chunking_params.py`
2. Analyze results in `data/tuning_results.json`
3. Select optimal parameters based on your quality metrics
4. Apply selected parameters to full dataset

### Cache Management Tips
- Cache is content-based and works across different documents
- Cache persists between script runs for development efficiency
- Cache includes statistics for performance monitoring
- Large cache files (~38MB for 900 sentences) - plan storage accordingly

## Notes

- The chunker uses mock embeddings for testing (random vectors)
- For production use, replace `MockEmbeddingService` with a real embedding service
- Embeddings are generated with 1536 dimensions (OpenAI standard)
- Cache files can be large but provide significant speed improvements
- All chunks include metadata for traceability and debugging 