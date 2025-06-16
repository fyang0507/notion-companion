-- Drop all tables and functions for clean restart
-- Run this first to clean up everything

-- Drop functions first (they depend on tables)
DROP FUNCTION IF EXISTS hybrid_search_documents(vector, uuid, text[], text[], date, date, jsonb, float, int);
DROP FUNCTION IF EXISTS search_with_multimedia(vector, uuid, boolean, float, int);
DROP FUNCTION IF EXISTS get_document_with_multimedia(uuid);
DROP FUNCTION IF EXISTS update_document_stats();
DROP FUNCTION IF EXISTS cleanup_orphaned_records();

-- Drop tables in dependency order (children first, parents last)
DROP TABLE IF EXISTS search_analytics;
DROP TABLE IF EXISTS document_multimedia;
DROP TABLE IF EXISTS multimedia_assets;
DROP TABLE IF EXISTS document_chunks;
DROP TABLE IF EXISTS document_metadata;
DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS database_schemas;
DROP TABLE IF EXISTS workspaces;

-- Note: Extensions (vector, pg_trgm) are kept as they're managed by Supabase