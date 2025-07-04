# Dynamic Filter Implementation

## Overview

The dynamic filter system replaces hardcoded filter categories with metadata-driven filters that automatically adapt to the database configuration defined in `backend/config/databases.toml`.

## Architecture

### Backend Configuration (`backend/config/databases.toml`)

```toml
[databases.metadata.author]
notion_field = "Author"
type = "text" 
description = "文章作者"
filterable = true

[databases.metadata.published_date]
notion_field = "Date"
type = "date"
description = "文章创建日期"
filterable = true

[databases.metadata.status]
notion_field = "Status"
type = "status"
description = "文章阅读状态"
filterable = true

[databases.metadata.select]
notion_field = "Select"
type = "select"
description = "文章类型"
filterable = true

[databases.metadata.tags]
notion_field = "Multi-select"
type = "multi_select"
description = "文章标签"
filterable = true
```

### API Endpoints

**Database Schema Endpoint**: `GET /api/metadata/databases`
- Returns database configurations with field definitions
- Includes field types, descriptions, and filterability

**Aggregated Fields Endpoint**: `GET /api/metadata/aggregated-fields?field_names=author,tags,status`
- Returns unique values and counts for specified fields
- Used to populate filter options

### Frontend Components

#### 1. Dynamic Filter Types (`types/chat.ts`)

```typescript
export interface ChatFilter {
  workspaces: string[];
  dateRange: {
    from?: Date;
    to?: Date;
  };
  searchQuery: string;
  // Dynamic metadata fields - keys correspond to field names from database config
  metadataFilters: Record<string, string[]>; // field_name -> selected values
}

export interface DatabaseFieldDefinition {
  field_name: string;
  field_type: 'text' | 'date' | 'status' | 'select' | 'multi_select' | 'number' | 'checkbox';
  notion_field: string;
  description: string;
  is_filterable: boolean;
  sample_values?: string[] | null;
}
```

#### 2. Dynamic Filter Component (`components/dynamic-filter-section.tsx`)

**Features**:
- **Field Type Support**: Different UI controls for text, date, status, select, multi_select
- **Visual Distinction**: Color-coded icons and styling for different field types
- **Interactive Controls**: Checkboxes for multi-select, date inputs for date fields
- **Loading States**: Skeleton loading for async data fetching
- **Collapsible Sections**: Expandable/collapsible filter sections

**Field Type Mappings**:
- `text` → Blue, Type icon
- `date` → Green, Calendar icon with date inputs
- `status` → Purple, CheckCircle2 icon
- `select` → Orange, FileText icon
- `multi_select` → Pink, Tag icon
- `number` → Indigo, Hash icon

#### 3. Updated Chat Filter Bar (`components/chat-filter-bar.tsx`)

**Key Changes**:
- **Removed Hardcoded Sections**: No more "Document Types", "Authors", "Tags"
- **Dynamic Section Generation**: Sections generated based on selected database schemas
- **Database-Aware Filtering**: Filters adapt when database selection changes
- **Metadata State Management**: Uses `metadataFilters` object instead of separate arrays

### Data Flow

1. **User selects databases** → Filter bar fetches database schemas
2. **Database schemas loaded** → Available filter fields determined from `field_definitions`
3. **Filter sections rendered** → Dynamic components created based on field types
4. **User selects filter values** → `metadataFilters` state updated
5. **Search/Chat request** → Filters passed to backend in new structure

### Migration from Hardcoded Filters

**Before (Hardcoded)**:
```typescript
interface ChatFilter {
  workspaces: string[];
  documentTypes: string[];  // ❌ Hardcoded
  authors: string[];        // ❌ Hardcoded
  tags: string[];          // ❌ Hardcoded
  dateRange: {...};
  searchQuery: string;
}
```

**After (Dynamic)**:
```typescript
interface ChatFilter {
  workspaces: string[];
  dateRange: {...};
  searchQuery: string;
  metadataFilters: Record<string, string[]>; // ✅ Dynamic
}

// Example metadataFilters:
{
  "author": ["张三", "李四"],
  "status": ["已完成", "进行中"],
  "tags": ["技术", "工具"]
}
```

## Benefits

1. **Configuration-Driven**: Filter options automatically match database schema
2. **Multilingual Support**: Field descriptions support Chinese and other languages
3. **Type-Safe**: TypeScript interfaces ensure type safety
4. **Extensible**: New field types can be added without code changes
5. **Database-Specific**: Filters adapt to selected databases
6. **Better UX**: Visual distinction between field types, loading states, collapsible sections

## Testing

- **Frontend**: Linting passed, React hooks issues resolved
- **Backend**: Metadata API endpoints responding correctly
- **Integration**: Database selection triggers dynamic filter updates
- **Demo Mode**: Graceful fallback when no data available

## Configuration Example

To add a new filterable field:

1. **Add to `databases.toml`**:
```toml
[databases.metadata.priority]
notion_field = "Priority"
type = "select"
description = "任务优先级"
filterable = true
```

2. **Restart backend** → Field automatically appears in filter UI
3. **No frontend changes needed** → Dynamic components handle new field type

## Future Enhancements

- **Field Value Caching**: Cache unique values for better performance
- **Advanced Date Filtering**: Custom date range presets
- **Field Dependencies**: Conditional filters based on other selections
- **Bulk Filter Actions**: Select/clear all options
- **Filter Presets**: Save and load filter configurations 