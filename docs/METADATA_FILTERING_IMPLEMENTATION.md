# Metadata-Based Filtering Feature Implementation

## Investigation Summary

The metadata-based filtering feature is **partially implemented but broken** due to critical schema inconsistencies and frontend-backend disconnects.

### Key Issues Identified

1. **Schema Mismatch**: Legacy multi-row vs current single-row document_metadata schemas
2. **Broken Data Pipeline**: Metadata extraction works but uses wrong schema format  
3. **UI-Backend Gap**: Rich filtering UI exists but backend only processes database filters
4. **Multi-Database Problem**: Current design won't scale to different database schemas

### Current State Analysis

#### ✅ What's Working
- Database-level filtering (users can filter by Notion database IDs)
- Vector search infrastructure with robust pgvector implementation
- SQL function foundation that supports advanced filtering
- Well-designed frontend filtering UI architecture

#### ❌ What's Broken
- **Schema Inconsistency**: 
  - `backend/schema.sql`: Single-row per document with predefined columns
  - `app/setup/page.tsx`: Multi-row per document with `(document_id, field_name)` primary key
  - `lib/supabase.ts`: TypeScript types using legacy schema format
  - `database_schema_manager.py`: Code using legacy multi-row format

- **Frontend-Backend Disconnect**:
  - Frontend sends rich filters: document types, authors, tags, date ranges
  - Backend only processes `database_filters`, ignores all other filter types
  - API models missing metadata filter parameters

## Implementation Plan

### 🚨 CRITICAL (Week 1): Fix Schema Inconsistency

#### Task 1.1: Resolve Schema Mismatch
- [X] Update `backend/schema.sql` with hybrid schema design
- [X] Update TypeScript types in `lib/supabase.ts` to match new schema
- [X] Migrate existing data if any (create migration script)
- [X] Update `app/setup/page.tsx` setup SQL to match

#### Task 1.2: Fix Metadata Extraction
- [X] Update `database_schema_manager.py` to use new schema format
- [X] Fix `_convert_to_typed_values()` to populate both typed fields and JSONB
- [X] Test metadata extraction with real Notion data

### 🔥 HIGH PRIORITY (Week 2): Backend API Foundation

#### Task 2.1: Enhanced Request Models
- [X] Add `MetadataFilter` class to `backend/models.py`
- [X] Update `SearchRequest` and `ChatRequest` with metadata filters
- [X] Add validation and type checking for filter parameters

#### Task 2.2: Enhanced SQL Functions
- [X] Create `enhanced_metadata_search()` SQL function
- [X] Update existing search functions to support metadata filtering
- [X] Add proper indexing for metadata search fields

#### Task 2.3: Backend API Updates
- [X] Update `routers/search.py` to process metadata filters
- [X] Update `routers/chat.py` to use enhanced filtering
- [X] Update `contextual_search_engine.py` to pass filters to SQL

### 📊 MEDIUM PRIORITY (Week 3): Metadata APIs
- [ ] Create `routers/metadata.py` with field discovery endpoints
- [ ] Implement database schema analysis caching
- [ ] Add metadata aggregation across databases
- [ ] Enhanced Database Schema Manager with multi-database support

### 🎨 MEDIUM PRIORITY (Week 4): Frontend Integration
- [ ] Replace mock data in `chat-filter-bar.tsx` with API calls
- [ ] Add hooks for dynamic metadata loading
- [ ] Update filter state management
- [ ] Enhanced Filter UI with database-specific fields

## Proposed Architecture

