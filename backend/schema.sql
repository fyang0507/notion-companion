-- Schema V2 for Notion Companion RAG application
-- Hybrid approach: Single-user, flexible metadata handling, multimedia support
--
-- Design Principles:
-- 1. Single-user application (no user table complexity)
-- 2. Hybrid metadata: JSONB + extracted common fields for performance
-- 3. Database-aware schema management
-- 4. Multimedia-ready architecture

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For text search improvements

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Workspaces table (simplified for single workspace)
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL DEFAULT 'Default Workspace',
    notion_access_token TEXT NOT NULL,  -- Encrypted in production
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_sync_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE
);

-- Database schemas registry - tracks Notion database structures
CREATE TABLE IF NOT EXISTS database_schemas (
    database_id TEXT PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    database_name TEXT NOT NULL,
    
    -- Schema definition from Notion API
    notion_schema JSONB NOT NULL,  -- Raw Notion database schema
    
    -- Processed schema for our application
    field_definitions JSONB NOT NULL,  -- Field types, constraints, etc.
    queryable_fields JSONB NOT NULL,   -- Fields we extract to dedicated columns
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_analyzed_at TIMESTAMP WITH TIME ZONE
);

-- Core documents table with hybrid metadata approach
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    database_id TEXT NOT NULL REFERENCES database_schemas(database_id) ON DELETE CASCADE,
    
    -- Notion identifiers
    notion_page_id TEXT NOT NULL,
    notion_database_id TEXT NOT NULL,
    
    -- Core content
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    
    -- Embeddings for different granularities
    title_embedding vector(1536),      -- Title-only embedding for broad matching
    content_embedding vector(1536),    -- Full content embedding (for small docs)
    summary_embedding vector(1536),    -- Summary embedding (for large docs)
    
    -- Common metadata fields (extracted for performance)
    page_url TEXT,
    parent_page_id TEXT,
    
    -- Temporal data (commonly queried)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notion_created_time TIMESTAMP WITH TIME ZONE,
    notion_last_edited_time TIMESTAMP WITH TIME ZONE,
    
    -- Content classification
    content_type TEXT,  -- 'document', 'note', 'project', 'meeting', etc.
    content_length INTEGER,
    token_count INTEGER,
    
    -- Processing status
    processing_status TEXT DEFAULT 'pending',  -- 'pending', 'processing', 'completed', 'failed'
    is_chunked BOOLEAN DEFAULT FALSE,
    chunk_count INTEGER DEFAULT 0,
    
    -- Database-specific metadata (JSONB for flexibility)
    notion_properties JSONB DEFAULT '{}',  -- Raw Notion properties
    extracted_metadata JSONB DEFAULT '{}', -- Processed/normalized metadata
    
    -- Multimedia references
    has_multimedia BOOLEAN DEFAULT FALSE,
    multimedia_refs JSONB DEFAULT '[]',  -- References to multimedia content
    
    -- Constraints
    UNIQUE(workspace_id, notion_page_id),
    UNIQUE(database_id, notion_page_id)
);

-- Extracted metadata for common/queryable fields
CREATE TABLE IF NOT EXISTS document_metadata (
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    field_name TEXT NOT NULL,
    field_type TEXT NOT NULL,  -- 'text', 'number', 'date', 'select', 'multi_select', 'checkbox', etc.
    
    -- Typed values for efficient querying
    text_value TEXT,
    number_value DECIMAL,
    date_value DATE,
    datetime_value TIMESTAMP WITH TIME ZONE,
    boolean_value BOOLEAN,
    array_value TEXT[],
    
    -- Original raw value
    raw_value JSONB,
    
    -- Metadata about the field
    is_indexed BOOLEAN DEFAULT TRUE,
    field_priority INTEGER DEFAULT 0,  -- Higher priority = more important for search
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    PRIMARY KEY (document_id, field_name)
);

-- Document chunks for large documents
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    
    -- Chunk content
    content TEXT NOT NULL,
    embedding vector(1536),
    token_count INTEGER,
    
    -- Chunk context
    section_header TEXT,        -- Parent section title
    hierarchy_path TEXT[],      -- ['Chapter 1', 'Section 1.1', 'Subsection 1.1.1']
    context_before TEXT,        -- Previous chunk overlap
    context_after TEXT,         -- Next chunk overlap
    
    -- Chunk metadata
    start_position INTEGER,     -- Character position in original document
    end_position INTEGER,
    content_type TEXT,          -- 'text', 'code', 'table', 'list', etc.
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(document_id, chunk_index)
);

