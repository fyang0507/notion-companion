**This doc is meant to be consumed by human developers and coding agent can safely ignore the notes here.**

### Unify RAG strategy and endpoints
In BACKEND_SETUP.md, there are three endpoints already drafted for contextual RAG:
- **POST `/api/chat`**: Streaming chat with RAG
- **POST `/api/search`**: Vector similarity search
- **POST `/api/search/hybrid`**: Hybrid search (vector + full-text)

### Offline copy of Notion data before ingestion (avoid repeated data pull)

### FE tests

### Cache response
Need a toggle for response caching for the same question (when used in production)

### Metadata filtering