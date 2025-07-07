# Evaluation System Architecture Plan

## Overview

This document outlines the design and architecture for building an evaluation system for the Notion Companion agentic RAG system. The evaluation pipeline will create high-quality question-answer datasets from Notion content, with specialized handling for Chinese text.

## High-Level Workflow

1. **Data Collection**: Pull data from Notion and store offline
2. **Chunking**: Sentence-level chunking with semantic merging for Chinese text
3. **Question Generation**: Generate questions using LLM with context
4. **Self-Verification**: Filter QA pairs using Rouge-L scoring
5. **Dataset Storage**: Store final evaluation datasets

## Directory Structure

```
evaluation/
├── README.md                          # Documentation and usage guide
├── config/
│   ├── evaluation.toml                # Evaluation-specific configuration
│   └── chunking_config.toml           # Chinese text chunking parameters
├── data/
│   ├── raw/                           # Raw Notion data offline storage
│   ├── processed/                     # Processed chunks and embeddings
│   └── datasets/                      # Final evaluation datasets
├── scripts/
│   ├── collect_data.py                # Data collection from Notion
│   ├── process_chunks.py              # Chunking and embedding pipeline
│   ├── generate_questions.py          # Question generation pipeline
│   ├── verify_qa_pairs.py             # Self-verification filter
│   └── build_dataset.py               # Final dataset assembly
├── services/
│   ├── __init__.py
│   ├── data_collector.py              # Offline data collection service
│   ├── chinese_chunker.py             # Chinese sentence chunking + merging
│   ├── question_generator.py          # LLM-based question generation
│   ├── verification_engine.py         # Self-verification with Rouge-L
│   └── dataset_manager.py             # Dataset storage and management
├── models/
│   ├── __init__.py
│   ├── evaluation_models.py           # Pydantic models for evaluation data
│   └── dataset_models.py              # Dataset structure models
├── utils/
│   ├── __init__.py
│   ├── chinese_text_utils.py          # Chinese text processing utilities
│   ├── similarity_metrics.py          # Semantic similarity and Rouge-L
│   └── export_utils.py                # Dataset export utilities
└── tests/
    ├── __init__.py
    ├── test_chunker.py
    ├── test_question_gen.py
    └── test_verification.py
```

## Core Components Design

### 1. Data Collection Service (`services/data_collector.py`)

**Purpose**: Offline Notion data collection borrowing from existing `sync_databases.py`

**Key Features**:
- Offline Notion data storage (JSON/pickle format)
- Incremental updates support
- Chinese content encoding handling
- Document metadata preservation
- Configurable database selection

**Interface**:
```python
class DataCollector:
    async def collect_databases(self, database_ids: List[str]) -> CollectionResult
    async def incremental_update(self, since: datetime) -> CollectionResult
    def export_to_offline_storage(self, data: Dict, format: str) -> Path
```

### 2. Chinese Chunker (`services/chinese_chunker.py`)

**Purpose**: Sentence-level chunking with semantic merging for Chinese text

**Key Features**:
- Chinese sentence segmentation (jieba/spaCy)
- Sentence-level embedding generation
- Semantic similarity calculation between adjacent sentences
- Configurable merging threshold
- Document structure preservation

**Interface**:
```python
class ChineseChunker:
    def segment_sentences(self, text: str) -> List[str]
    async def generate_embeddings(self, sentences: List[str]) -> List[np.ndarray]
    def calculate_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float
    def merge_similar_sentences(self, sentences: List[str], threshold: float) -> List[str]
```

### 3. Question Generator (`services/question_generator.py`)

**Purpose**: LLM-based question generation with contextual prompting

**Key Features**:
- Context-aware prompt engineering
- JSON-structured output (question + answer pairs)
- Configurable question types (factoid, explanatory)
- Batch processing for efficiency
- Rate limiting and error handling

**Interface**:
```python
class QuestionGenerator:
    async def generate_questions(self, chunk: str, context: str) -> List[QAPair]
    def build_prompt(self, chunk: str, context: str) -> str
    async def batch_generate(self, chunks: List[ChunkWithContext]) -> List[QAPair]
```

