import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// Database schema types
export interface DatabaseSchema {
  public: {
    Tables: {
      users: {
        Row: {
          id: string;
          email: string;
          created_at: string;
          updated_at: string;
          notion_access_token?: string;
          monthly_token_limit: number;
          current_token_usage: number;
        };
        Insert: {
          id?: string;
          email: string;
          notion_access_token?: string;
          monthly_token_limit?: number;
          current_token_usage?: number;
        };
        Update: {
          email?: string;
          notion_access_token?: string;
          monthly_token_limit?: number;
          current_token_usage?: number;
        };
      };
      workspaces: {
        Row: {
          id: string;
          user_id: string;
          notion_workspace_id: string;
          name: string;
          type: string;
          document_count: number;
          last_sync: string;
          status: string;
          created_at: string;
        };
        Insert: {
          id?: string;
          user_id: string;
          notion_workspace_id: string;
          name: string;
          type: string;
          document_count?: number;
          last_sync?: string;
          status?: string;
        };
        Update: {
          name?: string;
          document_count?: number;
          last_sync?: string;
          status?: string;
        };
      };
      documents: {
        Row: {
          id: string;
          workspace_id: string;
          notion_page_id: string;
          title: string;
          content: string;
          embedding: number[];
          metadata: Record<string, any>;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          workspace_id: string;
          notion_page_id: string;
          title: string;
          content: string;
          embedding: number[];
          metadata?: Record<string, any>;
        };
        Update: {
          title?: string;
          content?: string;
          embedding?: number[];
          metadata?: Record<string, any>;
        };
      };
      chat_sessions: {
        Row: {
          id: string;
          user_id: string;
          workspace_id: string;
          title: string;
          messages: Record<string, any>[];
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          user_id: string;
          workspace_id: string;
          title: string;
          messages?: Record<string, any>[];
        };
        Update: {
          title?: string;
          messages?: Record<string, any>[];
        };
      };
      api_usage: {
        Row: {
          id: string;
          user_id: string;
          endpoint: string;
          tokens_used: number;
          cost: number;
          timestamp: string;
        };
        Insert: {
          id?: string;
          user_id: string;
          endpoint: string;
          tokens_used: number;
          cost: number;
        };
        Update: never;
      };
    };
  };
}