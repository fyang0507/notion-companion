-- Additional helper functions for the Notion Companion database

-- Function to get chunk count for a workspace
CREATE OR REPLACE FUNCTION get_workspace_chunk_count(workspace_id uuid)
RETURNS TABLE (count bigint)
LANGUAGE sql STABLE
AS $$
    SELECT COUNT(*) as count
    FROM document_chunks c
    JOIN documents d ON c.document_id = d.id
    WHERE d.workspace_id = get_workspace_chunk_count.workspace_id;
$$;

-- Function to get document by notion_page_id
CREATE OR REPLACE FUNCTION get_document_by_notion_page_id(page_id text)
RETURNS TABLE (
    id uuid,
    workspace_id uuid,
    title text,
    content text,
    metadata jsonb
)
LANGUAGE sql STABLE
AS $$
    SELECT 
        d.id,
        d.workspace_id,
        d.title,
        d.content,
        d.metadata
    FROM documents d
    WHERE d.notion_page_id = get_document_by_notion_page_id.page_id;
$$;

-- Function to clean up old API usage records (optional - for maintenance)
CREATE OR REPLACE FUNCTION cleanup_old_api_usage(days_to_keep integer DEFAULT 90)
RETURNS integer
LANGUAGE sql
AS $$
    WITH deleted AS (
        DELETE FROM api_usage
        WHERE created_at < NOW() - INTERVAL '1 day' * days_to_keep
        RETURNING 1
    )
    SELECT COUNT(*)::integer FROM deleted;
$$;