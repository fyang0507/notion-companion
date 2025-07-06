# Notion API Schema Analysis

## Overview

This document analyzes the Notion API database schema structure to understand how metadata is extracted and processed by the Notion Companion system.

## Notion API Database Schema Structure

### 1. Database Schema Endpoint

**API Call**: `notion_client.databases.retrieve(database_id="xxx")`

**Response Structure**:
```json
{
  "object": "database",
  "id": "database-id-here",
  "title": [{"type": "text", "text": {"content": "My Database"}}],
  "description": [...],
  "properties": {
    "Name": {
      "id": "title",
      "type": "title",
      "title": {}
    },
    "Status": {
      "id": "status-id",
      "type": "status",
      "status": {
        "options": [
          {"id": "1", "name": "Not started", "color": "default"},
          {"id": "2", "name": "In progress", "color": "blue"},
          {"id": "3", "name": "Completed", "color": "green"}
        ]
      }
    },
    "Tags": {
      "id": "multi-select-id", 
      "type": "multi_select",
      "multi_select": {
        "options": [
          {"id": "a", "name": "Important", "color": "red"},
          {"id": "b", "name": "Research", "color": "blue"}
        ]
      }
    },
    "Author": {
      "id": "people-id",
      "type": "people", 
      "people": {}
    },
    "Created": {
      "id": "created-id",
      "type": "created_time",
      "created_time": {}
    },
    "Due Date": {
      "id": "date-id",
      "type": "date",
      "date": {}
    },
    "Priority": {
      "id": "select-id",
      "type": "select",
      "select": {
        "options": [
          {"id": "1", "name": "High", "color": "red"},
          {"id": "2", "name": "Medium", "color": "yellow"},
          {"id": "3", "name": "Low", "color": "green"}
        ]
      }
    }
  }
}
```

### 2. Page Data Structure

**API Call**: `notion_client.databases.query(database_id="xxx")`

**Sample Page Properties**:
```json
{
  "properties": {
    "Name": {
      "type": "title",
      "title": [{"type": "text", "text": {"content": "My Document"}}]
    },
    "Status": {
      "type": "status", 
      "status": {"name": "In progress", "color": "blue"}
    },
    "Tags": {
      "type": "multi_select",
      "multi_select": [
        {"name": "Important", "color": "red"},
        {"name": "Research", "color": "blue"}
      ]
    },
    "Author": {
      "type": "people",
      "people": [{"name": "John Doe", "avatar_url": "..."}]
    },
    "Created": {
      "type": "created_time",
      "created_time": "2024-01-15T10:30:00.000Z"
    },
    "Due Date": {
      "type": "date", 
      "date": {"start": "2024-02-01", "end": null}
    },
    "Priority": {
      "type": "select",
      "select": {"name": "High", "color": "red"}
    }
  }
}
```

## Notion Field Types Reference

### Supported Field Types

| Notion Type | Description | Value Structure | Example |
|-------------|-------------|----------------|---------|
| `title` | Page title | `[{"type": "text", "text": {"content": "..."}}]` | Document titles |
| `rich_text` | Formatted text | `[{"type": "text", "text": {"content": "..."}}]` | Descriptions, notes |
| `number` | Numeric values | `42` | Priority scores, ratings |
| `select` | Single choice | `{"name": "High", "color": "red"}` | Categories, priorities |
| `status` | Status field | `{"name": "In Progress", "color": "blue"}` | Workflow states |
| `multi_select` | Multiple choices | `[{"name": "Tech", "color": "blue"}]` | Tags, categories |
| `date` | Date/time | `{"start": "2024-01-01", "end": null}` | Deadlines, created dates |
| `checkbox` | Boolean | `true` or `false` | Completion flags |
| `people` | User references | `[{"name": "John", "avatar_url": "..."}]` | Authors, assignees |
| `created_time` | Auto-generated | `"2024-01-15T10:30:00.000Z"` | Creation timestamp |
| `last_edited_time` | Auto-generated | `"2024-01-15T10:30:00.000Z"` | Last edit timestamp |

