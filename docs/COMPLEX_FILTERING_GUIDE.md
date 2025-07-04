# Complex Filtering with JSONB Metadata

## Quick Answer to Your Question

**YES**, the simplified JSONB schema supports complex filtering conditions like:
- `publish_date > '2025-01-01'`
- `['news', 'blog'] IN multi_select`

But you need to use PostgreSQL's JSONB operators instead of the basic containment search.

## How to Achieve Complex Filtering

### Current Limitations

The basic `search_with_metadata_filters()` function only supports **exact matches** using JSONB containment (`@>`):

```sql
-- ✅ This works (exact match)
SELECT * FROM search_with_metadata_filters(
    query_embedding,
    NULL,
    '{"status": "published", "author": "张三"}'::jsonb
);

-- ❌ This doesn't work (date ranges, array membership)
-- publish_date > '2025-01-01'
-- ['news', 'blog'] IN multi_select
```

### Solution: PostgreSQL JSONB Operators

PostgreSQL provides powerful JSONB operators for complex queries. Here's how to use them:

## Supported Data Types & Filtering

### 1. **Date Filtering** (`date` fields)

```sql
-- Date greater than
SELECT d.*, dm.extracted_fields 
FROM documents d
LEFT JOIN document_metadata dm ON d.id = dm.document_id
WHERE (dm.extracted_fields->>'publish_date')::date > '2025-01-01';

-- Date range
WHERE (dm.extracted_fields->>'publish_date')::date BETWEEN '2025-01-01' AND '2025-12-31';

-- Date less than or equal
WHERE (dm.extracted_fields->>'due_date')::date <= '2025-06-30';
```

### 2. **Multi-Select/Array Filtering** (`multi_select` fields)

```sql
-- Contains ANY of the specified values
WHERE dm.extracted_fields->'tags' ?| ARRAY['news', 'blog'];

-- Contains ALL of the specified values  
WHERE dm.extracted_fields->'tags' ?& ARRAY['AI', 'tech'];

-- Exact array match
WHERE dm.extracted_fields->'tags' = '["news", "blog"]'::jsonb;

-- Check if specific value exists in array
WHERE dm.extracted_fields->'tags' ? 'news';
```

### 3. **Numeric Filtering** (`number` fields)

```sql
-- Greater than
WHERE (dm.extracted_fields->>'priority')::numeric > 5;

-- Range queries
WHERE (dm.extracted_fields->>'score')::numeric BETWEEN 80 AND 100;

-- Less than or equal
WHERE (dm.extracted_fields->>'rating')::numeric <= 3;
```

### 4. **Text/Select Filtering** (`text`, `select`, `status` fields)

```sql
-- Case-insensitive text search
WHERE LOWER(dm.extracted_fields->>'author') LIKE LOWER('%zhang%');

-- Multiple status values
WHERE dm.extracted_fields->>'status' IN ('published', 'reviewed');

-- Text contains
WHERE dm.extracted_fields->>'title' ILIKE '%notion%';
```

### 5. **Checkbox Filtering** (`checkbox` fields)

```sql
-- Boolean exact match
WHERE (dm.extracted_fields->>'is_featured')::boolean = true;

-- Check if field exists and is true
WHERE dm.extracted_fields->>'is_public' = 'true';
```

## Practical Examples

### Example 1: Complex Date + Array Query

Find articles published after 2025-01-01 with tags containing 'news' OR 'blog':

```sql
SELECT d.*, dm.extracted_fields 
FROM documents d
LEFT JOIN document_metadata dm ON d.id = dm.document_id
WHERE (dm.extracted_fields->>'publish_date')::date > '2025-01-01'
  AND dm.extracted_fields->'tags' ?| ARRAY['news', 'blog'];
```

### Example 2: Multi-Condition Filter

Find high-priority published articles by specific author:

```sql
SELECT d.*, dm.extracted_fields 
FROM documents d
LEFT JOIN document_metadata dm ON d.id = dm.document_id
WHERE dm.extracted_fields->>'status' = 'published'
  AND dm.extracted_fields->>'author' = '张三'
  AND (dm.extracted_fields->>'priority')::numeric >= 8;
```

### Example 3: Your Exact Use Case

```sql
-- publish_date > '2025-01-01' OR ['news', 'blog'] IN multi_select
SELECT d.*, dm.extracted_fields 
FROM documents d
LEFT JOIN document_metadata dm ON d.id = dm.document_id
WHERE (dm.extracted_fields->>'publish_date')::date > '2025-01-01'
   OR dm.extracted_fields->'tags' ?| ARRAY['news', 'blog'];
```

## Implementation Options

