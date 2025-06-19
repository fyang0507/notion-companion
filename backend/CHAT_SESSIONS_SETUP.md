# Chat Sessions Setup Instructions

To enable chat history and session management in your Notion Companion, you need to deploy the chat sessions database schema to your Supabase instance.

## Quick Setup

1. **Open Supabase SQL Editor**:
   - Go to your Supabase project dashboard
   - Navigate to "SQL Editor" in the left sidebar

2. **Deploy the Schema**:
   - Copy the contents of `backend/chat_sessions_schema.sql`
   - Paste it into the SQL Editor
   - Click "Run" to execute the schema

3. **Verify Installation**:
   - After running the schema, your Recent Chats section should start working
   - You can create new chat sessions that will be saved and persist between sessions

## What This Adds

The chat sessions schema includes:

- **Chat Sessions Table**: Stores individual chat conversations with metadata
- **Chat Messages Table**: Stores all messages within each chat session
- **Functions & Indexes**: Optimized queries for retrieving recent chats and managing sessions
- **Triggers**: Automatic updates for message counts and timestamps

## Features Enabled

Once deployed, you'll have access to:

- ✅ **Persistent Chat History**: Conversations are saved and can be continued later
- ✅ **Recent Chats Sidebar**: Browse and resume previous conversations
- ✅ **Auto-Save**: Messages are automatically saved as you chat
- ✅ **Chat Management**: Delete old conversations, organize your chat history
- ✅ **Session Titles**: Auto-generated titles based on first message

## Fallback Behavior

If the schema is not deployed, the application will:

- Continue to work normally for temporary chats
- Show "No recent chats" with helpful instructions
- Gracefully handle missing tables without errors
- Allow you to use all other features normally

## File Location

The complete schema is located at:
```
backend/chat_sessions_schema.sql
```

Just copy this file's contents and run it in your Supabase SQL Editor to enable chat sessions.