### Hybrid Schema Design
```sql
CREATE TABLE document_metadata (
    document_id UUID PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
    notion_database_id TEXT NOT NULL REFERENCES notion_databases(database_id),
    
    -- Quick-access typed fields for common queries
    title TEXT,
    created_date DATE,
    modified_date DATE,
    author TEXT,
    status TEXT,
    
    -- Flexible per-database metadata storage
    database_fields JSONB DEFAULT '{}',  -- Database-specific fields
    search_metadata JSONB DEFAULT '{}',  -- Optimized for search/filtering
    
    -- Search optimization
    metadata_search tsvector,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Database Schema Registry
```sql
CREATE TABLE database_field_schemas (
    database_id TEXT PRIMARY KEY,
    database_name TEXT NOT NULL,
    field_definitions JSONB NOT NULL,     -- Per-database field schemas
    queryable_fields JSONB NOT NULL,      -- Fields suitable for filtering
    field_mappings JSONB DEFAULT '{}',    -- Map to common fields
    last_analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Testing Strategy

### Critical Test Cases
1. **Schema Migration**: Ensure existing data migrates correctly
2. **Multi-Database Filtering**: Test with databases having different schemas
3. **Performance**: Vector search with complex metadata filters
4. **Edge Cases**: Empty metadata, missing fields, invalid filters

### Testing Commands
```bash
# Component testing
cd backend && uv run python test_metadata_extraction.py

# Integration testing  
cd backend && uv run python test_enhanced_filtering.py

# Frontend testing
pnpm run test:metadata-filters
```

## Success Metrics

### Functional Success
- [ ] Users can filter documents by author, tags, dates from real Notion metadata
- [ ] Filters work consistently across different Notion databases
- [ ] Search results respect all applied metadata filters
- [ ] UI shows actual metadata values, not mock data

### Performance Success
- [ ] Metadata extraction completes within 5 seconds per document
- [ ] Filtered search returns results within 2 seconds
- [ ] UI filter options load within 1 second

### Scalability Success
- [ ] System handles 10+ databases with different metadata schemas
- [ ] Supports 100+ unique metadata fields across databases
- [ ] Performance remains stable with complex filter combinations

## Implementation Status

### ✅ Week 1+2 Progress (COMPLETED)

#### Week 1: Schema Inconsistency Resolution
- ✅ **Updated `backend/schema.sql`** with hybrid schema design supporting multi-database metadata
- ✅ **Updated TypeScript types** in `lib/supabase.ts` to match new schema
- ✅ **Updated setup SQL** in `app/setup/page.tsx` to use new schema
- ✅ **Updated `database_schema_manager.py`** to use new single-row metadata format with field mapping

#### Week 2: Backend API Foundation  
- ✅ **Added `MetadataFilter` class** and enhanced request models to `backend/models.py`
- ✅ **Updated `SearchRequest` and `ChatRequest`** with comprehensive metadata filtering parameters
- ✅ **Created `enhanced_metadata_search()` SQL function** with comprehensive filtering support
- ✅ **Updated `routers/search.py`** to process metadata filters and use enhanced search
- ✅ **Updated `routers/chat.py`** to use enhanced filtering in chat context

### Key Achievements

#### 1. **Multi-Database Schema Architecture**
```sql
-- Enhanced metadata table supporting multiple databases
CREATE TABLE document_metadata (
    document_id UUID PRIMARY KEY,
    notion_database_id TEXT NOT NULL,
    
    -- Common typed fields for fast querying
    title TEXT, author TEXT, status TEXT, tags TEXT[], 
    created_date DATE, modified_date DATE, ...
    
    -- Flexible storage for database-specific fields
    database_fields JSONB DEFAULT '{}',
    search_metadata JSONB DEFAULT '{}',
    field_mappings JSONB DEFAULT '{}'
);

-- Database schema registry for multi-database support
CREATE TABLE database_field_schemas (
    database_id TEXT PRIMARY KEY,
    field_definitions JSONB NOT NULL,
    queryable_fields JSONB NOT NULL,
    field_mappings JSONB DEFAULT '{}'
);
```

#### 2. **Enhanced API Models**
```python
class MetadataFilter(BaseModel):
    field_name: str
    operator: str  # 'equals', 'contains', 'in', 'range', 'exists'
    values: List[Any]

class SearchRequest(BaseModel):
    # ... existing fields ...
    metadata_filters: Optional[List[MetadataFilter]] = None
    author_filters: Optional[List[str]] = None
    tag_filters: Optional[List[str]] = None
    status_filters: Optional[List[str]] = None
    date_range_filter: Optional[DateRangeFilter] = None
```

#### 3. **Enhanced SQL Function**
```sql
CREATE OR REPLACE FUNCTION enhanced_metadata_search(
    query_embedding vector(1536),
    database_filter text[] DEFAULT NULL,
    metadata_filters jsonb DEFAULT '{}',
    author_filter text[] DEFAULT NULL,
    tag_filter text[] DEFAULT NULL,
    status_filter text[] DEFAULT NULL,
    date_range_filter jsonb DEFAULT '{}',
    -- ... more parameters
) RETURNS TABLE (...)
```

#### 4. **Smart API Routing**
- **Advanced filters detected** → Use `enhanced_metadata_search()` function
- **Basic database filtering** → Use existing optimized `contextual_search()` 
- **Backward compatibility** maintained for existing frontend

#### 5. **Field Mapping Intelligence**
Database-specific fields automatically mapped to common fields:
- `"Created By"` (People field) → `author` (text)
- `"Tags"` (Multi-select) → `tags` (array)  
- `"Status"` (Status field) → `status` (text)
- Custom fields stored in `database_fields` JSONB

## Next Steps: Manual Metadata Definition (NEW DIRECTION)

**📋 DECISION**: Based on investigation of Notion API schema structure and multi-language requirements, **manual metadata definition via `databases.toml` configuration** has been chosen over automatic inference for MVP.

### Week 3: Manual Metadata Definition Implementation
- [ ] Create `config/database_config.py` configuration loader for `databases.toml`
- [ ] Add `database_metadata_configs` table to store manual configurations
- [ ] Modify `database_schema_manager.py` to prefer manual config over automatic inference
- [ ] Create config generation tools (`scripts/generate_database_config.py`)
- [ ] Add configuration validation (`scripts/validate_database_config.py`)

### Week 4: Frontend Integration & Configuration Management
- [ ] Create configuration management API (`routers/metadata_config.py`)
- [ ] Replace mock data in `chat-filter-bar.tsx` with real metadata APIs
- [ ] Add dynamic metadata loading hooks for manually configured databases
- [ ] Create user documentation for `databases.toml` format and field mapping

### Manual Definition Benefits
- ✅ **International Support**: Works with Chinese/non-English field names
- ✅ **Production Reliability**: Predictable, debuggable metadata extraction
- ✅ **User Control**: Precise field mapping and exposure control
- ✅ **Minimal Schema Changes**: Current hybrid design works perfectly
- ✅ **Backward Compatible**: Automatic inference remains as fallback

**See**: `docs/MANUAL_METADATA_DEFINITION.md` for detailed analysis and implementation plan.