-- ============================================================================
-- MULTIMEDIA SUPPORT TABLES
-- ============================================================================

-- Multimedia assets referenced in documents
CREATE TABLE IF NOT EXISTS multimedia_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Asset identification
    notion_asset_id TEXT,           -- Notion's internal asset ID
    notion_url TEXT,                -- Original Notion URL
    asset_type TEXT NOT NULL,       -- 'image', 'video', 'audio', 'file', 'embed'
    mime_type TEXT,
    file_size_bytes BIGINT,
    
    -- Asset content
    original_filename TEXT,
    stored_path TEXT,               -- Local/cloud storage path
    thumbnail_path TEXT,            -- Thumbnail for images/videos
    
    -- Extracted content
    extracted_text TEXT,            -- OCR from images, transcripts from audio/video
    extracted_metadata JSONB DEFAULT '{}',
    
    -- Embeddings for multimedia content
    content_embedding vector(1536), -- Embedding of extracted text/description
    visual_embedding vector(512),   -- Image/video visual embedding (future)
    
    -- Processing status
    processing_status TEXT DEFAULT 'pending',
    extraction_completed_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Links between documents and multimedia assets
CREATE TABLE IF NOT EXISTS document_multimedia (
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    asset_id UUID NOT NULL REFERENCES multimedia_assets(id) ON DELETE CASCADE,
    
    -- Context of the multimedia in the document
    position_in_document INTEGER,   -- Order/position in the document
    context_before TEXT,            -- Text before the multimedia
    context_after TEXT,             -- Text after the multimedia
    caption TEXT,                   -- Alt text or caption
    
    -- Relationship metadata
    relationship_type TEXT,         -- 'embedded', 'referenced', 'attached'
    is_primary BOOLEAN DEFAULT FALSE, -- Is this a primary/hero image?
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    PRIMARY KEY (document_id, asset_id)
);

-- ============================================================================
-- SEARCH & ANALYTICS TABLES
-- ============================================================================

-- Search queries and results for learning/improvement
CREATE TABLE IF NOT EXISTS search_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Query information
    query_text TEXT NOT NULL,
    query_type TEXT,  -- 'semantic', 'keyword', 'hybrid', 'filter'
    query_intent TEXT, -- 'factual', 'procedural', 'exploratory'
    
    -- Search parameters
    search_parameters JSONB,
    filters_applied JSONB,
    
    -- Results
    result_count INTEGER,
    top_result_ids UUID[],
    response_time_ms INTEGER,
    
    -- User feedback (if available)
    user_clicked_result_id UUID,
    user_rating INTEGER,  -- 1-5 rating
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Document indexes
CREATE INDEX IF NOT EXISTS idx_documents_database_id ON documents(database_id);
CREATE INDEX IF NOT EXISTS idx_documents_notion_page_id ON documents(notion_page_id);
CREATE INDEX IF NOT EXISTS idx_documents_content_type ON documents(content_type);
CREATE INDEX IF NOT EXISTS idx_documents_notion_last_edited_time ON documents(notion_last_edited_time);
CREATE INDEX IF NOT EXISTS idx_documents_processing_status ON documents(processing_status);
CREATE INDEX IF NOT EXISTS idx_documents_has_multimedia ON documents(has_multimedia);

