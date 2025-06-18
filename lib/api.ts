import { logger } from './logger';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  // Single-user, single-workspace app - no IDs needed
}

export interface SearchRequest {
  query: string;
  limit?: number;
  // Single-user, single-workspace app - no workspace ID needed
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
}

export const apiClient = new ApiClient();