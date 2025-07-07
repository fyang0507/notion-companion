# Evaluation System

Simple system for collecting documents from Notion databases for evaluation purposes.

## Overview

This is a simplified data collection system that:
1. Connects to Notion databases
2. Downloads all documents/pages
3. Saves them as JSON files locally
4. Automatically loads environment variables from root folder's `.env` file

## Quick Start

1. Set your Notion token in the root folder's `.env` file:
```bash
# In your project root .env file
NOTION_ACCESS_TOKEN=your_token_here
```

2. Configure databases in `config/evaluation.toml`:
```toml
[collection]
database_ids = ["your_database_id_here"]
output_dir = "data"
min_content_length = 10
```

3. Run collection:
```bash
cd evaluation
python scripts/collect_data.py
```

## Usage

### Basic Collection
```bash
# Use default config
python scripts/collect_data.py

# Use custom config
python scripts/collect_data.py --config my_config.toml

# Collect single database
python scripts/collect_data.py --database-id abc123...
```

### Configuration

Simple configuration in `config/evaluation.toml`:
```toml
[collection]
database_ids = [
    "1519782c4f4a80dc9deff9768446a113",  # Database 1
    "another_database_id_here"           # Database 2
]
output_dir = "data"                      # Output directory
min_content_length = 10                  # Skip pages shorter than this
```

### Environment Variables

The system automatically loads environment variables from the root folder's `.env` file:
- Loads from project root `.env` file (not local evaluation folder)
- Requires `NOTION_ACCESS_TOKEN` to be set
- No need to manually export variables

### Output Format

Creates JSON files in the output directory:
```
data/
├── 15197823_20240101_123456.json
└── another_20240101_123456.json
```

Each file contains:
```json
{
  "database_id": "15197823...",
  "collected_at": "2024-01-01T12:34:56",
  "total_documents": 123,
  "documents": [
    {
      "id": "page_id",
      "title": "Page Title",
      "content": "Page content...",
      "database_id": "15197823...",
      "created_time": "2024-01-01T10:00:00",
      "last_edited_time": "2024-01-01T11:00:00",
      "url": "https://notion.so/..."
    }
  ]
}
```

## Architecture

- **`models/evaluation_models.py`** - Simple data models
- **`services/data_collector.py`** - Data collection logic with auto env loading
- **`scripts/collect_data.py`** - Main collection script
- **`config/evaluation.toml`** - Configuration file

## Error Handling

The system handles common errors gracefully:
- Missing environment variables with clear error messages
- Missing pages are skipped
- Network errors are logged
- Invalid content is filtered out
- Progress is reported throughout

## Requirements

- Python 3.8+
- Notion API access token (in root folder's `.env` file)
- Access to target Notion databases

That's it! The system is designed to be simple and focused on just collecting data for evaluation purposes. 