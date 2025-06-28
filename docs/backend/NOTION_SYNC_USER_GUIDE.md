# Notion Sync User Guide

This guide helps you set up and use the Notion database synchronization feature. For technical implementation details, see [DATA_INGESTION_PIPELINE.md](DATA_INGESTION_PIPELINE.md).

## Quick Start

### 1. Setup Configuration
```bash
cd backend/config
cp databases.example.toml databases.toml
# Edit databases.toml with your actual database IDs
```

### 2. Set Access Token
```bash
# Option 1: Environment variable
export NOTION_ACCESS_TOKEN="your_notion_integration_token"

# Option 2: Add to .env file in backend directory
echo "NOTION_ACCESS_TOKEN=your_notion_integration_token" >> .env
```

### 3. Run Sync
```bash
cd backend
./sync_notion_databases.sh
```

## Available Scripts

- **`sync_databases.py`** - Main Python script for database synchronization
- **`check_active_databases.py`** - Check what databases are currently in Supabase
- **`sync_notion_databases.sh`** - Convenient wrapper shell script
- **`config/databases.toml`** - Your database configuration file
- **`config/databases.example.toml`** - Example configuration template

## Basic Configuration

### Database Setup

Each database in your `config/databases.toml` needs these essential settings:

```toml
[[databases]]
name = "My Database"                    # Human-readable name
database_id = "uuid-of-notion-database" # Notion database ID
description = "What this database contains"

[databases.sync_settings]
batch_size = 10                       # Pages per batch (start with 10)
rate_limit_delay = 1.0                # Seconds between batches (start with 1.0)
max_retries = 3                       # Retry failed pages
```

> 💡 **For advanced configuration options**, see the [Configuration section](DATA_INGESTION_PIPELINE.md#️-configuration) in the technical documentation.

### Global Settings

```toml
[global_settings]
concurrent_databases = 3                 # Max databases to sync simultaneously
log_level = "INFO"                       # DEBUG, INFO, WARNING, ERROR
```

## Usage Examples

### Check Current Databases
```bash
cd backend
python scripts/check_active_databases.py
```

### Basic Sync
```bash
# Using environment variable
export NOTION_ACCESS_TOKEN="your_token"
./sync_notion_databases.sh

# Using .env file
echo "NOTION_ACCESS_TOKEN=your_token" >> .env
./sync_notion_databases.sh
```

### Advanced Usage
```bash
# Preview changes without applying
./sync_notion_databases.sh --dry-run

# Use custom config file
./sync_notion_databases.sh --config /path/to/custom.toml

# Sync specific database
python scripts/sync_databases.py --database-id your-database-id
```

## Getting Notion Database IDs

1. **Open your Notion database** in a web browser
2. **Copy the URL**, which looks like:
   ```
   https://www.notion.so/workspace/12345678123412341234123456789abc?v=...
   ```
3. **Extract the database ID** (the long string after the last slash and before the `?`)
4. **Format with dashes**: `12345678-1234-1234-1234-123456789abc`

## Security Best Practices

### ✅ Recommended: Environment Variables
```bash
export NOTION_ACCESS_TOKEN="secret_..."
```

### ✅ Alternative: .env File
```bash
echo "NOTION_ACCESS_TOKEN=secret_..." >> backend/.env
# Make sure .env is in .gitignore!
```

### ❌ Never: Hardcode in Files
Don't put tokens directly in scripts or config files.

### Notion Integration Permissions

Create a Notion integration with minimal permissions:
- ✅ Read content
- ✅ Read user information (if needed)
- ❌ No write permissions required

## Common Issues & Solutions

- **"Permission denied"**: Share the database with your Notion integration
- **Rate limit errors**: Increase `rate_limit_delay` in your config (e.g., from 1.0 to 2.0)
- **Database ID not found**: Check ID format has dashes and integration has access
- **Out of memory**: Reduce `batch_size` and `concurrent_databases` values

> 🔧 **For advanced troubleshooting**, see [Troubleshooting](DATA_INGESTION_PIPELINE.md#-troubleshooting) in the technical documentation.

## Performance Tips

**Small databases (< 100 pages)**: Use `batch_size = 20` and `rate_limit_delay = 0.5`  
**Large databases (> 500 pages)**: Use `batch_size = 10` and `rate_limit_delay = 2.0`  
**Rate limit issues**: Increase `rate_limit_delay` to 3.0 and reduce `batch_size` to 5

## Monitoring Your Sync

The script shows real-time progress and saves detailed logs to `database_sync.log`.

> 📊 **For detailed monitoring**, see [Performance & Monitoring](DATA_INGESTION_PIPELINE.md#-performance--monitoring) in the technical documentation.

## Setting Up Automation

**Daily Cron Job**: Add to crontab: `0 2 * * * /path/to/sync_notion_databases.sh >> /var/log/sync.log 2>&1`  
**Test First**: Always run `./sync_notion_databases.sh --dry-run` before automating

> 🚀 **For CI/CD integration**, see [Automation Options](DATA_INGESTION_PIPELINE.md#-automation-options) in the technical documentation.

## Integration with Notion Companion

After running the sync, your content is immediately available in the main application:

1. **Search Results** - Documents appear in vector search
2. **AI Chat** - Assistant can reference your synced content
3. **Real-time Updates** - Frontend automatically shows new content
4. **Database Filtering** - Filter results by specific Notion databases

## Getting Help

**Configuration**: [Configuration Guide](CONFIG_GUIDE.md) | **Technical Details**: [Data Ingestion Pipeline](DATA_INGESTION_PIPELINE.md) | **Backend Setup**: [Backend Setup Guide](BACKEND_SETUP.md)

**Debug Mode**: Add `log_level = "DEBUG"` to your config for verbose output

## Next Steps

1. Start with one database and small batch sizes
2. Monitor logs and adjust settings as needed  
3. Set up automation once everything works
4. Gradually scale up batch sizes and add more databases

> 💡 **Pro Tip**: Always use `--dry-run` to test configuration changes safely.