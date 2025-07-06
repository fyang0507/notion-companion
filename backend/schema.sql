-- Schema for Notion Companion - Simplified Single Workspace Architecture
-- Removes confusing "workspace" terminology and aligns with Notion concepts
--
-- Design Principles:
-- 1. Single Notion workspace/user (no workspace table needed)
-- 2. Notion databases are the primary organizational unit
-- 3. Clear terminology matching Notion's API concepts
-- 4. Simplified architecture for single-user deployment
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
    content_type TEXT DEFAULT 'page',
    
    -- Extracted common metadata
    created_time TIMESTAMP WITH TIME ZONE,
    last_edited_time TIMESTAMP WITH TIME ZONE,
    created_by TEXT,
    last_edited_by TEXT,
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
    has_multimedia BOOLEAN DEFAULT FALSE,
    multimedia_refs JSONB DEFAULT '[]',
    
    -- Timestamps
    indexed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Search optimization
    search_vector tsvector,
    
    -- Constraints
    CONSTRAINT documents_notion_page_unique UNIQUE(notion_page_id),
    CONSTRAINT documents_database_page_unique UNIQUE(notion_database_id, notion_page_id)
);

-- Document chunks for granular search with contextual retrieval support
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Chunk content
    content TEXT NOT NULL,
    chunk_order INTEGER NOT NULL,
    start_char INTEGER,
    end_char INTEGER,
    
    -- Vector embeddings (dual strategy)
    embedding vector(1536),                    -- Standard content embedding
    contextual_embedding vector(1536),         -- Embedding with contextual information
    
    -- Contextual retrieval (Anthropic-style)
    chunk_context TEXT,                        -- How this chunk relates to the document
    chunk_summary TEXT,                        -- Brief summary of chunk content
    document_section TEXT,                     -- Section/heading this chunk belongs to
    section_hierarchy JSONB DEFAULT '{}',     -- Hierarchical path in document
    
    -- Positional linking for context enrichment
    prev_chunk_id UUID REFERENCES document_chunks(id),
    next_chunk_id UUID REFERENCES document_chunks(id),
    chunk_position_metadata JSONB DEFAULT '{}',
    
    -- Content type awareness
    chunk_type TEXT DEFAULT 'content',        -- content, header, list_item, etc.
    content_density_score REAL DEFAULT 0.5,   -- Information density score
    
    -- Token count for processing
    token_count INTEGER DEFAULT 0,
    
    -- Metadata inheritance from parent document
    chunk_metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(document_id, chunk_order)
);

-- Enhanced metadata for multi-database filtering and search
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

-- Multimedia assets support
CREATE TABLE IF NOT EXISTS multimedia_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Asset identification
    notion_file_id TEXT,  -- From Notion API
    asset_type TEXT NOT NULL,  -- 'image', 'file', 'video', etc.
    file_name TEXT,
    file_size BIGINT,
    mime_type TEXT,
    
    -- Storage
    file_url TEXT,  -- Notion CDN URL or local storage path
    local_path TEXT,  -- If stored locally
    
    -- Content analysis
    extracted_text TEXT,  -- OCR or document text extraction
    content_embedding vector(1536),  -- Embedding of extracted content
    
    -- Metadata
    extracted_metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Link multimedia assets to documents
CREATE TABLE IF NOT EXISTS document_multimedia (
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    asset_id UUID NOT NULL REFERENCES multimedia_assets(id) ON DELETE CASCADE,
    
    -- Context within document
    context_description TEXT,
    position_in_document INTEGER,
    
    PRIMARY KEY (document_id, asset_id)
);

-- Search analytics and optimization
CREATE TABLE IF NOT EXISTS search_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Query information
    query_text TEXT NOT NULL,
    query_embedding vector(1536),
    
    -- Filters and context
    database_filters TEXT[],
    metadata_filters JSONB DEFAULT '{}',
    
    -- Results and performance
    result_count INTEGER,
    top_result_similarity REAL,
    response_time_ms INTEGER,
    
    -- User interaction (if applicable)
    clicked_result_ids UUID[],
    user_satisfaction_score INTEGER,  -- 1-5 if provided
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
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
CREATE INDEX IF NOT EXISTS idx_documents_content_type ON documents(content_type);
CREATE INDEX IF NOT EXISTS idx_documents_search_vector ON documents USING GIN(search_vector);

