# Manual Metadata Definition: Architecture & Implementation

## Executive Summary

Based on comprehensive analysis of Notion API schema structure, current automatic inference limitations, and multi-language requirements, **manual metadata definition via `databases.toml` configuration** is the recommended approach for MVP. This provides precise control, international support, and production reliability with minimal schema changes.

## Background: Why Manual Definition

### ❌ Automatic Inference Issues
1. **Fragile Name Matching**: Breaks with "Project Status" vs "Status" vs "Current State"
2. **Language Barriers**: Fails completely with Chinese/non-English field names
3. **Type Assumptions**: Assumes all `multi_select` = tags, all `people` = authors
4. **No User Control**: Can't exclude irrelevant fields or customize importance
5. **Business Logic Gaps**: Generic assumptions don't match specific database purposes

### 🔍 Notion API Schema Structure
- **Schema Endpoint**: `databases.retrieve(database_id)` returns complete field definitions
- **Rich Type System**: `select`, `multi_select`, `people`, `status`, `date`, `title`, etc.
- **Structured Data**: Each field type has specific configuration and data formats
- **Multi-Language Support**: Field names can be in any language (Chinese, Japanese, etc.)

**Sample API Response**:
```json
{
  "properties": {
    "Status": {"type": "status", "status": {"options": [...]}},
    "Tags": {"type": "multi_select", "multi_select": {"options": [...]}}, 
    "Author": {"type": "people", "people": {}},
    "作者": {"type": "people", "people": {}},  // Chinese field names
    "分类": {"type": "multi_select", "multi_select": {"options": [...]}}
  }
}
```

## Manual Definition Architecture

### Configuration Format (`databases.toml`)

```toml
# Research Papers Database
[databases."a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
name = "Research Papers"
description = "Academic research document database"

  [databases."a1b2c3d4-e5f6-7890-abcd-ef1234567890".metadata]
  author = { notion_field = "Created By", type = "text", description = "Document author", filterable = true }
  tags = { notion_field = "Categories", type = "array", description = "Document categories", filterable = true }
  status = { notion_field = "Review Status", type = "text", description = "Review progress", filterable = true }
  publication_date = { notion_field = "Published", type = "date", description = "Publication date", filterable = true }
  priority = { notion_field = "Research Priority", type = "text", description = "Research importance", filterable = true }

# Chinese Database Example  
[databases."中文数据库-id-here"]
name = "学术论文"
description = "学术研究文档数据库"

  [databases."中文数据库-id-here".metadata]
  author = { notion_field = "作者", type = "text", description = "文档作者", filterable = true }
  tags = { notion_field = "分类", type = "array", description = "文档分类", filterable = true }
  status = { notion_field = "状态", type = "text", description = "审核状态", filterable = true }
  created_date = { notion_field = "创建时间", type = "date", description = "创建日期", filterable = true }

# Meeting Notes Database
[databases."meeting-notes-db-id"]
name = "Meeting Notes"
description = "Team meeting documentation"

  [databases."meeting-notes-db-id".metadata]
  author = { notion_field = "Meeting Lead", type = "text", description = "Meeting organizer", filterable = true }
  tags = { notion_field = "Topics", type = "array", description = "Discussion topics", filterable = true }
  meeting_date = { notion_field = "Date", type = "date", description = "Meeting date", filterable = true }
  # Attendees stored but not filterable in UI
  attendees = { notion_field = "Participants", type = "array", description = "Meeting attendees", filterable = false }
```

### Benefits of Manual Approach

1. **🎯 Precision**: Exact field mapping regardless of naming conventions
2. **🌐 International**: Works with Chinese, Japanese, any language field names  
3. **🎛️ Control**: Choose exactly which fields to expose for filtering
4. **📝 Documentation**: Clear field purposes and descriptions for UI
5. **🔧 Maintainable**: Config file changes, no code deployment needed
6. **🏢 Business Logic**: Map fields according to actual business meaning
7. **🐛 Debuggable**: Clear configuration makes troubleshooting easy

## Schema Compatibility Analysis

### ✅ **Current Schema Works Perfectly**

