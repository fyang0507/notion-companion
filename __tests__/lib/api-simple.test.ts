import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ApiClient, ChatRequest, SearchRequest } from '@/lib/api'

describe('ApiClient Core Methods - Simple', () => {
  let apiClient: ApiClient
  let mockFetch: ReturnType<typeof vi.fn>

  beforeEach(() => {
    mockFetch = vi.fn()
    global.fetch = mockFetch
    apiClient = new ApiClient('http://localhost:8000')
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('sendChatMessage', () => {
    it('should make POST request to chat endpoint', async () => {
      const mockStream = new ReadableStream()
      const mockResponse = {
        ok: true,
        status: 200,
        statusText: 'OK',
        headers: { get: vi.fn().mockReturnValue('test-request-id') },
        body: mockStream
      }
      mockFetch.mockResolvedValueOnce(mockResponse)

      const chatRequest: ChatRequest = {
        messages: [{ role: 'user', content: 'Hello' }],
        session_id: 'test-session-123'
      }

      const result = await apiClient.sendChatMessage(chatRequest)
      
      expect(result).toBe(mockStream)
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/chat',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'X-Request-ID': expect.any(String)
          }),
          body: JSON.stringify(chatRequest)
        })
      )
    })

    it('should handle API errors', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        statusText: 'Internal Server Error'
      }
      mockFetch.mockResolvedValueOnce(mockResponse)

      const chatRequest: ChatRequest = {
        messages: [{ role: 'user', content: 'Hello' }],
        session_id: 'test-session-123'
      }

      await expect(apiClient.sendChatMessage(chatRequest)).rejects.toThrow()
    })
  })

  describe('createChatSession', () => {
    it('should make POST request to sessions endpoint', async () => {
      const mockSession = {
        id: 'test-session-123',
        title: 'Test Session',
        status: 'active',
        message_count: 0,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        last_message_at: '2024-01-01T00:00:00Z',
        session_context: {}
      }
      
      const mockResponse = {
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue(mockSession),
        headers: { get: vi.fn() }
      }
      mockFetch.mockResolvedValueOnce(mockResponse)

      const sessionData = {
        title: 'New Chat',
        session_context: { test: true }
      }

      const result = await apiClient.createChatSession(sessionData)
      
      expect(result).toEqual(mockSession)
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/chat-sessions/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(sessionData)
        })
      )
    })
  })

  describe('search', () => {
    it('should make POST request to search endpoint', async () => {
      const mockSearchResponse = {
        results: [
          {
            id: 'result-1',
            title: 'Test Document',
            content: 'Test content',
            similarity: 0.85,
            metadata: {},
            notion_page_id: 'page-1'
          }
        ],
        query: 'test query',
        total: 1
      }
      
      const mockResponse = {
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue(mockSearchResponse),
        headers: { get: vi.fn() }
      }
      mockFetch.mockResolvedValueOnce(mockResponse)

      const searchRequest: SearchRequest = {
        query: 'test query',
        limit: 10
      }

      const result = await apiClient.search(searchRequest)
      
      expect(result).toEqual(mockSearchResponse)
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/search',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(searchRequest)
        })
      )
    })
  })

  describe('error handling', () => {
    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'))

      await expect(apiClient.search({ query: 'test' })).rejects.toThrow('Network error')
    })

    it('should include request ID in headers', async () => {
      const mockResponse = {
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue({}),
        headers: { get: vi.fn() }
      }
      mockFetch.mockResolvedValueOnce(mockResponse)

      await apiClient.search({ query: 'test' })

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-Request-ID': expect.any(String)
          })
        })
      )
    })
  })
})