**Prompt Template**:
```
Given the following text span and its surrounding context, generate 2-3 factoid or explanatory questions that a user might ask about the content. Reply as JSON with "question" and "answer" fields, where the answer is exactly as found in the text.

Text Span: {chunk}
Context: {context}

Output format:
[
  {"question": "...", "answer": "..."},
  {"question": "...", "answer": "..."}
]
```

### 4. Verification Engine (`services/verification_engine.py`)

**Purpose**: Self-verification filter using Rouge-L scoring

**Key Features**:
- Rouge-L score calculation
- Configurable threshold (≥0.9)
- Batch verification processing
- Quality metrics tracking
- Automatic filtering of noisy pairs

**Interface**:
```python
class VerificationEngine:
    async def verify_qa_pair(self, question: str, gold_answer: str, full_doc: str) -> VerificationResult
    def calculate_rouge_l(self, generated: str, reference: str) -> float
    async def batch_verify(self, qa_pairs: List[QAPair]) -> List[VerifiedQAPair]
    def filter_by_threshold(self, pairs: List[VerifiedQAPair], threshold: float) -> List[QAPair]
```

### 5. Dataset Manager (`services/dataset_manager.py`)

**Purpose**: Final dataset assembly and management

**Key Features**:
- Multiple export formats (JSON, CSV, HuggingFace datasets)
- Dataset versioning and metadata
- Quality statistics and reporting
- Train/validation/test splits

**Interface**:
```python
class DatasetManager:
    def create_dataset(self, qa_pairs: List[QAPair], metadata: Dict) -> Dataset
    def split_dataset(self, dataset: Dataset, splits: Dict[str, float]) -> Dict[str, Dataset]
    def export_dataset(self, dataset: Dataset, format: str, path: Path) -> None
    def generate_statistics(self, dataset: Dataset) -> DatasetStats
```

## Configuration Design

### Main Configuration (`config/evaluation.toml`)

```toml
[data_collection]
notion_databases = ["db1", "db2"]  # Database IDs to collect
batch_size = 50
rate_limit_rps = 2
export_format = "json"
incremental_updates = true

[chunking]
sentence_segmenter = "jieba"  # or "spacy"
similarity_threshold = 0.85   # For merging adjacent sentences
max_chunk_size = 500         # Max tokens per chunk
min_chunk_size = 50          # Min tokens per chunk
embedding_model = "text-embedding-3-small"
context_window = 2           # Sentences before/after for context

[question_generation]
model = "gpt-4o-mini"
questions_per_chunk = 3
question_types = ["factoid", "explanatory"]
temperature = 0.7
max_tokens = 300
batch_size = 20

[verification]
rouge_l_threshold = 0.9
verification_model = "gpt-4o-mini"
batch_size = 20
filter_noisy_pairs = true
max_retries = 3

[dataset]
train_split = 0.7
val_split = 0.15
test_split = 0.15
export_formats = ["json", "csv", "huggingface"]
version_control = true
```

### Chinese Text Configuration (`config/chunking_config.toml`)

```toml
[chinese_processing]
# Sentence segmentation
use_jieba = true
custom_dict_path = "data/chinese_dict.txt"
sentence_endings = ["。", "！", "？", "；"]

# Semantic similarity
similarity_model = "text-embedding-3-small"
merge_threshold = 0.85
max_merge_distance = 3  # Maximum sentences to merge

# Text preprocessing
remove_punctuation = false
normalize_whitespace = true
handle_english_mixed = true
```

## Data Models

### Evaluation Models (`models/evaluation_models.py`)

```python
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

class NotionDocument(BaseModel):
    id: str
    title: str
    content: str
    database_id: str
    created_time: datetime
    last_edited_time: datetime
    metadata: Dict

class TextChunk(BaseModel):
    id: str
    document_id: str
    content: str
    start_sentence: int
    end_sentence: int
    embedding: Optional[List[float]]
    context_before: str
    context_after: str

class QAPair(BaseModel):
    id: str
    chunk_id: str
    question: str
    answer: str
    question_type: str
    generated_at: datetime

class VerificationResult(BaseModel):
    qa_pair_id: str
    verified: bool
    rouge_l_score: float
    generated_answer: str
    verification_timestamp: datetime

class EvaluationDataset(BaseModel):
    version: str
    created_at: datetime
    total_pairs: int
    filtered_pairs: int
    quality_score: float
    qa_pairs: List[QAPair]
    metadata: Dict
```

