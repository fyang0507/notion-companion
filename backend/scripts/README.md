# Notion Database Sync Scripts

This directory contains scripts for syncing multiple Notion databases simultaneously to your local database with RAG processing.

## Quick Start

1. **Setup Configuration**:
   ```bash
   cd backend/config
   cp databases.example.toml databases.toml
   # Edit databases.toml with your actual database IDs
   ```

2. **Set Access Token**:
   ```bash
   # Option 1: Environment variable
   export NOTION_ACCESS_TOKEN="your_notion_integration_token"
   
   # Option 2: Add to .env file in backend directory
   echo "NOTION_ACCESS_TOKEN=your_notion_integration_token" >> .env
   ```

3. **Run Sync**:
   ```bash
   cd backend
   ./sync_notion_databases.sh
   ```

## Files Overview

- `sync_databases.py` - Main Python script that handles the database synchronization
- `../sync_notion_databases.sh` - Convenient wrapper shell script
- `../config/databases.toml` - Configuration file defining which databases to sync (TOML format)
- `../config/databases.example.toml` - Example configuration file

## Configuration

### Database Configuration

Each database in your `config/databases.toml` file supports these options:

```toml
[[databases]]
name = "My Database"                    # Human-readable name
database_id = "uuid-of-notion-database" # Notion database ID
description = "What this database contains"

[databases.sync_settings]
batch_size = 10                       # Pages per batch
rate_limit_delay = 1.0                # Seconds between batches
max_retries = 3                       # Retry failed pages

[databases.filters]
archived = false                      # Skip archived pages
Status = "Published"                  # Filter by property (optional)

[databases.processing]
chunk_size = 1000                     # Tokens per chunk
chunk_overlap = 100                   # Overlap between chunks
enable_chunking = true                # Whether to chunk large documents
```

**Note**: This application uses a single-workspace design. All databases are synced to one "Default Workspace" in the system.

### Global Settings

```toml
[global_settings]
concurrent_databases = 3                 # Max databases to sync simultaneously
log_level = "INFO"                       # DEBUG, INFO, WARNING, ERROR
log_file = "database_sync.log"           # Log file location
```

## Usage Examples

### Basic Usage

```bash
# Basic sync (reads NOTION_ACCESS_TOKEN from environment or .env file)
export NOTION_ACCESS_TOKEN="your_token"
./sync_notion_databases.sh

# Or add token to .env file and run
echo "NOTION_ACCESS_TOKEN=your_token" >> .env
./sync_notion_databases.sh
```

### Advanced Usage

```bash
# Dry run to test configuration
./sync_notion_databases.sh --dry-run

# Use custom config file
./sync_notion_databases.sh --config /path/to/custom.toml

# Python script directly
python scripts/sync_databases.py --config config/databases.toml --dry-run
```

## Getting Notion Database IDs

1. Open your Notion database in a web browser
2. Copy the URL, which looks like:
   `https://www.notion.so/workspace/12345678123412341234123456789abc?v=...`
3. Extract the database ID (the long string after the last slash and before the `?`)
4. Format it with dashes: `12345678-1234-1234-1234-123456789abc`

## Security Best Practices

### Token Storage

**Recommended**: Use environment variables
```bash
export NOTION_ACCESS_TOKEN="secret_..."
```

**Alternative**: Use .env file in backend directory
```bash
echo "NOTION_ACCESS_TOKEN=secret_..." >> backend/.env
# Make sure .env is in .gitignore!
```

**Not Recommended**: Hardcoding tokens in scripts or config files

### Access Token Permissions

Create a Notion integration with minimal required permissions:
- Read content
- Read user information (if needed)
- No write permissions required for sync

## Monitoring and Logs

The script provides detailed logging and progress tracking:

- **Console Output**: Real-time progress and summary
- **Log File**: Detailed logs saved to `database_sync.log`
- **Error Handling**: Failed pages are logged with details for debugging

### Log Levels

- `DEBUG`: Verbose output for troubleshooting
- `INFO`: Normal operational information
- `WARNING`: Non-critical issues
- `ERROR`: Serious problems that need attention

## Performance Tuning

### Rate Limiting

Adjust `rate_limit_delay` in your config to respect Notion's API limits:
- Small databases: `0.5` seconds
- Large databases: `1.0-2.0` seconds
- If you hit rate limits: increase delay

### Concurrency

- `concurrent_databases`: Number of databases to process simultaneously
- `batch_size`: Pages processed per batch within each database
- `supabase_batch_size`: Documents uploaded to database at once

### Chunking Strategy

- `enable_chunking: true`: For large documents (articles, documentation)
- `enable_chunking: false`: For short content (notes, tasks)
- `chunk_size`: Adjust based on your content length and search needs

## Troubleshooting

### Common Issues

1. **"Permission denied" errors**: Check your Notion integration permissions
2. **Rate limit errors**: Increase `rate_limit_delay` in config
3. **Database ID not found**: Verify the database ID format and permissions
4. **Out of memory**: Reduce `batch_size` or `concurrent_databases`

### Debug Mode

Enable debug logging for detailed troubleshooting:
```yaml
global_settings:
  log_level: "DEBUG"
```

### Manual Testing

Test individual components:
```python
# Test Notion connection
from services.notion_service import NotionService
service = NotionService("your_token")
pages = await service.get_database_pages("database_id")

# Test database connection
from database import init_db, get_db
await init_db()
db = get_db()
```

## Integration with Main Application

The sync script creates documents in the default workspace that are immediately available to the main Notion Companion application. After running the sync:

1. Documents appear in search results
2. Chat can reference the synced content
3. Vector embeddings are ready for RAG queries
4. All content is organized under a single workspace for simplicity

## Automation

### Cron Job Setup

```bash
# Add to crontab for daily sync at 2 AM
0 2 * * * /path/to/notion-companion/backend/sync_notion_databases.sh >> /var/log/notion-sync.log 2>&1
```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Sync Notion Databases
  run: |
    export NOTION_ACCESS_TOKEN="${{ secrets.NOTION_TOKEN }}"
    ./backend/sync_notion_databases.sh
```