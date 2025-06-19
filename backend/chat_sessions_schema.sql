-- Chat Sessions Schema Extension for Notion Companion
-- Adds chat session management functionality

-- ============================================================================
-- CHAT SESSIONS TABLES
-- ============================================================================

-- Chat sessions table to store individual chat conversations
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    
    -- Session metadata
    title TEXT NOT NULL,
    summary TEXT,  -- Auto-generated summary of the conversation
    
    -- Session state
    status TEXT DEFAULT 'active',  -- 'active', 'archived', 'deleted'
    message_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_message_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Context and filters used in this session
    session_context JSONB DEFAULT '{}',  -- Filters, models, etc.
    
    -- Search index for title and summary
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(summary, ''))
    ) STORED
);

-- Chat messages table to store individual messages within sessions
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    
    -- Message content
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    
    -- Message metadata
    model_used TEXT,  -- Which AI model was used for this response
    tokens_used INTEGER,  -- Token count for this message
    response_time_ms INTEGER,  -- Response time for AI messages
    
    -- Citations and context
    citations JSONB DEFAULT '[]',  -- Citations used in the response
    context_used JSONB DEFAULT '{}',  -- Context and filters applied
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Message ordering within session
    message_order INTEGER NOT NULL,
    
    UNIQUE(session_id, message_order)
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Chat sessions indexes
CREATE INDEX IF NOT EXISTS idx_chat_sessions_workspace_id ON chat_sessions(workspace_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_status ON chat_sessions(status);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_last_message_at ON chat_sessions(last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_created_at ON chat_sessions(created_at DESC);

-- Full-text search index for chat sessions
CREATE INDEX IF NOT EXISTS idx_chat_sessions_search ON chat_sessions USING gin(search_vector);

-- Chat messages indexes
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_role ON chat_messages(role);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_chat_messages_order ON chat_messages(session_id, message_order);

-- ============================================================================
-- FUNCTIONS FOR CHAT SESSION MANAGEMENT
-- ============================================================================

-- Function to get recent chat sessions for a workspace
CREATE OR REPLACE FUNCTION get_recent_chat_sessions(
    workspace_id_param UUID,
    limit_count INTEGER DEFAULT 20
)
RETURNS TABLE (
    id UUID,
    title TEXT,
    summary TEXT,
    message_count INTEGER,
    last_message_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE,
    last_message_preview TEXT
)
LANGUAGE sql STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT 
        cs.id,
        cs.title,
        cs.summary,
        cs.message_count,
        cs.last_message_at,
        cs.created_at,
        -- Get preview of last message
        (
            SELECT cm.content
            FROM chat_messages cm
            WHERE cm.session_id = cs.id
            ORDER BY cm.message_order DESC
            LIMIT 1
        ) as last_message_preview
    FROM chat_sessions cs
    WHERE cs.workspace_id = workspace_id_param
        AND cs.status = 'active'
    ORDER BY cs.last_message_at DESC
    LIMIT limit_count;
$$;

-- Function to get full chat session with messages
CREATE OR REPLACE FUNCTION get_chat_session_with_messages(
    session_id_param UUID
)
RETURNS JSONB
LANGUAGE sql STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT jsonb_build_object(
        'session', row_to_json(cs),
        'messages', COALESCE(messages_array.messages, '[]'::jsonb)
    )
    FROM chat_sessions cs
    LEFT JOIN (
        SELECT 
            cm.session_id,
            jsonb_agg(
                jsonb_build_object(
                    'id', cm.id,
                    'role', cm.role,
                    'content', cm.content,
                    'citations', cm.citations,
                    'model_used', cm.model_used,
                    'tokens_used', cm.tokens_used,
                    'created_at', cm.created_at,
                    'message_order', cm.message_order
                ) ORDER BY cm.message_order
            ) as messages
        FROM chat_messages cm
        WHERE cm.session_id = session_id_param
        GROUP BY cm.session_id
    ) messages_array ON cs.id = messages_array.session_id
    WHERE cs.id = session_id_param;
$$;

-- Function to update chat session metadata
CREATE OR REPLACE FUNCTION update_chat_session_metadata(
    session_id_param UUID,
    new_title TEXT DEFAULT NULL,
    new_summary TEXT DEFAULT NULL
)
RETURNS void
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    UPDATE chat_sessions 
    SET 
        title = COALESCE(new_title, title),
        summary = COALESCE(new_summary, summary),
        updated_at = NOW()
    WHERE id = session_id_param;
$$;

-- Function to archive or delete chat session
CREATE OR REPLACE FUNCTION update_chat_session_status(
    session_id_param UUID,
    new_status TEXT
)
RETURNS void
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    UPDATE chat_sessions 
    SET 
        status = new_status,
        updated_at = NOW()
    WHERE id = session_id_param;
$$;

-- ============================================================================
-- TRIGGERS FOR AUTOMATIC UPDATES
-- ============================================================================

-- Trigger to update message count and last_message_at when messages are added
CREATE OR REPLACE FUNCTION update_chat_session_on_message_change()
RETURNS TRIGGER AS $$
BEGIN
    -- Update session metadata
    UPDATE chat_sessions 
    SET 
        message_count = (
            SELECT COUNT(*) 
            FROM chat_messages 
            WHERE session_id = COALESCE(NEW.session_id, OLD.session_id)
        ),
        last_message_at = (
            SELECT MAX(created_at) 
            FROM chat_messages 
            WHERE session_id = COALESCE(NEW.session_id, OLD.session_id)
        ),
        updated_at = NOW()
    WHERE id = COALESCE(NEW.session_id, OLD.session_id);
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Create triggers
DROP TRIGGER IF EXISTS trg_update_session_on_message_insert ON chat_messages;
CREATE TRIGGER trg_update_session_on_message_insert
    AFTER INSERT ON chat_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_chat_session_on_message_change();

DROP TRIGGER IF EXISTS trg_update_session_on_message_delete ON chat_messages;
CREATE TRIGGER trg_update_session_on_message_delete
    AFTER DELETE ON chat_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_chat_session_on_message_change();

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

-- Enable RLS on chat tables
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

-- Simple policies (can be expanded later for multi-user)
CREATE POLICY "Allow all operations" ON chat_sessions FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON chat_messages FOR ALL USING (true);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to generate chat title from first user message
CREATE OR REPLACE FUNCTION generate_chat_title(first_message TEXT)
RETURNS TEXT
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT CASE 
        WHEN LENGTH(first_message) <= 50 THEN first_message
        ELSE LEFT(first_message, 47) || '...'
    END;
$$;

-- Function to clean up old chat sessions (for maintenance)
CREATE OR REPLACE FUNCTION cleanup_old_chat_sessions(
    days_old INTEGER DEFAULT 90,
    max_sessions_per_workspace INTEGER DEFAULT 100
)
RETURNS INTEGER
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    WITH old_sessions AS (
        DELETE FROM chat_sessions
        WHERE status = 'deleted' 
            AND updated_at < NOW() - INTERVAL '1 day' * days_old
        RETURNING 1
    ),
    excess_sessions AS (
        DELETE FROM chat_sessions
        WHERE id IN (
            SELECT id FROM (
                SELECT id, 
                       ROW_NUMBER() OVER (
                           PARTITION BY workspace_id 
                           ORDER BY last_message_at DESC
                       ) as rn
                FROM chat_sessions
                WHERE status = 'active'
            ) ranked
            WHERE rn > max_sessions_per_workspace
        )
        RETURNING 1
    )
    SELECT (
        (SELECT COUNT(*) FROM old_sessions) +
        (SELECT COUNT(*) FROM excess_sessions)
    )::INTEGER;
$$;