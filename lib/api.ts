const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  workspaceId: string;
  userId: string;
}

export interface SearchRequest {
  query: string;
  workspaceId: string;
  limit?: number;
}

export interface SearchResult {
  id: string;
  title: string;
  content: string;
  similarity: number;
  metadata: Record<string, any>;
  notion_page_id: string;
}

export interface SearchResponse {
  results: SearchResult[];
  query: string;
  total: number;
}

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async sendChatMessage(request: ChatRequest): Promise<ReadableStream> {
    const response = await fetch(`${this.baseUrl}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Chat API error: ${response.statusText}`);
    }

    if (!response.body) {
      throw new Error('No response body received');
    }

    return response.body;
  }

  async search(request: SearchRequest): Promise<SearchResponse> {
    const response = await fetch(`${this.baseUrl}/api/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Search API error: ${response.statusText}`);
    }

    return response.json();
  }

  async processNotionWebhook(payload: any): Promise<{ success: boolean }> {
    const response = await fetch(`${this.baseUrl}/api/notion/webhook`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Webhook API error: ${response.statusText}`);
    }

    return response.json();
  }
}

export const apiClient = new ApiClient();