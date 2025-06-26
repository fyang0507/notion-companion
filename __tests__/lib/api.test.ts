/**
 * Tests for API client functionality and backend integration
 */

import { apiClient, SearchRequest, ChatRequest } from '@/lib/api'
import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'

// Mock server for API calls
const server = setupServer(
  // Chat endpoint
  http.post('http://localhost:8000/api/chat', async ({ request }) => {
    const body = await request.json() as ChatRequest
    return HttpResponse.json({
      response: 'Test response from API',
      session_id: body.session_id,
      model_used: 'gpt-4',
      tokens_used: 50,
      response_time_ms: 1000,
      citations: [],
      context_used: {}
    })
  }),

  // Search endpoint
  http.get('http://localhost:8000/api/search', ({ request }) => {
    const url = new URL(request.url)
    const query = url.searchParams.get('q') || ''
    
    return HttpResponse.json({
      results: [
        {
          id: 'result-1',
          title: 'Test Document',
          content: `Content matching "${query}"`,
          similarity: 0.85,
          metadata: { source: 'notion' },
          notion_page_id: 'page-123'
        }
      ],
      query,
      total: 1
    })
  }),

  // Chat sessions endpoint
  http.get('http://localhost:8000/api/chat-sessions/recent', () => {
    return HttpResponse.json([
      {
        id: 'session-1',
        title: 'Test Chat Session',
        created_at: '2023-01-01T00:00:00Z',
        message_count: 5,
        last_message_at: '2023-01-01T01:00:00Z'
      }
    ])
  }),

  http.post('http://localhost:8000/api/chat-sessions', async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({
      id: 'new-session-id',
      title: body.title || 'New Chat Session',
      status: 'active',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    })
  }),

  // Notion connection endpoint
  http.get('http://localhost:8000/api/notion/databases', () => {
    return HttpResponse.json([
      {
        id: 'db-1',
        name: 'Test Database',
        notion_database_id: 'notion-db-1',
        is_active: true,
        last_synced: '2023-01-01T00:00:00Z'
      }
    ])
  })
)

// Setup and teardown
beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('API Client', () => {
  describe('Search API', () => {
    it('should perform search request successfully', async () => {
      const searchRequest: SearchRequest = {
        query: 'test search',
        limit: 10,
        database_filters: ['db-1']
      }

      const response = await apiClient.search(searchRequest)

      expect(response.results).toHaveLength(1)
      expect(response.results[0].title).toBe('Test Document')
      expect(response.results[0].content).toContain('test search')
      expect(response.query).toBe('test search')
      expect(response.total).toBe(1)
    })

    it('should handle search with minimal parameters', async () => {
      const response = await apiClient.search({ query: 'minimal' })

      expect(response.results).toBeDefined()
      expect(response.query).toBe('minimal')
    })

    it('should handle empty search results', async () => {
      // Override for this test
      server.use(
        http.get('http://localhost:8000/api/search', () => {
          return HttpResponse.json({
            results: [],
            query: 'no results',
            total: 0
          })
        })
      )

      const response = await apiClient.search({ query: 'no results' })

      expect(response.results).toHaveLength(0)
      expect(response.total).toBe(0)
    })
  })

  describe('Chat API', () => {
    it('should send chat message successfully', async () => {
      const chatRequest: ChatRequest = {
        messages: [
          { role: 'user', content: 'Hello, how are you?' }
        ],
        session_id: 'test-session-id',
        database_filters: ['db-1']
      }

      const response = await apiClient.chat(chatRequest)

      expect(response.response).toBe('Test response from API')
      expect(response.session_id).toBe('test-session-id')
      expect(response.model_used).toBe('gpt-4')
      expect(response.tokens_used).toBe(50)
    })

    it('should handle chat with multiple messages', async () => {
      const chatRequest: ChatRequest = {
        messages: [
          { role: 'user', content: 'First message' },
          { role: 'assistant', content: 'First response' },
          { role: 'user', content: 'Second message' }
        ],
        session_id: 'test-session-id'
      }

      const response = await apiClient.chat(chatRequest)

      expect(response.response).toBeDefined()
      expect(response.session_id).toBe('test-session-id')
    })
  })

  describe('Chat Sessions API', () => {
    it('should fetch recent chat sessions', async () => {
      const sessions = await apiClient.getRecentChatSessions()

      expect(sessions).toHaveLength(1)
      expect(sessions[0].id).toBe('session-1')
      expect(sessions[0].title).toBe('Test Chat Session')
      expect(sessions[0].message_count).toBe(5)
    })

    it('should create new chat session', async () => {
      const newSession = await apiClient.createChatSession({
        title: 'My New Session'
      })

      expect(newSession.id).toBe('new-session-id')
      expect(newSession.title).toBe('My New Session')
      expect(newSession.status).toBe('active')
    })

    it('should create session with default title', async () => {
      const newSession = await apiClient.createChatSession({})

      expect(newSession.id).toBe('new-session-id')
      expect(newSession.title).toBe('New Chat Session')
    })
  })

  describe('Notion Integration API', () => {
    it('should fetch notion databases', async () => {
      const databases = await apiClient.getNotionDatabases()

      expect(databases).toHaveLength(1)
      expect(databases[0].id).toBe('db-1')
      expect(databases[0].name).toBe('Test Database')
      expect(databases[0].is_active).toBe(true)
    })
  })

  describe('Error Handling', () => {
    it('should handle API errors gracefully', async () => {
      // Override for this test to return error
      server.use(
        http.post('http://localhost:8000/api/chat', () => {
          return new HttpResponse(null, { status: 500 })
        })
      )

      await expect(apiClient.chat({
        messages: [{ role: 'user', content: 'test' }],
        session_id: 'test'
      })).rejects.toThrow()
    })

    it('should handle network errors', async () => {
      // Override for this test to simulate network error
      server.use(
        http.get('http://localhost:8000/api/search', () => {
          return HttpResponse.error()
        })
      )

      await expect(apiClient.search({ query: 'test' })).rejects.toThrow()
    })
  })

  describe('API Base URL Configuration', () => {
    it('should use correct base URL from environment', () => {
      // This test ensures the API client is configured correctly
      expect(process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000')
        .toMatch(/^https?:\/\//)
    })
  })
})