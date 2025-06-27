# FastAPI Backend

This is the Python FastAPI backend for the Notion Companion RAG application.

## Setup

1. **Install Python Dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
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

- **POST `/api/chat`**: Streaming chat with RAG
- **POST `/api/search`**: Vector similarity search
- **POST `/api/notion/webhook`**: Notion webhook handler
- **GET `/`**: Health check
- **GET `/health`**: Health status

## Development

The server runs on `http://localhost:8000` by default with auto-reload enabled.

Visit `http://localhost:8000/docs` to see the interactive API documentation.

## Architecture

- **FastAPI**: Modern, fast web framework
- **Supabase**: PostgreSQL database with vector search
- **OpenAI**: LLM and embeddings
- **Pydantic**: Data validation and serialization