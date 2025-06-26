export interface Citation {
  id: string;
  title: string;
  url: string;
  preview: string;
  score: number;
  type: 'document' | 'chunk';
  metadata: Record<string, any>;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'bot';
  content: string;
  timestamp: Date;
  citations?: Citation[];
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

export interface ChatFilter {
  workspaces: string[];
  documentTypes: string[];
  dateRange: {
    from?: Date;
    to?: Date;
  };
  authors: string[];
  tags: string[];
  searchQuery: string;
}