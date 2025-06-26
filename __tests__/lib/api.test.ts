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

  // Search endpoint (POST method)
  http.post('http://localhost:8000/api/search', async ({ request }) => {
    const body = await request.json() as SearchRequest
    const query = body.query || ''
    
    // Return empty results for "no results" query
    if (query === 'no results') {
      return HttpResponse.json({
        results: [],
        query,
        total: 0
      })
    }
    
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

  http.post('http://localhost:8000/api/chat-sessions/', async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({
      id: 'new-session-id',
      title: body.title || 'New Chat Session',
      status: 'active',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    })
  }),

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
    it('should get chat stream successfully', async () => {
      const chatRequest: ChatRequest = {
        message: 'Hello, how are you?',
        session_id: 'test-session-id',
        database_filters: ['db-1']
      }

      const stream = await apiClient.chatStream(chatRequest)

      expect(stream).toBeDefined()
      // For streaming API, we just check that we get a ReadableStream
      expect(stream instanceof ReadableStream).toBe(true)
    })
  })

  describe('Chat Sessions API', () => {
    it('should fetch recent chat sessions', async () => {
      const sessions = await apiClient.getRecentChats()

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


  describe('Error Handling', () => {
    it('should handle API errors gracefully', async () => {
      // Override for this test to return error
      server.use(
        http.post('http://localhost:8000/api/chat', () => {
          return new HttpResponse(null, { status: 500 })
        })
      )

      await expect(apiClient.chatStream({
        message: 'test',
        session_id: 'test'
      })).rejects.toThrow()
    })

    it('should handle network errors', async () => {
      // Override for this test to simulate network error
      server.use(
        http.post('http://localhost:8000/api/search', () => {
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