# Document Chunking Scripts

This directory contains scripts to convert downloaded documents into chunks using the multilingual chunker.

## Files

- `chunk_documents.py` - Main script that processes JSON documents and creates chunks
- `test_chunking.py` - Test script to verify the chunking functionality works
- `view_chunks.py` - Utility script to view generated chunks without large embeddings

## Usage

### 1. Test the Chunking System

First, verify that the chunking system works correctly:

```bash
cd evaluation
python scripts/test_chunking.py
```

This will test the multilingual chunker with sample Chinese text and display the results.

### 2. Process Documents

Process all JSON documents in the `data/` directory:

```bash
cd evaluation
python scripts/chunk_documents.py
```

This will:
- Find all `.json` files in the `data/` directory
- Load each document's content
- Use the multilingual chunker to create semantic chunks
- Generate embeddings for each chunk
- Save results to `data/processed/` directory

### 3. View Results

Examine the generated chunks:

```bash
cd evaluation
python scripts/view_chunks.py
```

This displays a summary of the chunks without the large embedding vectors.

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
    "created_at": "2025-07-07T22:25:04.197859",
    "config": { ... }
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
      "created_at": "2025-07-07T22:25:04.197859"
    }
  ]
}
```

## Results Summary

From the test run with `768446a113_20250707_135150.json`:

- **Total chunks**: 920
- **Total tokens**: 45,440
- **Average tokens per chunk**: 49.4

### Per Document Statistics:

1. **高善文国投证券2025年度投资策略会：2025年可能是一个重要的转折点**
   - Chunks: 86
   - Total tokens: 3,982
   - Average tokens/chunk: 46.3

2. **付鹏在汇丰银行内部活动演讲**
   - Chunks: 606
   - Total tokens: 30,966
   - Average tokens/chunk: 51.1

3. **历史的垃圾时间**
   - Chunks: 228
   - Total tokens: 10,492
   - Average tokens/chunk: 46.0

## Features

The multilingual chunker provides:

1. **Robust sentence boundary detection** for Chinese, English, and French
2. **Intelligent quotation mark handling** for various quote types
3. **Semantic similarity merging** of adjacent sentences
4. **Token-aware chunk sizing** to respect model limits
5. **Context preservation** with before/after context
6. **Full embedding generation** for similarity search
7. **Comprehensive metadata** tracking

## Dependencies

- `tiktoken` - Token counting and encoding
- `numpy` - Numerical operations
- `tomllib` - Configuration file parsing
- Standard Python libraries (json, logging, asyncio, etc.)

## Notes

- The chunker uses mock embeddings for testing (random vectors)
- For production use, replace `MockEmbeddingService` with a real embedding service
- Embeddings are generated with 1536 dimensions (OpenAI standard)
- Large output files (~39MB) are due to embedding vectors
- All chunks include metadata for traceability and debugging 