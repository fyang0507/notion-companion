**This doc is meant to be consumed by human developers and coding agent can safely ignore the notes here.**

### Unify RAG strategy and endpoints
In BACKEND_SETUP.md, there are three endpoints already drafted for contextual RAG:
- **POST `/api/chat`**: Streaming chat with RAG
- **POST `/api/search`**: Vector similarity search
- **POST `/api/search/hybrid`**: Hybrid search (vector + full-text)

### Offline copy of Notion data before ingestion (avoid repeated data pull)

### Cache response
Need a toggle for response caching for the same question (when used in production)

### ✅ Metadata filtering - COMPLETED
**Status**: Implemented with simplified configuration-based approach
- Replaced complex typed metadata schema with simple JSONB `extracted_fields`
- Configuration-driven metadata extraction via `databases.toml`
- Simplified search functions using JSONB containment queries
- Migration script provided for existing databases

### Remaining metadata tasks:
- Test the new simplified filtering with different database configurations
- Add UI components for filtering based on extracted fields
- ✅ Complex filtering support documented (see COMPLEX_FILTERING_GUIDE.md)

### Complex Filtering Capabilities Added:
- Date range queries: `publish_date > '2025-01-01'`
- Array membership: `['news', 'blog'] IN multi_select`
- Numeric comparisons: `priority >= 5`
- Text search with LIKE patterns
- Boolean filtering for checkbox fields
- Performance indexing strategies documented

### Seeing the log, it seems that there are repeated api calling after some time (not concluding conversation, just let it stay idle for some time)

### Create Evaluation Dataset at scale