# Conversation State Management Specification

*Last Updated: 2025-07-16*

## Overview

The conversation state management system handles chat session lifecycle across frontend and backend layers, with automatic session management, persistence, and intelligent state transitions.

## Architecture

### Backend Components
- **Database Tables**: `chat_sessions`, `chat_messages` with status states (`active`, `concluded`, `deleted`)
- **API Layer**: `api/routers/chat_sessions.py` with REST endpoints
- **Service Layer**: `rag/services/chat_session_service.py` with business logic
- **Key Constraint**: Only one active session at a time

### Frontend Components
- **State Hook**: `hooks/use-chat-sessions.ts` manages session state
- **Lifecycle Hook**: `hooks/use-session-lifecycle.ts` handles cleanup
- **Temporary Chat Pattern**: Seamless transition from temporary to permanent sessions

## State Flow

### Session Creation
```
User clicks "New Chat" → startTemporaryChat() → isTemporaryChat = true
User sends first message → addMessage() → createChatSession() → permanent session
```

### Message Flow
```
Frontend: addMessage() → immediate UI update
Backend: process message → save to database → generate AI response
→ stream response → update message state
```

### Session Conclusion
```
Trigger (idle/new chat/window close) → conclude_session()
→ AI generates title/summary → status: 'concluded'
```

## Key Patterns

### Single Source of Truth
- **Backend database** is authoritative state store
- **Frontend state** is ephemeral and UI-focused
- **No client-side persistence** beyond current session

### Optimistic Updates
- **UI updates immediately** when user sends message
- **Backend processes asynchronously** in parallel
- **Error states handled** if backend operations fail

### State Machine Pattern
- **Clear transitions**: `temporary → active → concluded`
- **Consistent rules**: one active session constraint
- **Automated management**: 10-minute idle timeout

## API Contract

### Core Endpoints
- `POST /api/chat-sessions/` - Create new session
- `GET /api/chat-sessions/{id}` - Load session with messages
- `POST /api/chat-sessions/{id}/messages` - Add message
- `POST /api/chat-sessions/{id}/conclude` - Conclude with AI title/summary
- `POST /api/chat-sessions/{id}/resume` - Resume concluded session

### State Synchronization
- **Backend-first persistence** - messages saved immediately
- **Real-time updates** via streaming responses
- **Session metadata** updated after each message

## Error Handling

### Frontend Recovery
- **API timeout protection** (5-second timeout)
- **Graceful degradation** (empty arrays vs errors)
- **Retry mechanisms** for failed messages

### Backend Safety
- **Database transactions** with rollback on errors
- **Fallback title generation** if AI fails
- **Idle session cleanup** with error recovery

## Performance Optimizations

- **Minimal re-renders** using React hooks and memoization
- **Debounced operations** for frequent state changes
- **Lazy loading** of session history
- **Indexed database queries** for efficient retrieval