-- Vector similarity indexes
CREATE INDEX IF NOT EXISTS idx_documents_content_embedding ON documents USING ivfflat (content_embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_documents_summary_embedding ON documents USING ivfflat (summary_embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_chunks_contextual_embedding ON document_chunks USING ivfflat (contextual_embedding vector_cosine_ops) WITH (lists = 100);

-- Contextual retrieval indexes
CREATE INDEX IF NOT EXISTS idx_chunks_prev_chunk ON document_chunks(prev_chunk_id);
CREATE INDEX IF NOT EXISTS idx_chunks_next_chunk ON document_chunks(next_chunk_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document_section ON document_chunks(document_section);
CREATE INDEX IF NOT EXISTS idx_chunks_chunk_type ON document_chunks(chunk_type);
CREATE INDEX IF NOT EXISTS idx_chunks_section_hierarchy ON document_chunks USING GIN(section_hierarchy);

-- Metadata indexes
CREATE INDEX IF NOT EXISTS idx_document_metadata_extracted_fields ON document_metadata USING GIN(extracted_fields);
CREATE INDEX IF NOT EXISTS idx_document_metadata_search ON document_metadata USING GIN(metadata_search);

-- Chat indexes
CREATE INDEX IF NOT EXISTS idx_chat_sessions_status ON chat_sessions(status);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_last_message ON chat_sessions(last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_order ON chat_messages(session_id, message_order);

-- Analytics indexes
CREATE INDEX IF NOT EXISTS idx_search_analytics_created ON search_analytics(created_at DESC);
-- Use 'simple' configuration for bilingual query indexing
CREATE INDEX IF NOT EXISTS idx_search_analytics_query ON search_analytics USING GIN(to_tsvector('simple', query_text));

-- ============================================================================
-- HELPER FUNCTIONS
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

-- Hybrid search combining documents and chunks
CREATE OR REPLACE FUNCTION hybrid_search(
    query_embedding vector(1536),
    database_filter text[] DEFAULT NULL,
    content_type_filter text[] DEFAULT NULL,
    metadata_filters jsonb DEFAULT '{}',
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    result_type text,
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
    WITH document_results AS (
        SELECT 
            'document'::text as result_type,
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
            AND (content_type_filter IS NULL OR d.content_type = ANY(content_type_filter))
            AND 1 - (d.content_embedding <=> query_embedding) > match_threshold
    ),
    chunk_results AS (
        SELECT 
            'chunk'::text as result_type,
            dc.id,
            d.title,
            dc.content,
            (1 - (dc.embedding <=> query_embedding))::real as similarity,
            d.extracted_metadata as metadata,
            d.notion_page_id,
            d.page_url
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE dc.embedding IS NOT NULL
            AND (database_filter IS NULL OR d.notion_database_id = ANY(database_filter))
            AND (content_type_filter IS NULL OR d.content_type = ANY(content_type_filter))
            AND 1 - (dc.embedding <=> query_embedding) > match_threshold
    )
    SELECT * FROM (
        SELECT * FROM document_results
        UNION ALL
        SELECT * FROM chunk_results
    ) combined_results
    ORDER BY similarity DESC
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
-- ENHANCED CONTEXTUAL RETRIEVAL FUNCTIONS
-- ============================================================================

-- Function to get chunk with adjacent context for context enrichment
CREATE OR REPLACE FUNCTION get_chunk_with_context(
    chunk_id_param uuid,
    include_adjacent boolean DEFAULT true
)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    result jsonb;
    chunk_record record;
    prev_chunk jsonb DEFAULT null;
    next_chunk jsonb DEFAULT null;
BEGIN
    -- Get the main chunk
    SELECT * INTO chunk_record 
    FROM document_chunks 
    WHERE id = chunk_id_param;
    
    IF NOT FOUND THEN
        RETURN null;
    END IF;
    
    IF include_adjacent THEN
        -- Get previous chunk
        IF chunk_record.prev_chunk_id IS NOT NULL THEN
            SELECT to_jsonb(prev.*) INTO prev_chunk
            FROM document_chunks prev
            WHERE prev.id = chunk_record.prev_chunk_id;
        END IF;
        
        -- Get next chunk  
        IF chunk_record.next_chunk_id IS NOT NULL THEN
            SELECT to_jsonb(next.*) INTO next_chunk
            FROM document_chunks next
            WHERE next.id = chunk_record.next_chunk_id;
        END IF;
    END IF;
    
    -- Build enriched result
    SELECT jsonb_build_object(
        'main_chunk', to_jsonb(chunk_record),
        'prev_chunk', prev_chunk,
        'next_chunk', next_chunk,
        'context_type', 'adjacent_enriched'
    ) INTO result;
    
    RETURN result;
END;
$$;

-- Enhanced chunk search with contextual embeddings
CREATE OR REPLACE FUNCTION match_contextual_chunks(
    query_embedding vector(1536),
    database_filter text[] DEFAULT NULL,
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    chunk_id uuid,
    content text,
    chunk_context text,
    chunk_summary text,
    document_section text,
    contextual_similarity real,
    content_similarity real,
    combined_score real,
    document_id uuid,
    title text,
    notion_page_id text,
    page_url text,
    chunk_index integer
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dc.id as chunk_id,
        dc.content,
        dc.chunk_context,
        dc.chunk_summary,
        dc.document_section,
        -- Contextual embedding similarity (preferred)
        CASE 
            WHEN dc.contextual_embedding IS NOT NULL THEN
                (1 - (dc.contextual_embedding <=> query_embedding))::real
            ELSE 0.0::real
        END as contextual_similarity,
        -- Content embedding similarity (fallback)
        CASE 
            WHEN dc.embedding IS NOT NULL THEN
                (1 - (dc.embedding <=> query_embedding))::real
            ELSE 0.0::real
        END as content_similarity,
        -- Weighted combined score (favor contextual understanding)
        CASE 
            WHEN dc.contextual_embedding IS NOT NULL AND dc.embedding IS NOT NULL THEN
                (
                    (1 - (dc.contextual_embedding <=> query_embedding)) * 0.7 +
                    (1 - (dc.embedding <=> query_embedding)) * 0.3
                )::real
            WHEN dc.contextual_embedding IS NOT NULL THEN
                (1 - (dc.contextual_embedding <=> query_embedding))::real
            WHEN dc.embedding IS NOT NULL THEN
                (1 - (dc.embedding <=> query_embedding))::real
            ELSE 0.0::real
        END as combined_score,
        d.id as document_id,
        d.title,
        d.notion_page_id,
        d.page_url,
        dc.chunk_order as chunk_index
    FROM document_chunks dc
    JOIN documents d ON dc.document_id = d.id
    WHERE (dc.contextual_embedding IS NOT NULL OR dc.embedding IS NOT NULL)
        AND (database_filter IS NULL OR d.notion_database_id = ANY(database_filter))
        AND (
            (dc.contextual_embedding IS NOT NULL AND 1 - (dc.contextual_embedding <=> query_embedding) > match_threshold) OR
            (dc.embedding IS NOT NULL AND 1 - (dc.embedding <=> query_embedding) > match_threshold)
        )
    ORDER BY combined_score DESC
    LIMIT match_count;
END;
$$;

-- Function to get chunks by position for building context windows
CREATE OR REPLACE FUNCTION get_chunks_in_range(
    document_id_param uuid,
    start_chunk_order integer,
    end_chunk_order integer
)
RETURNS TABLE (
    chunk_id uuid,
    content text,
    chunk_summary text,
    chunk_order integer
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dc.id as chunk_id,
        dc.content,
        dc.chunk_summary,
        dc.chunk_order
    FROM document_chunks dc
    WHERE dc.document_id = document_id_param
        AND dc.chunk_order >= start_chunk_order
        AND dc.chunk_order <= end_chunk_order
    ORDER BY dc.chunk_order;
END;
$$;

-- Enhanced hybrid search with contextual awareness
CREATE OR REPLACE FUNCTION hybrid_contextual_search(
    query_embedding vector(1536),
    database_filter text[] DEFAULT NULL,
    content_type_filter text[] DEFAULT NULL,
    metadata_filters jsonb DEFAULT '{}',
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10,
    include_context boolean DEFAULT true
)
RETURNS TABLE (
    result_type text,
    id uuid,
    title text,
    content text,
    chunk_context text,
    chunk_summary text,
    similarity real,
    metadata jsonb,
    notion_page_id text,
    page_url text,
    has_adjacent_context boolean
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH document_results AS (
        SELECT 
            'document'::text as result_type,
            d.id,
            d.title,
            d.content,
            null::text as chunk_context,
            d.summary as chunk_summary,
            (1 - (d.content_embedding <=> query_embedding))::real as similarity,
            d.extracted_metadata as metadata,
            d.notion_page_id,
            d.page_url,
            false as has_adjacent_context
        FROM documents d
        WHERE d.content_embedding IS NOT NULL
            AND (database_filter IS NULL OR d.notion_database_id = ANY(database_filter))
            AND (content_type_filter IS NULL OR d.content_type = ANY(content_type_filter))
            AND 1 - (d.content_embedding <=> query_embedding) > match_threshold
    ),
    contextual_chunk_results AS (
        SELECT 
            'chunk'::text as result_type,
            dc.id,
            d.title,
            dc.content,
            dc.chunk_context,
            dc.chunk_summary,
            CASE 
                WHEN dc.contextual_embedding IS NOT NULL AND dc.embedding IS NOT NULL THEN
                    (
                        (1 - (dc.contextual_embedding <=> query_embedding)) * 0.7 +
                        (1 - (dc.embedding <=> query_embedding)) * 0.3
                    )::real
                WHEN dc.contextual_embedding IS NOT NULL THEN
                    (1 - (dc.contextual_embedding <=> query_embedding))::real
                WHEN dc.embedding IS NOT NULL THEN
                    (1 - (dc.embedding <=> query_embedding))::real
                ELSE 0.0::real
            END as similarity,
            d.extracted_metadata as metadata,
            d.notion_page_id,
            d.page_url,
            (dc.prev_chunk_id IS NOT NULL OR dc.next_chunk_id IS NOT NULL) as has_adjacent_context
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE (dc.contextual_embedding IS NOT NULL OR dc.embedding IS NOT NULL)
            AND (database_filter IS NULL OR d.notion_database_id = ANY(database_filter))
            AND (content_type_filter IS NULL OR d.content_type = ANY(content_type_filter))
            AND (
                (dc.contextual_embedding IS NOT NULL AND 1 - (dc.contextual_embedding <=> query_embedding) > match_threshold) OR
                (dc.embedding IS NOT NULL AND 1 - (dc.embedding <=> query_embedding) > match_threshold)
            )
    )
    SELECT * FROM (
        SELECT * FROM document_results
        UNION ALL
        SELECT * FROM contextual_chunk_results
    ) combined_results
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$;

-- Simplified metadata search with configuration-based filtering (original)
CREATE OR REPLACE FUNCTION search_with_metadata_filters(
    query_embedding vector(1536),
    database_filter text[] DEFAULT NULL,
    metadata_filters jsonb DEFAULT '{}',
    match_threshold float DEFAULT 0.1,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    result_type text,
    id uuid,
    title text,
    content text,
    chunk_context text,
    chunk_summary text,
    similarity real,
    metadata jsonb,
    document_metadata jsonb,
    notion_page_id text,
    page_url text,
    has_adjacent_context boolean,
    database_id text
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH document_results AS (
        SELECT 
            'document'::text as result_type,
            d.id,
            d.title,
            d.content,
            NULL::text as chunk_context,
            NULL::text as chunk_summary,
            CASE 
                WHEN d.summary_embedding IS NOT NULL AND d.content_embedding IS NOT NULL THEN
                    (
                        (1 - (d.summary_embedding <=> query_embedding)) * 0.6 +
                        (1 - (d.content_embedding <=> query_embedding)) * 0.4
                    )::real
                WHEN d.summary_embedding IS NOT NULL THEN
                    (1 - (d.summary_embedding <=> query_embedding))::real
                WHEN d.content_embedding IS NOT NULL THEN
                    (1 - (d.content_embedding <=> query_embedding))::real
                ELSE 0.0::real
            END as similarity,
            d.extracted_metadata as metadata,
            COALESCE(dm.extracted_fields, '{}'::jsonb) as document_metadata,
            d.notion_page_id,
            d.page_url,
            false as has_adjacent_context,
            d.notion_database_id as database_id
        FROM documents d
        LEFT JOIN document_metadata dm ON d.id = dm.document_id
        WHERE (d.summary_embedding IS NOT NULL OR d.content_embedding IS NOT NULL)
            AND (database_filter IS NULL OR d.notion_database_id = ANY(database_filter))
            -- Configuration-based metadata filtering using JSONB containment
            AND (metadata_filters = '{}' OR dm.extracted_fields @> metadata_filters)
            AND (
                (d.summary_embedding IS NOT NULL AND 1 - (d.summary_embedding <=> query_embedding) > match_threshold) OR
                (d.content_embedding IS NOT NULL AND 1 - (d.content_embedding <=> query_embedding) > match_threshold)
            )
    ),
    chunk_results AS (
        SELECT 
            'chunk'::text as result_type,
            dc.id,
            d.title,
            dc.content,
            dc.chunk_context,
            dc.chunk_summary,
            CASE 
                WHEN dc.contextual_embedding IS NOT NULL AND dc.embedding IS NOT NULL THEN
                    (
                        (1 - (dc.contextual_embedding <=> query_embedding)) * 0.7 +
                        (1 - (dc.embedding <=> query_embedding)) * 0.3
                    )::real
                WHEN dc.contextual_embedding IS NOT NULL THEN
                    (1 - (dc.contextual_embedding <=> query_embedding))::real
                WHEN dc.embedding IS NOT NULL THEN
                    (1 - (dc.embedding <=> query_embedding))::real
                ELSE 0.0::real
            END as similarity,
            d.extracted_metadata as metadata,
            COALESCE(dm.extracted_fields, '{}'::jsonb) as document_metadata,
            d.notion_page_id,
            d.page_url,
            (dc.prev_chunk_id IS NOT NULL OR dc.next_chunk_id IS NOT NULL) as has_adjacent_context,
            d.notion_database_id as database_id
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        LEFT JOIN document_metadata dm ON d.id = dm.document_id
        WHERE (dc.contextual_embedding IS NOT NULL OR dc.embedding IS NOT NULL)
            AND (database_filter IS NULL OR d.notion_database_id = ANY(database_filter))
            -- Configuration-based metadata filtering using JSONB containment
            AND (metadata_filters = '{}' OR dm.extracted_fields @> metadata_filters)
            AND (
                (dc.contextual_embedding IS NOT NULL AND 1 - (dc.contextual_embedding <=> query_embedding) > match_threshold) OR
                (dc.embedding IS NOT NULL AND 1 - (dc.embedding <=> query_embedding) > match_threshold)
            )
    )
    SELECT * FROM (
        SELECT * FROM document_results
        UNION ALL
        SELECT * FROM chunk_results
    ) combined_results
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$;

-- Enhanced metadata search function with comprehensive filtering support
-- This function handles the advanced metadata filters expected by the Python code
CREATE OR REPLACE FUNCTION enhanced_metadata_search(
    query_embedding vector(1536),
    database_filter text[] DEFAULT NULL,
    metadata_filters jsonb DEFAULT '{}',
    author_filter text[] DEFAULT NULL,
    tag_filter text[] DEFAULT NULL,
    status_filter text[] DEFAULT NULL,
    date_range_filter jsonb DEFAULT '{}',
    content_type_filter text[] DEFAULT NULL,
    metadata_query_conditions text[] DEFAULT NULL,
    -- Additional field type filters
    text_filter jsonb DEFAULT '{}',           -- For text/rich_text fields: {"field_name": ["value1", "value2"]}
    number_filter jsonb DEFAULT '{}',         -- For number fields: {"field_name": {"min": 1, "max": 100}}
    select_filter jsonb DEFAULT '{}',         -- For select fields: {"field_name": ["option1", "option2"]}
    checkbox_filter jsonb DEFAULT '{}',       -- For checkbox fields: {"field_name": true/false}
    match_threshold float DEFAULT 0.1,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    result_type text,
    id uuid,
    chunk_id uuid,
    title text,
    content text,
    chunk_context text,
    chunk_summary text,
    similarity real,
    final_score real,
    combined_score real,
    contextual_similarity real,
    content_similarity real,
    metadata jsonb,
    document_metadata jsonb,
    notion_page_id text,
    page_url text,
    has_adjacent_context boolean,
    database_id text,
    author text,
    tags text[],
    status text,
    created_date timestamp with time zone,
    modified_date timestamp with time zone,
    document_id uuid,
    chunk_index integer,
    document_section text,
    has_context_enrichment boolean,
    enriched_content text
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH document_results AS (
        SELECT 
            'document'::text as result_type,
            d.id,
            NULL::uuid as chunk_id,
            d.title,
            d.content,
            NULL::text as chunk_context,
            NULL::text as chunk_summary,
            CASE 
                WHEN d.summary_embedding IS NOT NULL AND d.content_embedding IS NOT NULL THEN
                    (
                        (1 - (d.summary_embedding <=> query_embedding)) * 0.6 +
                        (1 - (d.content_embedding <=> query_embedding)) * 0.4
                    )::real
                WHEN d.summary_embedding IS NOT NULL THEN
                    (1 - (d.summary_embedding <=> query_embedding))::real
                WHEN d.content_embedding IS NOT NULL THEN
                    (1 - (d.content_embedding <=> query_embedding))::real
                ELSE 0.0::real
            END as similarity,
            CASE 
                WHEN d.summary_embedding IS NOT NULL AND d.content_embedding IS NOT NULL THEN
                    (
                        (1 - (d.summary_embedding <=> query_embedding)) * 0.6 +
                        (1 - (d.content_embedding <=> query_embedding)) * 0.4
                    )::real
                WHEN d.summary_embedding IS NOT NULL THEN
                    (1 - (d.summary_embedding <=> query_embedding))::real
                WHEN d.content_embedding IS NOT NULL THEN
                    (1 - (d.content_embedding <=> query_embedding))::real
                ELSE 0.0::real
            END as final_score,
            CASE 
                WHEN d.summary_embedding IS NOT NULL AND d.content_embedding IS NOT NULL THEN
                    (
                        (1 - (d.summary_embedding <=> query_embedding)) * 0.6 +
                        (1 - (d.content_embedding <=> query_embedding)) * 0.4
                    )::real
                WHEN d.summary_embedding IS NOT NULL THEN
                    (1 - (d.summary_embedding <=> query_embedding))::real
                WHEN d.content_embedding IS NOT NULL THEN
                    (1 - (d.content_embedding <=> query_embedding))::real
                ELSE 0.0::real
            END as combined_score,
            0.0::real as contextual_similarity,
            CASE 
                WHEN d.content_embedding IS NOT NULL THEN
                    (1 - (d.content_embedding <=> query_embedding))::real
                ELSE 0.0::real
            END as content_similarity,
            d.extracted_metadata as metadata,
            COALESCE(dm.extracted_fields, '{}'::jsonb) as document_metadata,
            d.notion_page_id,
            d.page_url,
            false as has_adjacent_context,
            d.notion_database_id as database_id,
            COALESCE(dm.extracted_fields->>'author', '')::text as author,
            CASE 
                WHEN dm.extracted_fields->'tags' ? 'type' AND dm.extracted_fields->'tags'->>'type' = 'multi_select' THEN
                    ARRAY(SELECT jsonb_array_elements_text(dm.extracted_fields->'tags'->'multi_select'))
                WHEN jsonb_typeof(dm.extracted_fields->'tags') = 'array' THEN
                    ARRAY(SELECT jsonb_array_elements_text(dm.extracted_fields->'tags'))
                ELSE 
                    ARRAY[]::text[]
            END as tags,
            COALESCE(dm.extracted_fields->>'status', '')::text as status,
            d.created_time as created_date,
            d.last_edited_time as modified_date,
            d.id as document_id,
            0 as chunk_index,
            NULL::text as document_section,
            false as has_context_enrichment,
            d.content as enriched_content
        FROM documents d
        LEFT JOIN document_metadata dm ON d.id = dm.document_id
        WHERE (d.summary_embedding IS NOT NULL OR d.content_embedding IS NOT NULL)
            AND (database_filter IS NULL OR d.notion_database_id = ANY(database_filter))
            AND (content_type_filter IS NULL OR d.content_type = ANY(content_type_filter))
            -- Handle metadata filters
            AND (metadata_filters = '{}' OR dm.extracted_fields @> metadata_filters)
            -- Handle author filters
            AND (author_filter IS NULL OR dm.extracted_fields->>'author' = ANY(author_filter))
            -- Handle tag filters (support both array and multi_select format)
            AND (tag_filter IS NULL OR (
                (jsonb_typeof(dm.extracted_fields->'tags') = 'array' AND dm.extracted_fields->'tags' ?| tag_filter) OR
                (dm.extracted_fields->'tags' ? 'multi_select' AND dm.extracted_fields->'tags'->'multi_select' ?| tag_filter)
            ))
            -- Handle status filters
            AND (status_filter IS NULL OR dm.extracted_fields->>'status' = ANY(status_filter))
            -- Handle date range filters
            AND (date_range_filter = '{}' OR (
                (NOT date_range_filter ? 'from' OR d.created_time >= (date_range_filter->>'from')::timestamp with time zone) AND
                (NOT date_range_filter ? 'to' OR d.created_time <= (date_range_filter->>'to')::timestamp with time zone)
            ))
            -- Handle text/rich_text field filters
            AND (text_filter = '{}' OR (
                SELECT bool_and(
                    CASE 
                        WHEN jsonb_typeof(text_filter->field_key) = 'array' THEN
                            dm.extracted_fields->>field_key = ANY(ARRAY(SELECT jsonb_array_elements_text(text_filter->field_key)))
                        ELSE
                            dm.extracted_fields->>field_key = text_filter->>field_key
                    END
                ) 
                FROM jsonb_object_keys(text_filter) AS field_key
            ))
            -- Handle number field filters
            AND (number_filter = '{}' OR (
                SELECT bool_and(
                    CASE 
                        WHEN number_filter->field_key ? 'min' AND number_filter->field_key ? 'max' THEN
                            (dm.extracted_fields->>field_key)::numeric >= (number_filter->field_key->>'min')::numeric AND
                            (dm.extracted_fields->>field_key)::numeric <= (number_filter->field_key->>'max')::numeric
                        WHEN number_filter->field_key ? 'min' THEN
                            (dm.extracted_fields->>field_key)::numeric >= (number_filter->field_key->>'min')::numeric
                        WHEN number_filter->field_key ? 'max' THEN
                            (dm.extracted_fields->>field_key)::numeric <= (number_filter->field_key->>'max')::numeric
                        ELSE
                            (dm.extracted_fields->>field_key)::numeric = (number_filter->>field_key)::numeric
                    END
                )
                FROM jsonb_object_keys(number_filter) AS field_key
            ))
            -- Handle select field filters
            AND (select_filter = '{}' OR (
                SELECT bool_and(
                    CASE 
                        WHEN jsonb_typeof(select_filter->field_key) = 'array' THEN
                            dm.extracted_fields->>field_key = ANY(ARRAY(SELECT jsonb_array_elements_text(select_filter->field_key)))
                        ELSE
                            dm.extracted_fields->>field_key = select_filter->>field_key
                    END
                ) 
                FROM jsonb_object_keys(select_filter) AS field_key
            ))
            -- Handle checkbox field filters
            AND (checkbox_filter = '{}' OR (
                SELECT bool_and(
                    (dm.extracted_fields->>field_key)::boolean = (checkbox_filter->>field_key)::boolean
                )
                FROM jsonb_object_keys(checkbox_filter) AS field_key
            ))
            AND (
                (d.summary_embedding IS NOT NULL AND 1 - (d.summary_embedding <=> query_embedding) > match_threshold) OR
                (d.content_embedding IS NOT NULL AND 1 - (d.content_embedding <=> query_embedding) > match_threshold)
            )
    ),
    chunk_results AS (
        SELECT 
            'chunk'::text as result_type,
            dc.id,
            dc.id as chunk_id,
            d.title,
            dc.content,
            dc.chunk_context,
            dc.chunk_summary,
            CASE 
                WHEN dc.contextual_embedding IS NOT NULL AND dc.embedding IS NOT NULL THEN
                    (
                        (1 - (dc.contextual_embedding <=> query_embedding)) * 0.7 +
                        (1 - (dc.embedding <=> query_embedding)) * 0.3
                    )::real
                WHEN dc.contextual_embedding IS NOT NULL THEN
                    (1 - (dc.contextual_embedding <=> query_embedding))::real
                WHEN dc.embedding IS NOT NULL THEN
                    (1 - (dc.embedding <=> query_embedding))::real
                ELSE 0.0::real
            END as similarity,
            CASE 
                WHEN dc.contextual_embedding IS NOT NULL AND dc.embedding IS NOT NULL THEN
                    (
                        (1 - (dc.contextual_embedding <=> query_embedding)) * 0.7 +
                        (1 - (dc.embedding <=> query_embedding)) * 0.3
                    )::real
                WHEN dc.contextual_embedding IS NOT NULL THEN
                    (1 - (dc.contextual_embedding <=> query_embedding))::real
                WHEN dc.embedding IS NOT NULL THEN
                    (1 - (dc.embedding <=> query_embedding))::real
                ELSE 0.0::real
            END as final_score,
            CASE 
                WHEN dc.contextual_embedding IS NOT NULL AND dc.embedding IS NOT NULL THEN
                    (
                        (1 - (dc.contextual_embedding <=> query_embedding)) * 0.7 +
                        (1 - (dc.embedding <=> query_embedding)) * 0.3
                    )::real
                WHEN dc.contextual_embedding IS NOT NULL THEN
                    (1 - (dc.contextual_embedding <=> query_embedding))::real
                WHEN dc.embedding IS NOT NULL THEN
                    (1 - (dc.embedding <=> query_embedding))::real
                ELSE 0.0::real
            END as combined_score,
            CASE 
                WHEN dc.contextual_embedding IS NOT NULL THEN
                    (1 - (dc.contextual_embedding <=> query_embedding))::real
                ELSE 0.0::real
            END as contextual_similarity,
            CASE 
                WHEN dc.embedding IS NOT NULL THEN
                    (1 - (dc.embedding <=> query_embedding))::real
                ELSE 0.0::real
            END as content_similarity,
            d.extracted_metadata as metadata,
            COALESCE(dm.extracted_fields, '{}'::jsonb) as document_metadata,
            d.notion_page_id,
            d.page_url,
            (dc.prev_chunk_id IS NOT NULL OR dc.next_chunk_id IS NOT NULL) as has_adjacent_context,
            d.notion_database_id as database_id,
            COALESCE(dm.extracted_fields->>'author', '')::text as author,
            CASE 
                WHEN dm.extracted_fields->'tags' ? 'type' AND dm.extracted_fields->'tags'->>'type' = 'multi_select' THEN
                    ARRAY(SELECT jsonb_array_elements_text(dm.extracted_fields->'tags'->'multi_select'))
                WHEN jsonb_typeof(dm.extracted_fields->'tags') = 'array' THEN
                    ARRAY(SELECT jsonb_array_elements_text(dm.extracted_fields->'tags'))
                ELSE 
                    ARRAY[]::text[]
            END as tags,
            COALESCE(dm.extracted_fields->>'status', '')::text as status,
            d.created_time as created_date,
            d.last_edited_time as modified_date,
            d.id as document_id,
            dc.chunk_order as chunk_index,
            dc.document_section,
            (dc.prev_chunk_id IS NOT NULL OR dc.next_chunk_id IS NOT NULL) as has_context_enrichment,
            dc.content as enriched_content
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        LEFT JOIN document_metadata dm ON d.id = dm.document_id
        WHERE (dc.contextual_embedding IS NOT NULL OR dc.embedding IS NOT NULL)
            AND (database_filter IS NULL OR d.notion_database_id = ANY(database_filter))
            AND (content_type_filter IS NULL OR d.content_type = ANY(content_type_filter))
            -- Handle metadata filters
            AND (metadata_filters = '{}' OR dm.extracted_fields @> metadata_filters)
            -- Handle author filters
            AND (author_filter IS NULL OR dm.extracted_fields->>'author' = ANY(author_filter))
            -- Handle tag filters (support both array and multi_select format)
            AND (tag_filter IS NULL OR (
                (jsonb_typeof(dm.extracted_fields->'tags') = 'array' AND dm.extracted_fields->'tags' ?| tag_filter) OR
                (dm.extracted_fields->'tags' ? 'multi_select' AND dm.extracted_fields->'tags'->'multi_select' ?| tag_filter)
            ))
            -- Handle status filters
            AND (status_filter IS NULL OR dm.extracted_fields->>'status' = ANY(status_filter))
            -- Handle date range filters
            AND (date_range_filter = '{}' OR (
                (NOT date_range_filter ? 'from' OR d.created_time >= (date_range_filter->>'from')::timestamp with time zone) AND
                (NOT date_range_filter ? 'to' OR d.created_time <= (date_range_filter->>'to')::timestamp with time zone)
            ))
            -- Handle text/rich_text field filters
            AND (text_filter = '{}' OR (
                SELECT bool_and(
                    CASE 
                        WHEN jsonb_typeof(text_filter->field_key) = 'array' THEN
                            dm.extracted_fields->>field_key = ANY(ARRAY(SELECT jsonb_array_elements_text(text_filter->field_key)))
                        ELSE
                            dm.extracted_fields->>field_key = text_filter->>field_key
                    END
                ) 
                FROM jsonb_object_keys(text_filter) AS field_key
            ))
            -- Handle number field filters
            AND (number_filter = '{}' OR (
                SELECT bool_and(
                    CASE 
                        WHEN number_filter->field_key ? 'min' AND number_filter->field_key ? 'max' THEN
                            (dm.extracted_fields->>field_key)::numeric >= (number_filter->field_key->>'min')::numeric AND
                            (dm.extracted_fields->>field_key)::numeric <= (number_filter->field_key->>'max')::numeric
                        WHEN number_filter->field_key ? 'min' THEN
                            (dm.extracted_fields->>field_key)::numeric >= (number_filter->field_key->>'min')::numeric
                        WHEN number_filter->field_key ? 'max' THEN
                            (dm.extracted_fields->>field_key)::numeric <= (number_filter->field_key->>'max')::numeric
                        ELSE
                            (dm.extracted_fields->>field_key)::numeric = (number_filter->>field_key)::numeric
                    END
                )
                FROM jsonb_object_keys(number_filter) AS field_key
            ))
            -- Handle select field filters
            AND (select_filter = '{}' OR (
                SELECT bool_and(
                    CASE 
                        WHEN jsonb_typeof(select_filter->field_key) = 'array' THEN
                            dm.extracted_fields->>field_key = ANY(ARRAY(SELECT jsonb_array_elements_text(select_filter->field_key)))
                        ELSE
                            dm.extracted_fields->>field_key = select_filter->>field_key
                    END
                ) 
                FROM jsonb_object_keys(select_filter) AS field_key
            ))
            -- Handle checkbox field filters
            AND (checkbox_filter = '{}' OR (
                SELECT bool_and(
                    (dm.extracted_fields->>field_key)::boolean = (checkbox_filter->>field_key)::boolean
                )
                FROM jsonb_object_keys(checkbox_filter) AS field_key
            ))
            AND (
                (dc.contextual_embedding IS NOT NULL AND 1 - (dc.contextual_embedding <=> query_embedding) > match_threshold) OR
                (dc.embedding IS NOT NULL AND 1 - (dc.embedding <=> query_embedding) > match_threshold)
            )
    )
    SELECT * FROM (
        SELECT * FROM document_results
        UNION ALL
        SELECT * FROM chunk_results
    ) combined_results
    ORDER BY final_score DESC
    LIMIT match_count;
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
ALTER TABLE multimedia_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_multimedia ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

-- Simple policies (single user, allow all operations)
CREATE POLICY "Allow all operations" ON notion_databases FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON documents FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON document_metadata FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON document_chunks FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON multimedia_assets FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON document_multimedia FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON search_analytics FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON chat_sessions FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON chat_messages FOR ALL USING (true);

-- ============================================================================
-- INITIAL SETUP
-- ============================================================================

-- Note: This schema removes the concept of "workspaces" entirely
-- The application operates within a single Notion workspace/user context
-- Notion databases are the primary organizational unit for content