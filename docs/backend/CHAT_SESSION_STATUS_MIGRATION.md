# Chat Session Status System Migration

## Overview

The chat session system has been upgraded from a two-status system (`active`, `deleted`) to a more logical three-status system (`active`, `concluded`, `deleted`) that ensures only one conversation is active at a time.

## Status Definitions

### `active` 
- **Only 1 session can be active at any time**
- Represents the current conversation the user is working on
- Default status for new sessions
- Can receive new messages and interactions

### `concluded`
- Sessions that have been finished but can be resumed
- Created when:
  - User goes idle for 10+ minutes
  - User clicks "New Chat" 
  - User closes/refreshes the window
  - User resumes a different session
- Displayed in Recent chat history
- Can be resumed (becomes `active` again)

### `deleted`
- Soft-deleted sessions (not shown in UI)
- Can potentially be recovered
- Excluded from recent chats and searches

## Key Changes Made

### 1. Database Schema Updates
- Updated `chat_sessions.status` comment to include `concluded`
- Modified `get_recent_chat_sessions()` function to return both `active` and `concluded` sessions
- Active sessions are sorted first, then concluded sessions by recency

### 2. Database Service Layer (`database.py`)
- Added `get_active_session()` - returns the single active session
- Added `conclude_session(session_id)` - marks session as concluded
- Added `resume_session(session_id)` - reactivates a concluded session and concludes any currently active session
- Updated `create_chat_session()` to auto-conclude any existing active session
- Updated `get_recent_chat_sessions()` to include both active and concluded sessions

### 3. Chat Session Service (`chat_session_service.py`)
- Updated `_conclude_session_due_to_idle()` to set status to `concluded`
- Updated `conclude_session()` to set status to `concluded` 
- Enhanced `handle_resume_other_trigger()` to properly resume target sessions
- Added `ensure_single_active_session()` to guarantee single active session constraint

### 4. API Endpoints (`chat_sessions.py`)
- Added `POST /{session_id}/resume` - resume a concluded session
- Added `GET /current-active` - get the currently active session
- Updated `RecentChatSummary` model to include `status` field
- Updated recent chats endpoint to return status information

## API Usage Examples

### Get Current Active Session
```bash
GET /api/chat-sessions/current-active
```
Returns the single active session or `null` if none exists.

### Resume a Concluded Session
```bash
POST /api/chat-sessions/{session_id}/resume
```
Makes the specified session active and concludes any currently active session.

### Create New Session (Auto-Concludes Current)
```bash
POST /api/chat-sessions/
```
Creates a new active session and automatically concludes any existing active session.

## Frontend Integration Guide

### 1. Recent Chats Display
Recent chats now include both `active` and `concluded` sessions with status indicators:

```typescript
interface RecentChatSummary {
  id: string;
  title: string;
  summary?: string;
  status: 'active' | 'concluded' | 'deleted';
  message_count: number;
  last_message_at: string;
  created_at: string;
  last_message_preview?: string;
}
```

### 2. Visual Indicators
- **Active sessions**: Highlighted differently (green border, "Currently Active" badge)
- **Concluded sessions**: Normal appearance with "Resume" option
- Should show maximum 1 active session at any time

### 3. Session Resumption
When user clicks on a concluded session:
```typescript
await api.post(`/api/chat-sessions/${sessionId}/resume`);
// This automatically concludes any currently active session
// and makes the clicked session active
```

### 4. New Chat Flow
When user clicks "New Chat":
```typescript
// Get current active session if any
const currentActive = await api.get('/api/chat-sessions/current-active');

// Conclude it before creating new session
if (currentActive.active_session) {
  await api.post(`/api/chat-sessions/${currentActive.active_session.id}/conclude`, {
    reason: 'new_chat'
  });
}

// Create new session (will auto-conclude any remaining active sessions)
const newSession = await api.post('/api/chat-sessions/', {
  title: 'New Chat'
});
```

## Migration Impact

### Existing Data
- All existing `active` sessions will remain active
- On first backend startup, idle monitoring will automatically conclude sessions idle for 10+ minutes
- No data loss, only status transitions

### Backward Compatibility
- API responses include status field with fallback to `active` for compatibility
- Existing endpoints continue to work
- Database queries handle both old and new status values

## Benefits

1. **Clear UX**: Users always know which conversation is currently active
2. **Automatic Organization**: Idle sessions are automatically concluded and organized
3. **Resumable History**: Easy to resume previous conversations
4. **Performance**: Only one active session reduces resource usage
5. **Logical State Management**: Status transitions reflect actual user behavior

## Testing

To test the new system:

1. **Create multiple sessions** - verify only one stays active
2. **Let session go idle** - verify it gets concluded after 10 minutes
3. **Resume concluded session** - verify it becomes active and others conclude
4. **Create new chat** - verify current active session gets concluded
5. **Check recent chats** - verify both active and concluded sessions appear with correct status 