-- Text search indexes
CREATE INDEX IF NOT EXISTS idx_documents_title_gin ON documents USING gin(title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_documents_content_gin ON documents USING gin(content gin_trgm_ops);

-- Metadata indexes
CREATE INDEX IF NOT EXISTS idx_document_metadata_field_name ON document_metadata(field_name);
CREATE INDEX IF NOT EXISTS idx_document_metadata_field_type ON document_metadata(field_type);
CREATE INDEX IF NOT EXISTS idx_document_metadata_text_value ON document_metadata(text_value);
CREATE INDEX IF NOT EXISTS idx_document_metadata_date_value ON document_metadata(date_value);
CREATE INDEX IF NOT EXISTS idx_document_metadata_number_value ON document_metadata(number_value);

-- Vector indexes (using HNSW for better performance)
CREATE INDEX IF NOT EXISTS idx_documents_content_embedding ON documents 
    USING hnsw (content_embedding vector_cosine_ops) 
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding ON document_chunks 
    USING hnsw (embedding vector_cosine_ops) 
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_multimedia_content_embedding ON multimedia_assets 
    USING hnsw (content_embedding vector_cosine_ops) 
    WITH (m = 16, ef_construction = 64);

-- Chunk indexes
CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_content_type ON document_chunks(content_type);

-- Multimedia indexes
CREATE INDEX IF NOT EXISTS idx_multimedia_assets_type ON multimedia_assets(asset_type);
CREATE INDEX IF NOT EXISTS idx_multimedia_assets_processing_status ON multimedia_assets(processing_status);
CREATE INDEX IF NOT EXISTS idx_document_multimedia_document_id ON document_multimedia(document_id);

-- ============================================================================
-- FUNCTIONS FOR SEARCH AND RETRIEVAL
-- ============================================================================

-- Enhanced vector similarity search with metadata filtering
CREATE OR REPLACE FUNCTION hybrid_search_documents(
    query_embedding vector(1536),
    workspace_id_param uuid,
    database_filter text[] DEFAULT NULL,
    content_type_filter text[] DEFAULT NULL,
    date_range_start date DEFAULT NULL,
    date_range_end date DEFAULT NULL,
    metadata_filters jsonb DEFAULT '{}',
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id uuid,
    database_id text,
    notion_page_id text,
    title text,
    content text,
    similarity float,
    extracted_metadata jsonb,
    content_type text,
    notion_last_edited_time timestamp with time zone,
    page_url text
)
LANGUAGE sql STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    WITH filtered_docs AS (
        SELECT d.*
        FROM documents d
        WHERE d.workspace_id = workspace_id_param
            AND d.content_embedding IS NOT NULL
            AND (database_filter IS NULL OR d.database_id = ANY(database_filter))
            AND (content_type_filter IS NULL OR d.content_type = ANY(content_type_filter))
            AND (date_range_start IS NULL OR d.notion_last_edited_time::date >= date_range_start)
            AND (date_range_end IS NULL OR d.notion_last_edited_time::date <= date_range_end)
            AND (metadata_filters = '{}' OR d.extracted_metadata @> metadata_filters)
    )
    SELECT
        d.id,
        d.database_id,
        d.notion_page_id,
        d.title,
        CASE 
            WHEN length(d.content) > 500 THEN left(d.content, 500) || '...'
            ELSE d.content
        END as content,
        1 - (d.content_embedding <=> query_embedding) as similarity,
        d.extracted_metadata,
        d.content_type,
        d.notion_last_edited_time,
        d.page_url
    FROM filtered_docs d
    WHERE 1 - (d.content_embedding <=> query_embedding) > match_threshold
    ORDER BY d.content_embedding <=> query_embedding
    LIMIT match_count;
$$;

-- Search function that includes multimedia content
CREATE OR REPLACE FUNCTION search_with_multimedia(
    query_embedding vector(1536),
    workspace_id_param uuid,
    include_multimedia boolean DEFAULT TRUE,
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id uuid,
    type text,  -- 'document' or 'multimedia'
    title text,
    content text,
    similarity float,
    metadata jsonb,
    asset_type text  -- NULL for documents
)
LANGUAGE sql STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    WITH document_results AS (
        SELECT 
            d.id,
            'document'::text as type,
            d.title,
            d.content,
            1 - (d.content_embedding <=> query_embedding) as similarity,
            d.extracted_metadata as metadata,
            NULL::text as asset_type
        FROM documents d
        WHERE d.workspace_id = workspace_id_param
            AND d.content_embedding IS NOT NULL
            AND 1 - (d.content_embedding <=> query_embedding) > match_threshold
    ),
    multimedia_results AS (
        SELECT 
            ma.id,
            'multimedia'::text as type,
            COALESCE(ma.original_filename, 'Multimedia Asset') as title,
            COALESCE(ma.extracted_text, '') as content,
            1 - (ma.content_embedding <=> query_embedding) as similarity,
            ma.extracted_metadata as metadata,
            ma.asset_type
        FROM multimedia_assets ma
        JOIN document_multimedia dm ON ma.id = dm.asset_id
        JOIN documents d ON dm.document_id = d.id
        WHERE d.workspace_id = workspace_id_param
            AND ma.content_embedding IS NOT NULL
            AND include_multimedia = TRUE
            AND 1 - (ma.content_embedding <=> query_embedding) > match_threshold
    )
    SELECT * FROM (
        SELECT * FROM document_results
        UNION ALL
        SELECT * FROM multimedia_results
    ) combined_results
    ORDER BY similarity DESC
    LIMIT match_count;
$$;

-- Function to get document with all related multimedia
CREATE OR REPLACE FUNCTION get_document_with_multimedia(document_id_param uuid)
RETURNS JSONB
LANGUAGE sql STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT jsonb_build_object(
        'document', row_to_json(d),
        'multimedia_assets', COALESCE(multimedia_array.assets, '[]'::jsonb)
    )
    FROM documents d
    LEFT JOIN (
        SELECT 
            dm.document_id,
            jsonb_agg(
                jsonb_build_object(
                    'asset', row_to_json(ma),
                    'context', jsonb_build_object(
                        'position', dm.position_in_document,
                        'caption', dm.caption,
                        'relationship_type', dm.relationship_type
                    )
                )
            ) as assets
        FROM document_multimedia dm
        JOIN multimedia_assets ma ON dm.asset_id = ma.id
        WHERE dm.document_id = document_id_param
        GROUP BY dm.document_id
    ) multimedia_array ON d.id = multimedia_array.document_id
    WHERE d.id = document_id_param;
$$;

-- ============================================================================
-- ROW LEVEL SECURITY (simplified for single user)
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE database_schemas ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE multimedia_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_multimedia ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_analytics ENABLE ROW LEVEL SECURITY;

-- Simple policies (can be expanded later for multi-user)
CREATE POLICY "Allow all operations" ON workspaces FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON database_schemas FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON documents FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON document_metadata FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON document_chunks FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON multimedia_assets FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON document_multimedia FOR ALL USING (true);
CREATE POLICY "Allow all operations" ON search_analytics FOR ALL USING (true);

-- ============================================================================
-- HELPER FUNCTIONS FOR MAINTENANCE
-- ============================================================================

-- Update document statistics
CREATE OR REPLACE FUNCTION update_document_stats()
RETURNS void
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    UPDATE documents SET
        chunk_count = (
            SELECT COUNT(*) 
            FROM document_chunks 
            WHERE document_id = documents.id
        ),
        has_multimedia = (
            SELECT COUNT(*) > 0
            FROM document_multimedia
            WHERE document_id = documents.id
        )
    WHERE processing_status = 'completed';
$$;

-- Clean up orphaned records
CREATE OR REPLACE FUNCTION cleanup_orphaned_records()
RETURNS integer
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    WITH deleted_chunks AS (
        DELETE FROM document_chunks
        WHERE document_id NOT IN (SELECT id FROM documents)
        RETURNING 1
    ),
    deleted_metadata AS (
        DELETE FROM document_metadata
        WHERE document_id NOT IN (SELECT id FROM documents)
        RETURNING 1
    ),
    deleted_multimedia AS (
        DELETE FROM document_multimedia
        WHERE document_id NOT IN (SELECT id FROM documents)
        RETURNING 1
    )
    SELECT (
        (SELECT COUNT(*) FROM deleted_chunks) +
        (SELECT COUNT(*) FROM deleted_metadata) + 
        (SELECT COUNT(*) FROM deleted_multimedia)
    )::integer;
$$;

-- ============================================================================
-- SIMPLE SEARCH FUNCTIONS (for backward compatibility)
-- ============================================================================

-- Simple document similarity search function
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(1536),
    workspace_id uuid,
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id uuid,
    title text,
    content text,
    similarity float,
    metadata jsonb,
    notion_page_id text,
    page_url text
)
LANGUAGE sql STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT
        d.id,
        d.title,
        CASE 
            WHEN length(d.content) > 500 THEN left(d.content, 500) || '...'
            ELSE d.content
        END as content,
        1 - (d.content_embedding <=> query_embedding) as similarity,
        d.extracted_metadata as metadata,
        d.notion_page_id,
        d.page_url
    FROM documents d
    WHERE d.workspace_id = workspace_id
        AND d.content_embedding IS NOT NULL
        AND 1 - (d.content_embedding <=> query_embedding) > match_threshold
    ORDER BY d.content_embedding <=> query_embedding
    LIMIT match_count;
$$;

-- Simple chunk similarity search function
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding vector(1536),
    workspace_id uuid,
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    chunk_id uuid,
    document_id uuid,
    chunk_content text,
    chunk_index integer,
    similarity float,
    title text,
    notion_page_id text,
    page_url text
)
LANGUAGE sql STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT
        dc.id as chunk_id,
        dc.document_id,
        dc.content as chunk_content,
        dc.chunk_index,
        1 - (dc.embedding <=> query_embedding) as similarity,
        d.title,
        d.notion_page_id,
        d.page_url
    FROM document_chunks dc
    JOIN documents d ON dc.document_id = d.id
    WHERE d.workspace_id = workspace_id
        AND dc.embedding IS NOT NULL
        AND 1 - (dc.embedding <=> query_embedding) > match_threshold
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
$$;