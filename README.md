# Notion Companion RAG Application

A production-ready AI-powered knowledge assistant that connects to your Notion workspace, providing intelligent search and chat capabilities with real-time synchronization.

## Features

- **Real-time Notion Integration**: Automatic webhook-based synchronization with your Notion workspace
- **Intelligent Search**: Hybrid vector and semantic search with Cohere reranking
- **AI Chat Interface**: Stream-enabled chat with GPT-4 and source citations
- **Token Management**: Per-user monthly quotas and usage tracking
- **Responsive Design**: Modern UI with dark/light theme support
- **Production Ready**: Built for scale with proper error handling and monitoring

## Architecture

- **Frontend**: Next.js 13.5 with Tailwind CSS and shadcn/ui
- **Backend**: FastAPI with async Python 3.8+
- **Database**: Supabase with pgvector for embeddings
- **AI Models**: OpenAI embeddings + GPT-4
- **Deployment**: Frontend on Vercel, FastAPI backend on your preferred platform

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.8+
- Notion workspace with admin access

### Installation

1. **Clone and setup environment**:
```bash
git clone <repository>
cd notion-companion
```

2. **Install frontend dependencies**:
```bash
npm install
```

3. **Install backend dependencies**:
```bash
cd backend
pip install -r requirements.txt
```

4. **Configure environment variables**:

For **frontend** (`.env.local`):
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

For **backend** (`backend/.env`):
```env
OPENAI_API_KEY=your_openai_api_key
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

5. **Start development servers**:

Option A - Start both frontend and backend:
```bash
npm run dev:full
```

Option B - Start separately:
```bash
# Terminal 1 - Frontend
npm run dev

# Terminal 2 - Backend
npm run backend
```

### Database Setup

The application uses Supabase with the following schema:

- `users` - User accounts and token quotas
- `workspaces` - Connected Notion workspaces
- `documents` - Processed pages with embeddings
- `chat_sessions` - Chat history and context
- `api_usage` - Token usage tracking

Create the required tables and enable RLS policies using the Supabase dashboard.

## Usage

### Connecting Notion

1. Navigate to the application and sign in
2. Click "Connect Notion Workspace"
3. Authorize the integration in Notion
4. Select workspaces to sync

### Chat Interface

- Ask questions about your Notion content
- Get responses with source citations
- View real-time token usage
- Access chat history

### Search

- Semantic search across all documents
- Hybrid ranking with similarity scores
- Filter by workspace or document type

## API Endpoints

The FastAPI backend provides the following endpoints (served at `http://localhost:8000`):

### Chat
```
POST /api/chat
{
  "messages": [...],
  "workspaceId": "workspace-id",
  "userId": "user-id"
}
```
Returns streaming SSE response with chat content.

### Search
```
POST /api/search
{
  "query": "search terms",
  "workspaceId": "workspace-id",
  "limit": 10
}
```
Returns JSON with search results and similarity scores.

### Webhook
```
POST /api/notion/webhook
# Receives Notion webhook events
```
Processes Notion page updates, creation, and deletion events.

### Documentation
- Interactive API docs: `http://localhost:8000/docs`
- OpenAPI schema: `http://localhost:8000/openapi.json`

## Configuration

### Token Limits
- Free tier: 10,000 tokens/month
- Pro tier: 100,000 tokens/month
- Enterprise: Custom limits

### Sync Settings
- Real-time webhook updates
- Manual sync triggers
- Batch processing for large workspaces

## Deployment

### Vercel Deployment

1. **Connect repository** to Vercel
2. **Set environment variables** in Vercel dashboard
3. **Deploy** - both frontend and API routes deploy automatically

### Supabase Setup

1. Create new Supabase project
2. Enable pgvector extension
3. Run migration scripts
4. Configure RLS policies

## Development

### Project Structure
```
├── app/                 # Next.js app directory
├── components/          # React components
├── lib/                # Frontend utility libraries
├── types/              # TypeScript definitions
├── hooks/              # Custom React hooks
├── backend/            # FastAPI backend
│   ├── main.py         # FastAPI app
│   ├── routers/        # API route handlers
│   ├── services/       # Business logic
│   ├── models.py       # Pydantic models
│   ├── database.py     # Database layer
│   └── requirements.txt # Python dependencies
└── package.json        # Frontend dependencies
```

### Key Components

- `ChatInterface` - Main chat UI with streaming
- `Sidebar` - Workspace and chat navigation
- `MessageCitations` - Source reference display
- `TokenUsageIndicator` - Usage tracking UI

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- Create GitHub issues for bugs
- Check documentation for setup help
- Contact support for enterprise needs