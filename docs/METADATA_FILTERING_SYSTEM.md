# Metadata Filtering System Documentation

## Overview

The Notion Companion implements a **configuration-based metadata filtering system** that allows users to search and filter documents based on custom metadata fields extracted from Notion databases. The system supports multiple databases with different schemas and provides dynamic field discovery and intelligent filtering capabilities.

## Architecture

### Core Components

1. **Configuration System** (`databases.toml`) - Defines metadata field mappings
2. **Metadata Extraction** (`DatabaseSchemaManager`) - Extracts configured fields from Notion
3. **Search Integration** (`enhanced_metadata_search`) - Filters documents based on metadata
4. **Dynamic APIs** (`/api/metadata`) - Provides field discovery and value aggregation
5. **Bilingual Support** - Full Chinese/English content and filtering support

### Configuration-Based Design

All metadata field definitions are stored in `backend/config/databases.toml`:

```toml
[[databases]]
name = "他山之石"
database_id = "1519782c4f4a80dc9deff9768446a113"
description = "其他人的好文章"

[databases.metadata]
  [databases.metadata.author]
  notion_field = "Author"
  type = "rich_text" 
  description = "文章作者"
  filterable = true

  [databases.metadata.tags]
  notion_field = "Multi-select"
  type = "multi_select"
  description = "文章标签"
  filterable = true

  [databases.metadata.status]
  notion_field = "Status"
  type = "status"
  description = "文章阅读状态"
  filterable = true
```

## Supported Field Types

The system supports these Notion field types with intelligent filtering:

| Field Type | Description | Filtering Strategy | Example |
|------------|-------------|-------------------|---------|
| `text` | Simple text fields | Exact match, contains | Title fields |
| `rich_text` | Formatted text | Exact match, contains | Author, descriptions |
| `number` | Numeric values | Range filtering (`min:X, max:Y`) | Priority scores |
| `select` | Single choice | Exact match | Categories |
| `status` | Status fields | Exact match | Review status |
| `multi_select` | Multiple choices | Tag filtering | Tags, categories |
| `date` | Date/time fields | Date range filtering | Created, published dates |
| `checkbox` | Boolean values | True/false, yes/no, 1/0 | Completed flags |

## Database Schema

### Document Metadata Storage

```sql
CREATE TABLE document_metadata (
    document_id UUID PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
    notion_database_id TEXT NOT NULL REFERENCES notion_databases(database_id),
    
    -- Configuration-based metadata storage
    extracted_fields JSONB DEFAULT '{}',    -- Fields extracted via databases.toml
    
    -- Search optimization
    metadata_search tsvector,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Sample Data Structure

```json
{
  "document_id": "123e4567-e89b-12d3-a456-426614174000",
  "notion_database_id": "1519782c4f4a80dc9deff9768446a113",
  "extracted_fields": {
    "author": "张三",
    "tags": ["技术", "AI", "机器学习"],
    "status": "已发布",
    "published_date": "2024-01-15",
    "priority": 5
  }
}
```

## API Endpoints

### Search with Metadata Filters

```http
POST /api/search
Content-Type: application/json

{
  "query": "AI技术发展",
  "metadata_filters": [
    {
      "field_name": "tags",
      "operator": "in",
      "values": ["AI", "机器学习"]
    },
    {
      "field_name": "status", 
      "operator": "equals",
      "values": ["已发布"]
    }
  ],
  "tag_filters": ["博客", "技术"],
  "author_filters": ["张三"],
  "date_range_filter": {
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
  }
}
```

### Metadata Discovery

```http
GET /api/metadata/databases
# Returns all configured databases with field definitions

GET /api/metadata/databases/{database_id}/fields
# Returns field definitions for specific database

GET /api/metadata/databases/{database_id}/field-values/{field_name}
# Returns unique values for a specific field with search and pagination

GET /api/metadata/filter-options
# Returns all available filter options for UI dropdowns
```

## Implementation Details

### Configuration-Based Field Routing

The system reads `databases.toml` and routes filters to appropriate handlers:

```python
def _get_field_type_mapping() -> Dict[str, str]:
    """Create mapping of field names to their configured types."""
    field_type_mapping = {}
    configurations = _load_database_configurations()
    
    for config in configurations:
        metadata_config = config.get('metadata', {})
        for field_name, field_config in metadata_config.items():
            field_type = field_config.get('type', 'text')
            field_type_mapping[field_name] = field_type
    
    return field_type_mapping

# Route filters based on configured field types
field_type = field_type_mapping.get(field_name)
if field_type in ['text', 'rich_text']:
    text_filters[field_name] = values
elif field_type == 'multi_select':
    # Routes to tag_filter for array-based filtering
    tag_filters.extend(values)
