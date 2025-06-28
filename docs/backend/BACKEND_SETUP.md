# FastAPI Backend

This is the Python FastAPI backend for the Notion Companion RAG application.

## Setup

1. **Install Python Dependencies**:
   ```bash
   cd backend
   uv sync
   ```

2. **Environment Variables**:
   Copy `.env.example` to `.env` and fill in your values:
   ```bash
   cp .env.example .env
   ```

3. **Start the Server**:
   ```bash
   python start.py
   ```
   
   Or manually:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## API Endpoints

### Core Endpoints
- **GET `/`**: API information and health status

### Chat & RAG
- **POST `/api/chat`**: Streaming chat with RAG
- **POST `/api/search`**: Vector similarity search
- **POST `/api/search/hybrid`**: Hybrid search (vector + full-text)

> **🔮 Future Consolidation**: Plan to consolidate RAG strategy by keeping one endpoint for conversation (`/api/chat`) and one unified endpoint for pure RAG search (consolidating current `/api/search` and `/api/search/hybrid` functionality). This will simplify the API surface and reduce maintenance overhead while maintaining full functionality.

### Chat Sessions

#### Core Session Management
- **GET `/api/chat-sessions/recent`**: Get recent chat sessions
- **POST `/api/chat-sessions/`**: Create new chat session
- **GET `/api/chat-sessions/{session_id}`**: Get chat session with messages
- **PUT `/api/chat-sessions/{session_id}`**: Update chat session
- **DELETE `/api/chat-sessions/{session_id}`**: Delete chat session
- **POST `/api/chat-sessions/{session_id}/resume`**: Resume chat session
- **GET `/api/chat-sessions/current-active`**: Get current active session

#### Message Persistence
- **POST `/api/chat-sessions/{session_id}/messages`**: Add single message to session
  - *Purpose*: Persist individual messages during active conversation
  - *Actions*: Saves content, tokens, citations; auto-generates title from first user message
  - *When*: Called for each message during chat flow (primary persistence method)

#### Session Lifecycle Management

**Foundational API:**
- **POST `/api/chat-sessions/{session_id}/conclude`**: Conclude chat session with AI enhancement
  - *Purpose*: Finalize conversation with intelligent title/summary generation
  - *Actions*: Re-generates title using full conversation context, creates AI summary, marks as concluded
  - *When*: Called when conversation lifecycle ends
  - *Note*: This is a foundational API used by trigger endpoints below

**Trigger APIs** (all use `/conclude` internally):
- **POST `/api/chat-sessions/{session_id}/conclude-for-new-chat`**: Conclude for new chat
- **POST `/api/chat-sessions/{session_id}/conclude-for-resume`**: Conclude for resume
- **POST `/api/chat-sessions/{session_id}/window-close`**: Handle window close
- **POST `/api/chat-sessions/{session_id}/window-refresh`**: Handle window refresh

### Notion Integration
- **POST `/api/notion/webhook`**: Notion webhook handler for real-time sync

### Bootstrap & Management
- **POST `/api/bootstrap/bootstrap`**: Start bootstrap process
- **GET `/api/bootstrap/bootstrap/{job_id}/status`**: Get bootstrap status
- **DELETE `/api/bootstrap/bootstrap/{job_id}`**: Cancel bootstrap job
- **GET `/api/bootstrap/databases/stats`**: Get database statistics
- **DELETE `/api/bootstrap/databases/{database_id}/documents`**: Clear database documents

### Development & Debugging
- **POST `/api/logs/frontend`**: Submit frontend logs

## Development

The server runs on `http://localhost:8000` by default with auto-reload enabled.

Visit `http://localhost:8000/docs` to see the interactive API documentation.

## Architecture

- **FastAPI**: Modern, fast web framework
- **Supabase**: PostgreSQL database with vector search
- **OpenAI**: LLM and embeddings
- **Pydantic**: Data validation and serialization