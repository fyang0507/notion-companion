import { logger } from './logger';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  database_filters?: string[];  // Filter by specific Notion databases
  session_id: string;  // Required session ID for conversation history
}

export interface SearchRequest {
  query: string;
  limit?: number;
  database_filters?: string[];  // Filter by specific Notion databases
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

export interface ChatSessionMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  model_used?: string;
  tokens_used?: number;
  response_time_ms?: number;
  citations: any[];
  context_used: Record<string, any>;
  created_at: string;
  message_order: number;
}

export interface ChatSession {
  id: string;
  title: string;
  summary?: string;
  status: string;
  message_count: number;
  created_at: string;
  updated_at: string;
  last_message_at: string;
  session_context: Record<string, any>;
}

export interface ChatSessionWithMessages {
  session: ChatSession;
  messages: ChatSessionMessage[];
}

export interface RecentChatSummary {
  id: string;
  title: string;
  summary?: string;
  status: string; // 'active', 'concluded', 'deleted'
  message_count: number;
  last_message_at: string;
  created_at: string;
  last_message_preview?: string;
}

export interface ChatSessionCreate {
  title?: string;
  summary?: string;
  session_context?: Record<string, any>;
}

export interface ChatSessionUpdate {
  title?: string;
  summary?: string;
  status?: string;
}

export interface ChatMessageCreate {
  role: 'user' | 'assistant';
  content: string;
  model_used?: string;
  tokens_used?: number;
  response_time_ms?: number;
  citations?: any[];
  context_used?: Record<string, any>;
}

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async makeRequest<T>(
    method: string,
    endpoint: string,
    body?: any,
    options: RequestInit = {}
  ): Promise<{ data: T; response: Response; duration: number }> {
    const startTime = performance.now();
    const requestId = logger.generateAndSetRequestId();
    const url = `${this.baseUrl}${endpoint}`;

    logger.info(`API request started: ${method} ${endpoint}`, 'api', {
      method,
      url,
      requestId,
      bodySize: body ? JSON.stringify(body).length : 0,
    });

    try {
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'X-Request-ID': requestId,
          ...options.headers,
        },
        body: body ? JSON.stringify(body) : undefined,
        ...options,
      });

      const duration = performance.now() - startTime;
      const backendRequestId = response.headers.get('X-Request-ID');

      if (backendRequestId && backendRequestId !== requestId) {
        logger.info('Backend assigned different request ID', 'api', {
          frontend_request_id: requestId,
          backend_request_id: backendRequestId,
        });
      }

      if (!response.ok) {
        logger.error(`API request failed: ${method} ${endpoint}`, 'api', {
          method,
          url,
          status: response.status,
          statusText: response.statusText,
          duration,
        });
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      
      logger.logApiRequest(method, endpoint, response.status, duration, {
        requestId,
        backendRequestId,
        responseSize: JSON.stringify(data).length,
      });

      return { data, response, duration };
    } catch (error) {
      const duration = performance.now() - startTime;
      logger.error(`API request error: ${method} ${endpoint}`, 'api', {
        method,
        url,
        duration,
        error: error instanceof Error ? error.message : String(error),
      }, error instanceof Error ? error : undefined);
      throw error;
    }
  }

  async sendChatMessage(request: ChatRequest): Promise<ReadableStream> {
    const startTime = performance.now();
    const requestId = logger.generateAndSetRequestId();
    const url = `${this.baseUrl}/api/chat`;

    logger.info('Chat stream request started', 'api', {
      messageCount: request.messages.length,
      requestId,
    });

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Request-ID': requestId,
        },
        body: JSON.stringify(request),
      });

      const duration = performance.now() - startTime;
      const backendRequestId = response.headers.get('X-Request-ID');

      if (!response.ok) {
        logger.error('Chat stream request failed', 'api', {
          status: response.status,
          statusText: response.statusText,
          duration,
        });
        throw new Error(`Chat API error: ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error('No response body received');
      }

      logger.info('Chat stream request successful', 'api', {
        requestId,
        backendRequestId,
        duration,
      });

      return response.body;
    } catch (error) {
      const duration = performance.now() - startTime;
      logger.error('Chat stream request error', 'api', {
        duration,
        error: error instanceof Error ? error.message : String(error),
      }, error instanceof Error ? error : undefined);
      throw error;
    }
  }

  async search(request: SearchRequest): Promise<SearchResponse> {
    const { data } = await this.makeRequest<SearchResponse>('POST', '/api/search', request);
    return data;
  }

  async processNotionWebhook(payload: any): Promise<{ success: boolean }> {
    const { data } = await this.makeRequest<{ success: boolean }>('POST', '/api/notion/webhook', payload);
    return data;
  }

  // Chat Session Management
  async getRecentChats(limit: number = 20): Promise<RecentChatSummary[]> {
    const { data } = await this.makeRequest<RecentChatSummary[]>('GET', `/api/chat-sessions/recent?limit=${limit}`);
    return data;
  }

  async createChatSession(sessionData: ChatSessionCreate): Promise<ChatSession> {
    const { data } = await this.makeRequest<ChatSession>('POST', '/api/chat-sessions/', sessionData);
    return data;
  }

  async getChatSession(sessionId: string): Promise<ChatSessionWithMessages> {
    const { data } = await this.makeRequest<ChatSessionWithMessages>('GET', `/api/chat-sessions/${sessionId}`);
    return data;
  }

  async updateChatSession(sessionId: string, updates: ChatSessionUpdate): Promise<ChatSession> {
    const { data } = await this.makeRequest<ChatSession>('PUT', `/api/chat-sessions/${sessionId}`, updates);
    return data;
  }

  async deleteChatSession(sessionId: string, softDelete: boolean = true): Promise<{ message: string }> {
    const { data } = await this.makeRequest<{ message: string }>('DELETE', `/api/chat-sessions/${sessionId}?soft_delete=${softDelete}`);
    return data;
  }

  async addMessageToSession(sessionId: string, message: ChatMessageCreate): Promise<ChatSessionMessage> {
    const { data } = await this.makeRequest<ChatSessionMessage>('POST', `/api/chat-sessions/${sessionId}/messages`, message);
    return data;
  }



  async concludeChatSession(sessionId: string, reason: string = 'manual'): Promise<{ message: string; title: string; summary: string }> {
    const { data } = await this.makeRequest<{ message: string; title: string; summary: string }>('POST', `/api/chat-sessions/${sessionId}/conclude`, { reason });
    return data;
  }



  async concludeForResume(currentSessionId: string, resumingSessionId: string): Promise<{ message: string; title: string; summary: string }> {
    const { data } = await this.makeRequest<{ message: string; title: string; summary: string }>('POST', `/api/chat-sessions/${currentSessionId}/conclude-for-resume`, { 
      resuming_session_id: resumingSessionId 
    });
    return data;
  }

  async concludeForNewChat(currentSessionId: string): Promise<{ message: string; title?: string; summary?: string }> {
    const { data } = await this.makeRequest<{ message: string; title?: string; summary?: string }>('POST', `/api/chat-sessions/${currentSessionId}/conclude-for-new-chat`);
    return data;
  }
}

export const apiClient = new ApiClient();