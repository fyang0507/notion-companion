export interface Citation {
  id: string;
  title: string;
  url?: string;
  snippet?: string;
  metadata?: {
    database_name?: string;
    author?: string;
    created_date?: string;
    page_type?: string;
  };
}

export interface ChatMessage {
  id: string;
  session_id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: string;
  metadata?: {
    model?: string;
    citations?: Citation[];
    thinking_time?: number;
    token_usage?: {
      prompt_tokens?: number;
      completion_tokens?: number;
      total_tokens?: number;
    };
  };
}

export interface Workspace {
  id: string;
  name: string;
  type: 'page' | 'database' | 'workspace';
  documentCount: number;
  lastSync: string;
  status: 'active' | 'syncing' | 'error';
}

export interface TokenUsage {
  currentTokens: number;
  monthlyLimit: number;
  costThisMonth: number;
  requestsToday: number;
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  status: 'active' | 'archived';
  metadata?: {
    model?: string;
    total_messages?: number;
    last_activity?: string;
  };
}

export interface ChatFilter {
  workspaces: string[];
  dateRange: {
    from?: Date;
    to?: Date;
  };
  searchQuery: string;
  metadataFilters: Record<string, string[]>;
}

export interface DatabaseFieldDefinition {
  field_name: string;
  field_type: 'text' | 'date' | 'status' | 'select' | 'multi_select' | 'number' | 'checkbox';
  notion_field: string;
  description: string;
  is_filterable: boolean;
  sample_values?: string[] | null;
}

export interface FieldFilterOptions {
  field_name: string;
  unique_values: (string | number)[];
  value_counts: Record<string, number>;
  field_definition: DatabaseFieldDefinition;
}

export interface UsageStats {
  searchesToday: number;
  requestsToday: number;
}