### Chinese Language Support

Notion API natively supports Chinese field names and values:

```json
{
  "properties": {
    "作者": {
      "type": "people",
      "people": [{"name": "张三"}]
    },
    "标签": {
      "type": "multi_select",
      "multi_select": [
        {"name": "技术", "color": "blue"},
        {"name": "博客", "color": "red"}
      ]
    },
    "状态": {
      "type": "status",
      "status": {"name": "已发布", "color": "green"}
    }
  }
}
```

## Value Extraction Patterns

### Simple Values
```json
// Text/Rich Text
"rich_text": [{"type": "text", "text": {"content": "Extracted Value"}}]
→ "Extracted Value"

// Number
"number": 42
→ 42

// Checkbox
"checkbox": true
→ true
```

### Complex Values
```json
// Select/Status
"select": {"name": "High Priority", "color": "red"}
→ "High Priority"

// Multi-select (Tags)
"multi_select": [
  {"name": "Tech", "color": "blue"},
  {"name": "AI", "color": "green"}
]
→ ["Tech", "AI"]

// Date
"date": {"start": "2024-01-01", "end": "2024-01-31"}
→ "2024-01-01" (start date extracted)

// People
"people": [{"name": "John Doe", "avatar_url": "..."}]
→ "John Doe"
```

## Configuration Mapping

The Notion Companion system maps Notion field types to internal field types:

```toml
# databases.toml configuration
[databases.metadata.author]
notion_field = "Created By"    # Notion field name (can be Chinese)
type = "rich_text"            # Internal field type
description = "文档作者"       # Description (can be Chinese)
filterable = true             # Enable filtering
```

### Field Type Mapping

| Notion Type | Internal Type | Filtering Strategy |
|-------------|---------------|-------------------|
| `title`, `rich_text` | `text`, `rich_text` | Text matching |
| `number` | `number` | Range filtering |
| `select`, `status` | `select`, `status` | Exact matching |
| `multi_select` | `multi_select` | Array/tag filtering |
| `date`, `created_time` | `date` | Date range filtering |
| `checkbox` | `checkbox` | Boolean filtering |
| `people` | `rich_text` | Text matching (name extraction) |

## Multi-Language Considerations

### Field Name Handling
- **English**: `"Author"`, `"Tags"`, `"Status"`
- **Chinese**: `"作者"`, `"标签"`, `"状态"`
- **Mixed**: `"Author (作者)"`, `"Tags/标签"`

### Value Processing
- **Consistent Internal Storage**: All values stored in consistent format
- **Unicode Support**: Full UTF-8 support for Chinese characters
- **Search Optimization**: Both Chinese and English searchable

## Schema Evolution

### Version Compatibility
- **Notion Schema Changes**: Field types and names can change
- **Configuration Flexibility**: `databases.toml` allows adaptation
- **Backward Compatibility**: Existing configurations continue working

### Best Practices
1. **Stable Field Names**: Use consistent internal field names
2. **Type Consistency**: Map similar Notion types to same internal types
3. **Documentation**: Document field mappings for team understanding
4. **Testing**: Test with real Notion data including Chinese content

## API Rate Limits

### Notion API Constraints
- **Rate Limit**: 3 requests per second per integration
- **Batch Processing**: Use appropriate delays between requests
- **Error Handling**: Implement retry logic for rate limit errors

### Optimization Strategies
- **Caching**: Cache database schemas to reduce API calls
- **Incremental Updates**: Only fetch changed pages
- **Batch Operations**: Group multiple operations where possible

---

**For Implementation Details**: See `docs/METADATA_FILTERING_SYSTEM.md`

**For Current Status**: See `docs/METADATA_FILTERING_IMPLEMENTATION.md`