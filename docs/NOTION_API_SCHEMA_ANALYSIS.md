# Notion API Database Schema Analysis

## Overview

This document analyzes how the Notion API returns database schema information to inform the decision between **automatic metadata inference** vs **manual metadata definition**.

## How Notion API Returns Database Schema

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

## Current Automatic Inference Approach

### How It Works Now

1. **Schema Discovery** (`database_schema_manager.py`):
   ```python
   # Gets database schema
   database_info = notion_service.client.databases.retrieve(database_id)
   properties = database_info.get('properties', {})
   
   # Analyzes each field
   for field_name, field_config in properties.items():
       field_type = field_config.get('type')
       # Assigns priority scores based on type
       # Determines if field is "queryable" for filtering
   ```

2. **Field Prioritization** (Current Logic):
   ```python
   priority_field_types = {
       'date': 10,           # High priority for filtering
       'created_time': 10,
       'status': 9,         # Great for filtering  
       'select': 8,         # Good categorical data
       'multi_select': 8,
       'number': 7,
       'people': 7,         # Author information
       'title': 10,         # Always important
       'rich_text': 5,      # Lower priority
   }
   ```

3. **Automatic Mapping** (Current Implementation):
   ```python
   def _map_to_common_field(self, field_name: str, field_type: str, raw_value: Any):
       field_name_lower = field_name.lower()
       
       if 'author' in field_name_lower or 'creator' in field_name_lower:
           return ('author', processed_value)
       elif 'tag' in field_name_lower or field_type == 'multi_select':
           return ('tags', processed_value)
       elif 'status' in field_name_lower or field_type == 'status':
           return ('status', processed_value)
       # ... more mappings
   ```

### Issues with Current Approach

1. **Name-Based Mapping is Fragile**:
   - Field named "Project Status" vs "Status" vs "Current State"
   - Non-English field names (Chinese databases)
   - Ambiguous field purposes

2. **Type-Based Assumptions**:
   - Not all `multi_select` fields are "tags"
   - `people` fields might be "reviewers" not "authors"
   - `select` fields could be anything

3. **No User Control**:
   - Can't exclude irrelevant fields
   - Can't customize field importance  
   - Can't handle business-specific semantics

## Manual Metadata Definition Approach

### Proposed `databases.toml` Configuration

```toml
# Database-specific metadata configuration
[databases."database-id-1"]
name = "Research Papers"
description = "Academic research document database"

  [databases."database-id-1".metadata]
  # Define which fields to expose for filtering
  author = { notion_field = "Created By", type = "text", description = "Document author", filterable = true }
  tags = { notion_field = "Categories", type = "array", description = "Document categories", filterable = true }
  status = { notion_field = "Review Status", type = "text", description = "Review progress", filterable = true }
  publication_date = { notion_field = "Published", type = "date", description = "Publication date", filterable = true }
  priority = { notion_field = "Research Priority", type = "text", description = "Research importance", filterable = true }
  
  # Fields to ignore (not expose for filtering)
  # notion_field_name = { ignore = true }

[databases."database-id-2"] 
name = "Meeting Notes"
description = "Team meeting documentation"

  [databases."database-id-2".metadata]
  author = { notion_field = "Meeting Lead", type = "text", description = "Meeting organizer", filterable = true }
  tags = { notion_field = "Topics", type = "array", description = "Discussion topics", filterable = true }
  meeting_date = { notion_field = "Date", type = "date", description = "Meeting date", filterable = true }
  attendees = { notion_field = "Participants", type = "array", description = "Meeting attendees", filterable = false }
```

### Benefits of Manual Definition

1. **Precise Control**:
   - Exact field mapping regardless of names
   - Choose which fields to expose
   - Custom descriptions for UI

2. **Multi-Language Support**:
   - Works with Chinese, Japanese, etc. field names
   - Consistent English metadata field names

3. **Business Logic Alignment**:
   - Map fields according to actual business meaning
   - Handle different database purposes appropriately

4. **Maintainable**:
   - Clear documentation of field purposes
   - Version controlled configuration
   - Easy to adjust without code changes

### Implementation Changes Needed

#### 1. **Configuration Loading**
```python
# New: config/database_config.py
class DatabaseMetadataConfig:
    def __init__(self, config_path: str):
        self.config = load_toml(config_path)
    
    def get_database_metadata_config(self, database_id: str) -> Dict[str, Any]:
        return self.config.get('databases', {}).get(database_id, {}).get('metadata', {})
```

#### 2. **Schema Manager Changes**
```python
# Modified: services/database_schema_manager.py
async def extract_document_metadata(self, document_id: str, page_data: Dict[str, Any], database_id: str):
    # Get manual configuration instead of automatic inference
    metadata_config = self.database_config.get_database_metadata_config(database_id)
    
    if not metadata_config:
        self.logger.warning(f"No metadata configuration found for database {database_id}")
        return {}
    
    # Extract only configured fields
    for common_field, field_config in metadata_config.items():
        if field_config.get('ignore'):
            continue
            
        notion_field = field_config['notion_field']
        if notion_field in page_properties:
            # Extract and map according to configuration
            raw_value = self._extract_field_value(page_properties[notion_field], field_config['type'])
            metadata_record[common_field] = raw_value
```

#### 3. **Database Schema Storage** (Minor Changes)
The current `database_field_schemas` table could still be used but simplified:

```sql
-- Store manual configuration instead of inferred schema  
CREATE TABLE database_metadata_configs (
    database_id TEXT PRIMARY KEY,
    database_name TEXT NOT NULL,
    manual_config JSONB NOT NULL,  -- From databases.toml
    last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Comparison: Automatic vs Manual

| Aspect | Automatic Inference | Manual Definition |
|--------|-------------------|------------------|
| **Setup Effort** | ✅ Zero configuration | ❌ Requires setup per database |
| **Accuracy** | ❌ Hit-or-miss field mapping | ✅ Precise field control |
| **Multi-Language** | ❌ Struggles with non-English | ✅ Works with any language |
| **Maintainability** | ❌ Code changes for adjustments | ✅ Config file changes only |
| **Business Logic** | ❌ Generic field assumptions | ✅ Business-specific mapping |
| **User Control** | ❌ No customization | ✅ Full control over exposure |
| **Debugging** | ❌ Hard to understand failures | ✅ Clear configuration |
| **Scalability** | ❌ Breaks with diverse databases | ✅ Handles different database types |

## Recommendation

**For MVP: Manual Definition Approach**

### Reasons:
1. **Reliability**: Won't break with different database naming conventions
2. **International Support**: Essential for Chinese/multi-language databases  
3. **User Expectations**: Users can control what metadata is exposed
4. **Debugging**: Clear configuration makes troubleshooting easier
5. **Future-Proof**: Can handle diverse database types as system grows

### Implementation Plan:
1. Create `databases.toml` configuration file
2. Build configuration loader
3. Modify `database_schema_manager.py` to use manual config
4. Simplify database schema storage  
5. Document configuration format for users

### Migration Path:
- Keep automatic inference as fallback for unconfigured databases
- Provide tools to generate initial `databases.toml` from existing databases
- Allow gradual migration database by database

This approach gives you the reliability and control needed for production while maintaining the flexibility to add automatic inference later if needed.