elif field_type in ['select', 'status']:
    select_filters[field_name] = values
```

### Enhanced Search Function

The PostgreSQL function `enhanced_metadata_search()` handles complex filtering:

```sql
SELECT * FROM enhanced_metadata_search(
    query_embedding := $1,
    database_filter := $2,
    metadata_filters := $3,
    author_filter := $4,
    tag_filter := $5,
    status_filter := $6,
    date_range_filter := $7,
    text_filter := $8,
    number_filter := $9,
    select_filter := $10,
    checkbox_filter := $11,
    match_threshold := $12,
    match_count := $13
);
```

### Metadata Extraction Process

1. **Configuration Loading**: Read field mappings from `databases.toml`
2. **Notion Data Extraction**: Extract raw field values from Notion API
3. **Type-Aware Processing**: Process values according to configured field types
4. **Storage**: Store in `extracted_fields` JSONB column
5. **Search Indexing**: Update `metadata_search` tsvector for full-text search

## Chinese Language Support

The system provides full bilingual support:

- **Chinese Field Names**: `"作者"`, `"标签"`, `"状态"` etc.
- **Chinese Values**: `"博客"`, `"技术文章"`, `"已发布"` etc.
- **Mixed Content**: Documents with both Chinese and English content
- **Query Language**: Users can search in Chinese or English

## Frontend Integration

### Dynamic Filter Components

```typescript
// Get available filter options
const filterOptions = await fetch('/api/metadata/filter-options');

// Apply filters in search
const searchResults = await fetch('/api/search', {
  method: 'POST',
  body: JSON.stringify({
    query: searchQuery,
    tag_filters: selectedTags,
    author_filters: selectedAuthors,
    metadata_filters: customFilters
  })
});
```

### Filter UI Components

- `chat-filter-bar.tsx` - Main filtering interface
- `dynamic-filter-section.tsx` - Dynamic field-based filters
- Real-time filter option loading with search and pagination

## Performance Optimizations

1. **JSONB Indexing**: `extracted_fields` uses GIN indexes for fast queries
2. **tsvector Search**: Full-text search on metadata fields
3. **Caching**: Filter options cached and refreshed on demand
4. **Batch Processing**: Efficient bulk metadata extraction
5. **Pagination**: Large result sets paginated for UI performance

## Testing

The system includes comprehensive testing:

- **Unit Tests**: Field type routing, configuration loading
- **Integration Tests**: End-to-end metadata filtering
- **API Tests**: All metadata endpoints
- **Chinese Support Tests**: Bilingual content and filtering

```bash
# Run all tests
cd backend && uv run python -m pytest tests/

# Specific metadata tests
cd backend && uv run python -m pytest tests/api/test_metadata_filtering.py
```

## Migration and Deployment

### Adding New Database

1. **Update Configuration**: Add database entry to `databases.toml`
2. **Define Metadata Fields**: Map Notion fields to system fields
3. **Sync Database**: Run `sync_databases.py` to extract metadata
4. **Verify**: Test filtering with new fields

### Field Type Changes

1. **Update Configuration**: Modify field type in `databases.toml`
2. **Re-extract Metadata**: Run sync to update existing documents
3. **Test Filtering**: Verify new filtering behavior

## Best Practices

1. **Configuration Management**: Keep `databases.toml` in version control
2. **Field Naming**: Use consistent field names across databases
3. **Type Selection**: Choose appropriate field types for optimal filtering
4. **Performance**: Limit filterable fields to frequently queried ones
5. **Testing**: Test metadata changes with real Notion data

## Troubleshooting

### Common Issues

1. **Field Not Found**: Check field name spelling in `databases.toml`
2. **No Filter Results**: Verify field type configuration matches Notion
3. **Chinese Characters**: Ensure UTF-8 encoding in configuration
4. **Performance**: Check JSONB indexes on large datasets

### Debugging Tools

```bash
# Check configuration loading
cd backend && uv run python -c "
from routers.search import _load_database_configurations
print(_load_database_configurations())
"

# Test field type mapping
cd backend && uv run python -c "
from routers.search import _get_field_type_mapping
print(_get_field_type_mapping())
"
```

## Future Enhancements

1. **Advanced Operators**: `contains`, `starts_with`, `greater_than`
2. **Nested Filtering**: Complex boolean filter expressions
3. **Auto-Configuration**: Generate `databases.toml` from Notion schema
4. **Field Validation**: Validate configuration against Notion database
5. **Performance Analytics**: Track filter performance and optimization

---

This documentation reflects the current production implementation as of 2024. The system successfully handles bilingual content, provides dynamic field discovery, and offers intelligent filtering across multiple Notion databases with different schemas. 