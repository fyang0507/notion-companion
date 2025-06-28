import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

// Check if we have valid Supabase configuration
const hasValidSupabaseConfig = supabaseUrl && 
  supabaseAnonKey && 
  supabaseUrl !== 'your_supabase_url_here' && 
  supabaseAnonKey !== 'your_supabase_anon_key_here'

// Create a placeholder client if no valid config
export const supabase = hasValidSupabaseConfig 
  ? createClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
      }
    })
  : null

// Single Database Model - NO workspace concept
// This webapp supports ONLY ONE Notion workspace with multiple databases
export type Database = {
  public: {
    Tables: {
      // NO workspaces table - single workspace model
      database_schemas: {
        Row: {
          database_id: string
          database_name: string
          notion_schema: any
          field_definitions: any
          queryable_fields: any
          created_at: string
          updated_at: string
          last_analyzed_at?: string
        }
        Insert: {
          database_id: string
          database_name: string
          notion_schema: any
          field_definitions: any
          queryable_fields: any
          created_at?: string
          updated_at?: string
          last_analyzed_at?: string
        }
        Update: {
          database_id?: string
          database_name?: string
          notion_schema?: any
          field_definitions?: any
          queryable_fields?: any
          created_at?: string
          updated_at?: string
          last_analyzed_at?: string
        }
      }
      documents: {
        Row: {
          id: string
          database_id: string
          notion_page_id: string
          notion_database_id?: string
          title: string
          content: string
          title_embedding?: number[]
          content_embedding?: number[]
          summary_embedding?: number[]
          page_url?: string
          parent_page_id?: string
          notion_created_time?: string
          notion_last_edited_time?: string
          content_type: string
          content_length: number
          token_count: number
          notion_properties: any
          extracted_metadata: any
          has_multimedia: boolean
          multimedia_refs: any[]
          is_chunked: boolean
          chunk_count: number
          document_summary?: string
          processing_status: string
          created_at: string
          updated_at: string
        }
      }
      document_chunks: {
        Row: {
          id: string
          document_id: string
          chunk_index: number
          content: string
          embedding?: number[]
          token_count: number
          content_type: string
          created_at: string
        }
      }
      document_metadata: {
        Row: {
          document_id: string
          notion_database_id: string
          title?: string
          created_date?: string
          modified_date?: string
          author?: string
          status?: string
          tags?: string[]
          priority?: string
          assignee?: string
          due_date?: string
          completion_date?: string
          database_fields?: any
          search_metadata?: any
          field_mappings?: any
          metadata_search?: string
          created_at: string
          updated_at: string
        }
      }
      database_field_schemas: {
        Row: {
          database_id: string
          database_name: string
          field_definitions: any
          queryable_fields: any
          field_mappings?: any
          common_field_stats?: any
          total_documents?: number
          last_analyzed_at: string
          analysis_version?: number
          created_at: string
          updated_at: string
        }
      }
      chat_sessions: {
        Row: {
          id: string
          user_id: string
          title: string
          messages: any[]
          database_filters: string[]
          created_at: string
          updated_at: string
        }
      }
      search_analytics: {
        Row: {
          id: string
          user_id: string
          query: string
          result_count: number
          clicked_document_id?: string
          created_at: string
        }
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      match_documents_by_content: {
        Args: {
          query_embedding: number[]
          match_threshold: number
          match_count: number
          database_ids?: string[]
        }
        Returns: {
          id: string
          title: string
          content: string
          extracted_metadata: any
          notion_page_id: string
          database_id: string
          similarity: number
        }[]
      }
      match_document_chunks: {
        Args: {
          query_embedding: number[]
          match_threshold: number
          match_count: number
          database_ids?: string[]
        }
        Returns: {
          id: string
          document_id: string
          content: string
          chunk_index: number
          similarity: number
          document_title: string
          database_id: string
        }[]
      }
    }
    Enums: {
      [_ in never]: never
    }
  }
}