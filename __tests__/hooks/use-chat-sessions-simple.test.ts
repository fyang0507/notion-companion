import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'

// Mock all external dependencies
vi.mock('@/lib/api', () => ({
  apiClient: {
    createChatSession: vi.fn(),
    addMessageToSession: vi.fn(),
    getRecentChats: vi.fn(),
    getChatSession: vi.fn(),
    concludeForResume: vi.fn()
  }
}))

vi.mock('@/lib/logger', () => ({
  logger: {
    generateAndSetRequestId: vi.fn(() => 'test-request-id'),
    info: vi.fn(),
    error: vi.fn(),
    logApiRequest: vi.fn(),
  }
}))

// Now import after mocks are set up
import { useChatSessions } from '@/hooks/use-chat-sessions'
import { apiClient } from '@/lib/api'

const mockApiClient = apiClient as any

describe('useChatSessions - Session Creation Timing', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    // Setup default mock responses
    mockApiClient.createChatSession.mockResolvedValue({
      id: 'test-session-123',
      title: 'New Chat',
      status: 'active',
      message_count: 0,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      last_message_at: '2024-01-01T00:00:00Z',
      session_context: {}
    })
    
    mockApiClient.getRecentChats.mockResolvedValue([])
  })

  describe('temporary chat to permanent session conversion', () => {
    it('should create session on first user message, not second', async () => {
      const { result } = renderHook(() => useChatSessions())

      // Start temporary chat
      act(() => {
        result.current.startTemporaryChat()
      })

      expect(result.current.isTemporaryChat).toBe(true)
      expect(result.current.currentSession).toBeNull()

      // Add first user message - should create session
      let sessionId: string | null = null
      await act(async () => {
        sessionId = await result.current.addMessage({
          id: 'msg-1',
          role: 'user',
          content: 'First message',
          timestamp: new Date()
        })
      })

      // Verify session was created on first message
      expect(mockApiClient.createChatSession).toHaveBeenCalledTimes(1)
      expect(mockApiClient.createChatSession).toHaveBeenCalledWith({
        title: 'New Chat',
        session_context: {}
      })
      expect(sessionId).toBe('test-session-123')
      expect(result.current.isTemporaryChat).toBe(false)
      expect(result.current.currentSession?.id).toBe('test-session-123')

      // Add second user message - should NOT create another session
      await act(async () => {
        await result.current.addMessage({
          id: 'msg-2',
          role: 'user',
          content: 'Second message',
          timestamp: new Date()
        })
      })

      // Verify session creation was only called once
      expect(mockApiClient.createChatSession).toHaveBeenCalledTimes(1)
      expect(result.current.currentSession?.id).toBe('test-session-123')
    })

    it('should handle session creation with custom context', async () => {
      const { result } = renderHook(() => useChatSessions())

      const customContext = { databaseFilters: ['db-1', 'db-2'] }

      // Start temporary chat with context
      act(() => {
        result.current.startTemporaryChat(customContext)
      })

      // Add first user message
      await act(async () => {
        await result.current.addMessage({
          id: 'msg-1',
          role: 'user',
          content: 'First message',
          timestamp: new Date()
        })
      })

      // Verify session was created with custom context
      expect(mockApiClient.createChatSession).toHaveBeenCalledWith({
        title: 'New Chat',
        session_context: customContext
      })
    })

    it('should handle session creation failure gracefully', async () => {
      const { result } = renderHook(() => useChatSessions())

      // Mock session creation failure
      mockApiClient.createChatSession.mockRejectedValueOnce(new Error('Session creation failed'))

      act(() => {
        result.current.startTemporaryChat()
      })

      // Add first user message - session creation should fail
      await act(async () => {
        const sessionId = await result.current.addMessage({
          id: 'msg-1',
          role: 'user',
          content: 'First message',
          timestamp: new Date()
        })
        
        // Should return null when session creation fails
        expect(sessionId).toBeNull()
      })

      // Should remain in temporary chat mode when session creation fails
      expect(result.current.isTemporaryChat).toBe(true)
      expect(result.current.currentSession).toBeNull()
      
      // But message should still be added to UI
      expect(result.current.currentMessages).toHaveLength(1)
      expect(result.current.currentMessages[0].content).toBe('First message')
    })

    it('should not create session for assistant messages in temporary mode', async () => {
      const { result } = renderHook(() => useChatSessions())

      act(() => {
        result.current.startTemporaryChat()
      })

      // Add assistant message - should NOT create session
      await act(async () => {
        const sessionId = await result.current.addMessage({
          id: 'msg-1',
          role: 'assistant',
          content: 'Assistant response',
          timestamp: new Date()
        })
        
        expect(sessionId).toBeNull()
      })

      // Should remain in temporary chat mode
      expect(mockApiClient.createChatSession).not.toHaveBeenCalled()
      expect(result.current.isTemporaryChat).toBe(true)
      expect(result.current.currentSession).toBeNull()
    })

    it('should clear temporary chat state when starting new temporary chat', async () => {
      const { result } = renderHook(() => useChatSessions())

      // Set up some existing state
      act(() => {
        result.current.startTemporaryChat()
      })

      await act(async () => {
        await result.current.addMessage({
          id: 'msg-1',
          role: 'user',
          content: 'First message',
          timestamp: new Date()
        })
      })

      expect(result.current.currentSession).not.toBeNull()
      expect(result.current.currentMessages).toHaveLength(1)

      // Start new temporary chat
      act(() => {
        result.current.startTemporaryChat()
      })

      // Should clear previous state
      expect(result.current.currentSession).toBeNull()
      expect(result.current.currentMessages).toHaveLength(0)
      expect(result.current.isTemporaryChat).toBe(true)
    })
  })
})