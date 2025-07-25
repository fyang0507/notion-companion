-- Schema for Notion Companion - Basic Semantic Search
-- Simplified architecture focused on core functionality
--
-- Design Principles:
-- 1. Single Notion workspace/user (no workspace table needed)
-- 2. Notion databases are the primary organizational unit
-- 3. Basic semantic search with embeddings
-- 4. Simple metadata filtering
-- 5. Bilingual support (English/Chinese) using 'simple' text search configuration

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Notion databases registry - tracks connected Notion databases
CREATE TABLE IF NOT EXISTS notion_databases (
    database_id TEXT PRIMARY KEY,  -- Notion database ID
    database_name TEXT NOT NULL,
    
    -- Notion API access (single workspace model)
    notion_access_token TEXT NOT NULL,  -- Encrypted in production
    
    -- Database schema from Notion API
    notion_schema JSONB NOT NULL,  -- Raw Notion database schema
    field_definitions JSONB NOT NULL,  -- Field types, constraints, etc.
    queryable_fields JSONB NOT NULL,   -- Fields we extract to dedicated columns
    
    -- Sync and status tracking
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_sync_at TIMESTAMP WITH TIME ZONE,
    last_analyzed_at TIMESTAMP WITH TIME ZONE
);

-- Core documents table - pages from Notion databases
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notion_database_id TEXT NOT NULL REFERENCES notion_databases(database_id) ON DELETE CASCADE,
    
    -- Notion identifiers
    notion_page_id TEXT NOT NULL UNIQUE,
    notion_database_id_ref TEXT NOT NULL,  -- Redundant but useful for constraints
    
    -- Content and metadata
    title TEXT NOT NULL,
    content TEXT,  -- Full page content
    
    -- Extracted common metadata
    created_time TIMESTAMP WITH TIME ZONE,
    last_edited_time TIMESTAMP WITH TIME ZONE,
    page_url TEXT,
    
    -- Full Notion metadata (flexible storage)
    notion_properties JSONB NOT NULL DEFAULT '{}',
    extracted_metadata JSONB DEFAULT '{}',  -- Processed/computed metadata
    
    -- Vector embeddings
    content_embedding vector(1536),  -- OpenAI embedding
    summary TEXT,  -- AI-generated summary for large documents
    summary_embedding vector(1536),  -- Summary embedding for hybrid search
    
    -- Content processing
    token_count INTEGER DEFAULT 0,
    
    -- Timestamps
    indexed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Search optimization
    search_vector tsvector,
    
    -- Constraints
    CONSTRAINT documents_notion_page_unique UNIQUE(notion_page_id),
    CONSTRAINT documents_database_page_unique UNIQUE(notion_database_id, notion_page_id)
);

-- Document chunks for granular search
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Chunk content
    content TEXT NOT NULL,
    chunk_order INTEGER NOT NULL,
    
    -- Vector embeddings (dual strategy)
    embedding vector(1536),                    -- Standard content embedding
    
    -- Positional linking for context enrichment
    prev_chunk_id UUID REFERENCES document_chunks(id),
    next_chunk_id UUID REFERENCES document_chunks(id),
    
    -- Token count for processing
    token_count INTEGER DEFAULT 0,
    
    -- Metadata inheritance from parent document
    chunk_metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(document_id, chunk_order)
);

-- Basic metadata for filtering and search
CREATE TABLE IF NOT EXISTS document_metadata (
    document_id UUID PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
    notion_database_id TEXT NOT NULL REFERENCES notion_databases(database_id) ON DELETE CASCADE,
    
    -- Configuration-based metadata storage (extracted via DatabaseSchemaManager)
    extracted_fields JSONB DEFAULT '{}',    -- Fields extracted based on databases.toml config
    
    -- Search optimization
    metadata_search tsvector,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Chat sessions (simplified - no workspace reference needed)
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Session metadata
    title TEXT NOT NULL DEFAULT 'New Chat',
    summary TEXT,  -- AI-generated summary
    
    -- Session state
    status TEXT DEFAULT 'active',  -- 'active', 'concluded', 'deleted'
    message_count INTEGER DEFAULT 0,
    
    -- Context and filters used in this session
    session_context JSONB DEFAULT '{}',  -- Database filters, models, etc.
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_message_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,  -- For soft delete
    
    -- Search index
    search_vector tsvector
);