### Option 1: Custom SQL Queries (Recommended)

Write your own SQL queries using JSONB operators for maximum flexibility:

```python
# In your Python code
def search_with_custom_filters(db, query_embedding, custom_where_clause):
    query = """
    SELECT d.*, dm.extracted_fields,
           1 - (d.content_embedding <=> %s) as similarity
    FROM documents d
    LEFT JOIN document_metadata dm ON d.id = dm.document_id
    WHERE d.content_embedding IS NOT NULL
      AND {custom_where}
    ORDER BY similarity DESC
    LIMIT 10
    """.format(custom_where=custom_where_clause)
    
    return db.client.execute(query, [query_embedding]).data

# Usage
results = search_with_custom_filters(
    db, 
    query_embedding,
    """
    (dm.extracted_fields->>'publish_date')::date > '2025-01-01'
    OR dm.extracted_fields->'tags' ?| ARRAY['news', 'blog']
    """
)
```

### Option 2: Enhanced Search Function

Use a helper function that builds dynamic WHERE clauses:

```python
def build_complex_filters(filters):
    """Build WHERE clause from complex filter specifications."""
    conditions = []
    
    # Date filters
    for field, condition in filters.get('date_filters', {}).items():
        if 'gt' in condition:
            conditions.append(f"(dm.extracted_fields->>'{field}')::date > '{condition['gt']}'")
        if 'lt' in condition:
            conditions.append(f"(dm.extracted_fields->>'{field}')::date < '{condition['lt']}'")
    
    # Array filters  
    for field, condition in filters.get('array_filters', {}).items():
        if 'contains_any' in condition:
            values = "', '".join(condition['contains_any'])
            conditions.append(f"dm.extracted_fields->'{field}' ?| ARRAY['{values}']")
        if 'contains_all' in condition:
            values = "', '".join(condition['contains_all'])
            conditions.append(f"dm.extracted_fields->'{field}' ?& ARRAY['{values}']")
    
    # Numeric filters
    for field, condition in filters.get('numeric_filters', {}).items():
        if 'gt' in condition:
            conditions.append(f"(dm.extracted_fields->>'{field}')::numeric > {condition['gt']}")
        if 'gte' in condition:
            conditions.append(f"(dm.extracted_fields->>'{field}')::numeric >= {condition['gte']}")
    
    return ' AND '.join(conditions) if conditions else '1=1'

# Usage
filters = {
    'date_filters': {
        'publish_date': {'gt': '2025-01-01'}
    },
    'array_filters': {
        'tags': {'contains_any': ['news', 'blog']}
    },
    'numeric_filters': {
        'priority': {'gte': 5}
    }
}

where_clause = build_complex_filters(filters)
# Result: "(dm.extracted_fields->>'publish_date')::date > '2025-01-01' 
#          AND dm.extracted_fields->'tags' ?| ARRAY['news', 'blog'] 
#          AND (dm.extracted_fields->>'priority')::numeric >= 5"
```

## Performance Considerations

### Indexing for Complex Queries

```sql
-- Index for JSONB field access
CREATE INDEX idx_metadata_publish_date ON document_metadata 
USING BTREE ((extracted_fields->>'publish_date'));

-- Index for array operations
CREATE INDEX idx_metadata_tags ON document_metadata 
USING GIN ((extracted_fields->'tags'));

-- Index for numeric fields
CREATE INDEX idx_metadata_priority ON document_metadata 
USING BTREE (((extracted_fields->>'priority')::numeric));
```

### Query Optimization Tips

1. **Use specific indexes** for frequently queried fields
2. **Combine filters efficiently** - put most selective filters first
3. **Use EXPLAIN ANALYZE** to check query performance
4. **Consider materialized views** for complex recurring queries

## Summary

✅ **YES** - The JSONB schema supports all the complex filtering you need:

| Filter Type | Example | JSONB Operator |
|-------------|---------|----------------|
| Date ranges | `publish_date > '2025-01-01'` | `(field->>'key')::date > value` |
| Array membership | `['news', 'blog'] IN tags` | `field->'key' ?| ARRAY[...]` |
| Numeric comparison | `priority >= 5` | `(field->>'key')::numeric >= value` |
| Text search | `author LIKE '%zhang%'` | `field->>'key' LIKE pattern` |
| Boolean checks | `is_featured = true` | `(field->>'key')::boolean = value` |

The key is using **PostgreSQL's native JSONB operators** instead of simple containment queries. This gives you the flexibility of a document database with the power of SQL.

**Recommendation**: Start with custom SQL queries for your specific use cases, then create helper functions as patterns emerge. This approach is more maintainable than trying to create a universal dynamic query builder. 