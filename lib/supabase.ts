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

export type Database = {
  public: {
    Tables: {
      workspaces: {
        Row: {
          id: string
          user_id: string
          notion_workspace_id: string
          name: string
          icon?: string
          is_active: boolean
          last_sync_at?: string
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          user_id: string
          notion_workspace_id: string
          name: string
          icon?: string
          is_active?: boolean
          last_sync_at?: string
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          user_id?: string
          notion_workspace_id?: string
          name?: string
          icon?: string
          is_active?: boolean
          last_sync_at?: string
          created_at?: string
          updated_at?: string
        }
      }
      documents: {
        Row: {
          id: string
          workspace_id: string
          notion_page_id: string
          title: string
          url?: string
          status: string
          created_time: string
          last_edited_time: string
          created_by: string
          last_edited_by: string
          parent_id?: string
          icon?: string
          cover?: string
          archived: boolean
          in_trash: boolean
          created_at: string
          updated_at: string
        }
      }
      document_chunks: {
        Row: {
          id: string
          document_id: string
          content: string
          chunk_index: number
          tokens: number
          embedding: number[]
          created_at: string
        }
      }
      document_metadata: {
        Row: {
          document_id: string
          metadata_key: string
          metadata_value: string
          created_at: string
        }
      }
      search_analytics: {
        Row: {
          id: string
          user_id: string
          workspace_id?: string
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
      match_documents: {
        Args: {
          query_embedding: number[]
          match_threshold: number
          match_count: number
          workspace_id?: string
        }
        Returns: {
          id: string
          document_id: string
          content: string
          similarity: number
        }[]
      }
    }
    Enums: {
      [_ in never]: never
    }
  }
}