#### `document_metadata` Table Structure
```sql
CREATE TABLE document_metadata (
    document_id UUID PRIMARY KEY,
    notion_database_id TEXT NOT NULL,
    
    -- Common typed fields for fast querying (manual mapping targets)
    title TEXT, author TEXT, status TEXT, tags TEXT[], 
    created_date DATE, modified_date DATE, priority TEXT,
    assignee TEXT, due_date DATE, completion_date DATE,
    
    -- Flexible storage for database-specific fields
    database_fields JSONB DEFAULT '{}',     -- Raw Notion field values
    search_metadata JSONB DEFAULT '{}',     -- Normalized metadata for search/filtering
    field_mappings JSONB DEFAULT '{}',      -- Maps database fields to common fields
    
    -- Search optimization
    metadata_search tsvector,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Manual Definition Example**:
```json
{
  "document_id": "123",
  "notion_database_id": "db-456",
  
  // Manually mapped common fields  
  "author": "John Doe",              // From manual config: "Created By" → author
  "tags": ["Research", "Important"], // From manual config: "Categories" → tags
  "status": "In Progress",           // From manual config: "Review Status" → status
  
  // Raw storage
  "database_fields": {
    "Created By": [{"name": "John Doe"}],           // Raw Notion data
    "Categories": [{"name": "Research"}, {"name": "Important"}],
    "Review Status": {"name": "In Progress"}
  },
  
  // Search optimization
  "search_metadata": {
    "author": "John Doe",
    "tags": ["Research", "Important"], 
    "status": "In Progress"
  },
  
  // Configuration tracking
  "field_mappings": {
    "Created By": "author",
    "Categories": "tags",
    "Review Status": "status"
  }
}
```

### ✅ **No Changes Needed to Core Infrastructure**

1. **Enhanced Search Function**: `enhanced_metadata_search()` works perfectly with manual definition
2. **API Models**: `MetadataFilter`, `SearchRequest`, `ChatRequest` unchanged
3. **Search/Chat Routers**: No changes needed to API endpoints
4. **Frontend Types**: No changes needed to TypeScript types

## Implementation Plan

### **Phase 1: Core Infrastructure** (1-2 days)

#### 1.1 Add Configuration Table
```sql
CREATE TABLE database_metadata_configs (
    database_id TEXT PRIMARY KEY REFERENCES notion_databases(database_id),
    database_name TEXT NOT NULL,
    config_source TEXT NOT NULL DEFAULT 'manual',
    manual_config JSONB NOT NULL DEFAULT '{}',
    config_version TEXT DEFAULT '1.0',
    config_file_hash TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 1.2 Create Configuration Loader
```python
# New: config/database_config.py
class DatabaseConfig:
    def __init__(self, config_path: str = "config/databases.toml"):
        self.config_path = config_path
        self.config = None
        self._load_config()
    
    def _load_config(self):
        """Load and validate databases.toml"""
        
    def get_database_metadata_config(self, database_id: str) -> Dict[str, Any]:
        """Get manual metadata config for specific database"""
        
    def get_all_configured_databases(self) -> List[str]:
        """Get list of manually configured database IDs"""
        
    def validate_config(self, database_id: str) -> bool:
        """Validate config against actual Notion database schema"""
```

#### 1.3 Modify Schema Manager
```python
# Modified: services/database_schema_manager.py
class DatabaseSchemaManager:
    def __init__(self, db: Database, database_config: DatabaseConfig):
        self.db = db
        self.database_config = database_config
        
    async def extract_document_metadata(self, document_id: str, page_data: Dict[str, Any], database_id: str):
        # Try manual config first
        manual_config = self.database_config.get_database_metadata_config(database_id)
        
        if manual_config:
            return self._extract_with_manual_config(page_data, manual_config, database_id)
        else:
            # Fallback to automatic inference
            return self._extract_with_automatic_inference(page_data, database_id)
    
    def _extract_with_manual_config(self, page_data: Dict[str, Any], 
                                   manual_config: Dict[str, Any], 
                                   database_id: str) -> Dict[str, Any]:
        """Extract metadata using manual configuration"""
        metadata_record = {
            'document_id': document_id,
            'notion_database_id': database_id,
            'database_fields': {},
            'search_metadata': {},
            'field_mappings': {}
        }
        
        properties = page_data.get('properties', {})
        
        for common_field, field_config in manual_config.items():
            if field_config.get('ignore'):
                continue
                
            notion_field = field_config['notion_field']
            if notion_field in properties:
                # Extract raw value
                raw_value = self._extract_field_value(properties[notion_field], field_config['type'])
                
                if raw_value is not None:
                    # Store in all relevant places
                    metadata_record['database_fields'][notion_field] = raw_value
                    metadata_record[common_field] = self._process_for_common_field(raw_value, field_config)
                    metadata_record['search_metadata'][common_field] = raw_value
                    metadata_record['field_mappings'][notion_field] = common_field
        
        return metadata_record
```

### **Phase 2: Configuration Tools** (1 day)

#### 2.1 Config Generator Script
```python
# New: scripts/generate_database_config.py
"""
Generate databases.toml template from existing Notion databases
"""
async def generate_config_template(database_id: str) -> str:
    """Analyze Notion database and generate config template"""
    # Get database schema from Notion
    # Suggest common field mappings based on field types and names
    # Generate TOML template with comments
    # Include filterable suggestions based on field types
```

#### 2.2 Config Validator
```python
# New: scripts/validate_database_config.py
"""
Validate databases.toml against actual Notion databases
"""
async def validate_all_configs() -> Dict[str, List[str]]:
    """Validate all configured databases and return issues"""
    # Check if notion_field exists in actual database
    # Validate field types match Notion schema
    # Check for missing required fields
    # Report configuration issues
```

### **Phase 3: Integration** (1 day)

#### 3.1 Update Document Processor
```python
# Modified: services/document_processor.py
def __init__(self, ...):
    self.database_config = DatabaseConfig()
    self.schema_manager = DatabaseSchemaManager(db, self.database_config)
```

#### 3.2 Add Configuration Management API
```python
# New: routers/metadata_config.py
@router.get("/metadata/databases")
async def get_configured_databases():
    """Get list of databases with manual configuration"""

@router.get("/metadata/databases/{database_id}/config") 
async def get_database_config(database_id: str):
    """Get manual configuration for specific database"""

@router.post("/metadata/databases/{database_id}/validate")
async def validate_database_config(database_id: str):
    """Validate configuration against Notion database"""

@router.get("/metadata/databases/{database_id}/schema")
async def get_notion_database_schema(database_id: str):
    """Get actual Notion database schema for configuration help"""
```

### **Phase 4: Documentation & Migration** (1 day)

#### 4.1 Create User Documentation
- Configuration file format guide
- Field mapping examples for common scenarios
- Troubleshooting common configuration issues
- Migration guide from automatic to manual
- Multi-language database configuration examples

#### 4.2 Migration Workflow
1. Run config generator for existing databases: `uv run python scripts/generate_database_config.py`
2. Review and customize generated config file
3. Test configuration with validation script
4. Deploy configuration file
5. Monitor extraction results and adjust as needed

## Minimal Schema Changes Required

### **Only One New Table**
```sql
CREATE TABLE database_metadata_configs (
    database_id TEXT PRIMARY KEY,
    database_name TEXT NOT NULL,
    manual_config JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### **Everything Else Unchanged** ✅
- `document_metadata` table: Works perfectly as-is
- `enhanced_metadata_search()` function: No changes needed
- All API models and endpoints: No changes needed
- Frontend TypeScript types: No changes needed
- Search/chat routing logic: No changes needed

## Migration Strategy

### **Backward Compatibility**
```python
async def extract_document_metadata(self, document_id: str, page_data: Dict[str, Any], database_id: str):
    # Priority: Manual config > Automatic inference > Empty
    
    # 1. Try manual configuration
    manual_config = await self.get_manual_config(database_id)
    if manual_config:
        return self._extract_with_manual_config(page_data, manual_config, database_id)
    
    # 2. Fallback to automatic inference  
    auto_schema = await self.get_schema(database_id)
    if auto_schema:
        return self._extract_with_automatic_inference(page_data, auto_schema, database_id)
    
    # 3. No configuration available
    self.logger.warning(f"No metadata configuration found for database {database_id}")
    return {}
```

### **Gradual Rollout**
1. **Automatic Inference Default**: Keep current behavior for unconfigured databases
2. **Manual Config Override**: When `databases.toml` has config for a database, use it
3. **Database-by-Database**: Migrate one database at a time, test, adjust
4. **Zero Downtime**: No disruption to existing functionality

## Benefits Summary

| Manual Definition | Automatic Inference |
|------------------|-------------------|
| ✅ Works with any language | ❌ English-only field names |
| ✅ Precise field control | ❌ Hit-or-miss mapping |
| ✅ Business logic aware | ❌ Generic assumptions |
| ✅ User controls exposure | ❌ No customization |
| ✅ Clear documentation | ❌ Hard to debug failures |
| ✅ Production reliable | ❌ Unpredictable results |
| ❌ Requires setup per DB | ✅ Zero configuration |

## Timeline & Risk Assessment

### **Development Time**: 4-5 days total
- **Phase 1 (Core)**: 2 days
- **Phase 2 (Tools)**: 1 day  
- **Phase 3 (Integration)**: 1 day
- **Phase 4 (Docs)**: 1 day

### **Risk Assessment**: ⭐ Low Risk
- **Minimal schema changes**: Only adding new table
- **Backward compatible**: Automatic inference fallback
- **Incremental rollout**: Database-by-database migration
- **Easy rollback**: Remove config to revert to automatic

## Conclusion

Manual metadata definition provides the precision, international support, and production reliability needed for MVP while requiring minimal implementation effort due to the excellent current schema design. The small upfront investment in configuration pays huge dividends in reliability, maintainability, and user experience.

**The hybrid schema design completed in Week 1+2 is perfectly suited for this approach**, making manual definition the clear architectural choice for the Notion Companion metadata filtering system.