## Pipeline Workflow

### Phase 1: Data Collection
```bash
cd evaluation
python scripts/collect_data.py --config config/evaluation.toml
```

**Process**:
1. Connect to Notion databases
2. Pull all documents with metadata
3. Store offline in `data/raw/`
4. Generate collection report

### Phase 2: Chunking and Embedding
```bash
python scripts/process_chunks.py --input data/raw/ --output data/processed/
```

**Process**:
1. Load offline documents
2. Segment into sentences (Chinese-aware)
3. Generate embeddings for each sentence
4. Calculate semantic similarity
5. Merge adjacent similar sentences
6. Store chunks with context

### Phase 3: Question Generation
```bash
python scripts/generate_questions.py --chunks data/processed/ --output data/processed/
```

**Process**:
1. Load processed chunks
2. Generate contextual prompts
3. Call LLM for question generation
4. Parse JSON responses
5. Store QA pairs with metadata

### Phase 4: Self-Verification
```bash
python scripts/verify_qa_pairs.py --qa-pairs data/processed/ --output data/processed/
```

**Process**:
1. Load generated QA pairs
2. Ask LLM to answer questions given full document
3. Calculate Rouge-L scores
4. Filter pairs below threshold
5. Generate quality metrics

### Phase 5: Dataset Assembly
```bash
python scripts/build_dataset.py --verified data/processed/ --output data/datasets/
```

**Process**:
1. Load verified QA pairs
2. Create train/val/test splits
3. Export in multiple formats
4. Generate dataset statistics
5. Create version metadata

## Key Design Decisions

### 1. Modular Architecture
- Each component is independent and testable
- Clear separation of concerns
- Reusable services across different evaluation tasks

### 2. Configuration-Driven
- All parameters configurable via TOML files
- Easy experimentation with different settings
- Environment-specific configurations

### 3. Chinese Text Specialization
- Dedicated Chinese sentence segmentation
- Semantic similarity for Chinese text
- Mixed Chinese-English content handling

### 4. Quality Control
- Built-in verification and filtering mechanisms
- Rouge-L scoring for answer quality
- Configurable quality thresholds

### 5. Scalability
- Batch processing throughout pipeline
- Rate limiting for API calls
- Efficient data storage formats

### 6. Data Persistence
- Clear separation between raw, processed, and final data
- Incremental processing capabilities
- Version control for datasets

### 7. Consistent Patterns
- Follows existing service layer design
- Uses established configuration patterns
- Maintains code quality standards

## Testing Strategy

### Unit Tests
- Test each service independently
- Mock external dependencies
- Validate Chinese text processing

### Integration Tests
- Test end-to-end pipeline
- Validate data flow between components
- Test with sample Chinese content

### Quality Tests
- Validate question generation quality
- Test Rouge-L scoring accuracy
- Verify dataset integrity

## Usage Examples

### Basic Pipeline Run
```bash
# Full pipeline
make eval-pipeline

# Individual steps
make eval-collect
make eval-chunk
make eval-generate
make eval-verify
make eval-build
```

### Custom Configuration
```bash
# Use custom config
python scripts/collect_data.py --config custom_eval.toml

# Override specific settings
python scripts/generate_questions.py --questions-per-chunk 5 --temperature 0.8
```

### Dataset Export
```bash
# Export to HuggingFace format
python scripts/build_dataset.py --format huggingface --output datasets/notion_eval_v1/

# Export multiple formats
python scripts/build_dataset.py --formats json,csv,huggingface
```

This architecture provides a robust foundation for building a comprehensive evaluation system that can handle the complexities of Chinese text processing while maintaining high quality standards and following established patterns from the existing codebase. 