-- Chat messages
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    
    -- Message content
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    
    -- AI metadata (for assistant messages)
    model_used TEXT,
    tokens_used INTEGER,
    response_time_ms INTEGER,
    
    -- Context and citations
    citations JSONB DEFAULT '[]',
    context_used JSONB DEFAULT '{}',  -- Database filters, search results used
    
    -- Ordering and timestamps
    message_order INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(session_id, message_order)
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Document search indexes
CREATE INDEX IF NOT EXISTS idx_documents_database_id ON documents(notion_database_id);
CREATE INDEX IF NOT EXISTS idx_documents_last_edited ON documents(last_edited_time DESC);
CREATE INDEX IF NOT EXISTS idx_documents_search_vector ON documents USING GIN(search_vector);

-- Vector similarity indexes
CREATE INDEX IF NOT EXISTS idx_documents_content_embedding ON documents USING ivfflat (content_embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_documents_summary_embedding ON documents USING ivfflat (summary_embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Contextual retrieval indexes
CREATE INDEX IF NOT EXISTS idx_chunks_prev_chunk ON document_chunks(prev_chunk_id);
CREATE INDEX IF NOT EXISTS idx_chunks_next_chunk ON document_chunks(next_chunk_id);

-- Metadata indexes
CREATE INDEX IF NOT EXISTS idx_document_metadata_extracted_fields ON document_metadata USING GIN(extracted_fields);
CREATE INDEX IF NOT EXISTS idx_document_metadata_search ON document_metadata USING GIN(metadata_search);

-- Chat indexes
CREATE INDEX IF NOT EXISTS idx_chat_sessions_status ON chat_sessions(status);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_last_message ON chat_sessions(last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_order ON chat_messages(session_id, message_order);

-- ============================================================================
-- BASIC SEARCH FUNCTIONS
-- ============================================================================

-- Simple document similarity search
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(1536),
    database_filter text[] DEFAULT NULL,
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id uuid,
    title text,
    content text,
    similarity real,
    metadata jsonb,
    notion_page_id text,
    page_url text
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.id,
        d.title,
        d.content,
        (1 - (d.content_embedding <=> query_embedding))::real as similarity,
        d.extracted_metadata as metadata,
        d.notion_page_id,
        d.page_url
    FROM documents d
    WHERE d.content_embedding IS NOT NULL
        AND (database_filter IS NULL OR d.notion_database_id = ANY(database_filter))
        AND 1 - (d.content_embedding <=> query_embedding) > match_threshold
    ORDER BY d.content_embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Chunk similarity search
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding vector(1536),
    database_filter text[] DEFAULT NULL,
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    chunk_id uuid,
    content text,
    similarity real,
    document_id uuid,
    title text,
    notion_page_id text,
    page_url text
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dc.id as chunk_id,
        dc.content,
        (1 - (dc.embedding <=> query_embedding))::real as similarity,
        d.id as document_id,
        d.title,
        d.notion_page_id,
        d.page_url
    FROM document_chunks dc
    JOIN documents d ON dc.document_id = d.id
    WHERE dc.embedding IS NOT NULL
        AND (database_filter IS NULL OR d.notion_database_id = ANY(database_filter))
        AND 1 - (dc.embedding <=> query_embedding) > match_threshold
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Get recent chat sessions
CREATE OR REPLACE FUNCTION get_recent_chat_sessions(
    session_limit int DEFAULT 20
)
RETURNS TABLE (
    id uuid,
    title text,
    summary text,
    message_count integer,
    last_message_at timestamp with time zone,
    created_at timestamp with time zone,
    last_message_preview text
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cs.id,
        cs.title,
        cs.summary,
        cs.message_count,
        cs.last_message_at,
        cs.created_at,
        (
            SELECT cm.content
            FROM chat_messages cm
            WHERE cm.session_id = cs.id
            ORDER BY cm.message_order DESC
            LIMIT 1
        ) as last_message_preview
    FROM chat_sessions cs
    WHERE cs.status IN ('active', 'concluded')
    ORDER BY cs.status DESC, cs.last_message_at DESC  -- active sessions first, then concluded by recency
    LIMIT session_limit;
END;
$$;

-- Get chat session with messages
CREATE OR REPLACE FUNCTION get_chat_session_with_messages(session_id_param uuid)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    result jsonb;
BEGIN
    SELECT jsonb_build_object(
        'session', to_jsonb(cs.*),
        'messages', COALESCE(
            (
                SELECT jsonb_agg(to_jsonb(cm.*) ORDER BY cm.message_order)
                FROM chat_messages cm
                WHERE cm.session_id = session_id_param
            ),
            '[]'::jsonb
        )
    )
    INTO result
    FROM chat_sessions cs
    WHERE cs.id = session_id_param;
    
    RETURN result;
END;
$$;

-- ============================================================================
-- TRIGGERS FOR AUTOMATIC UPDATES
-- ============================================================================

-- Update document timestamps and search vector (bilingual EN/CN support)
CREATE OR REPLACE FUNCTION update_document_on_change()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    -- Use 'simple' configuration for bilingual English/Chinese content
    -- This avoids language-specific stemming and works better with mixed languages
    NEW.search_vector = to_tsvector('simple', coalesce(NEW.title, '') || ' ' || coalesce(NEW.content, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER documents_update_trigger
    BEFORE INSERT OR UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_document_on_change();

-- Update document metadata search vector (bilingual EN/CN support)
CREATE OR REPLACE FUNCTION update_document_metadata_search()
RETURNS TRIGGER AS $$
DECLARE
    searchable_text TEXT := '';
    field_key TEXT;
    field_value TEXT;
BEGIN
    NEW.updated_at = NOW();
    
    -- Extract searchable text from extracted_fields JSONB
    FOR field_key, field_value IN
        SELECT key, value::text
        FROM jsonb_each_text(NEW.extracted_fields)
    LOOP
        searchable_text := searchable_text || ' ' || coalesce(field_value, '');
    END LOOP;
    
    -- Use 'simple' configuration for bilingual metadata
    NEW.metadata_search = to_tsvector('simple', searchable_text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER document_metadata_update_trigger
    BEFORE INSERT OR UPDATE ON document_metadata
    FOR EACH ROW
    EXECUTE FUNCTION update_document_metadata_search();

-- Update chat session search vector (bilingual EN/CN support)
CREATE OR REPLACE FUNCTION update_chat_session_search()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    -- Use 'simple' configuration for bilingual chat titles/summaries
    NEW.search_vector = to_tsvector('simple', coalesce(NEW.title, '') || ' ' || coalesce(NEW.summary, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER chat_sessions_update_trigger
    BEFORE INSERT OR UPDATE ON chat_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_chat_session_search();

-- Update chat session metadata when messages change
CREATE OR REPLACE FUNCTION update_chat_session_on_message_change()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE chat_sessions 
        SET 
            message_count = message_count + 1,
            last_message_at = NEW.created_at,
            updated_at = NOW()
        WHERE id = NEW.session_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE chat_sessions 
        SET 
            message_count = GREATEST(message_count - 1, 0),
            updated_at = NOW()
        WHERE id = OLD.session_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER chat_messages_update_session
    AFTER INSERT OR DELETE ON chat_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_chat_session_on_message_change();

-- ============================================================================
-- ROW LEVEL SECURITY (Simplified for single user)
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE notion_databases ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

-- Simple policies (single user, allow all operations)
CREATE POLICY "Allow all operations" ON notion_databases FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON documents FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON document_metadata FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON document_chunks FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON chat_sessions FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON chat_messages FOR ALL USING (true);

-- ============================================================================
-- INITIAL SETUP
-- ============================================================================

-- Note: This schema focuses on basic semantic search functionality
-- The application operates within a single Notion workspace/user context
-- Notion databases are the primary organizational unit for content