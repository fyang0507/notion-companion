**This doc is meant to be consumed by human developers and coding agent can safely ignore the notes here.**

### Unify RAG strategy and endpoints
In BACKEND_SETUP.md, there are three endpoints already drafted for contextual RAG:
- **POST `/api/chat`**: Streaming chat with RAG
- **POST `/api/search`**: Vector similarity search
- **POST `/api/search/hybrid`**: Hybrid search (vector + full-text)

### Offline copy of Notion data before ingestion (avoid repeated data pull)

### Cache response
Need a toggle for response caching for the same question (when used in production)

### Metadata filtering
* UI container of date filter sizing
* Name/Title column not in metadata (which makes sense but should be added)
* When filter being added, it should restrict the search

### Seeing the log, it seems that there are repeated api calling after some time (not concluding conversation, just let it stay idle for some time)

### Create Evaluation Dataset at scale