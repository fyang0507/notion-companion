/**
 * Tests for useChatSessions hook - core chat functionality
 */

import { renderHook, act, waitFor } from '@testing-library/react'
import { useChatSessions } from '@/hooks/use-chat-sessions'
import { apiClient } from '@/lib/api'
import { ChatMessage } from '@/types/chat'

// Mock the API client
jest.mock('@/lib/api', () => ({
  apiClient: {
    createChatSession: jest.fn(),
    getRecentChats: jest.fn(),
    getChatSession: jest.fn(),
    addMessageToSession: jest.fn(),
    updateChatSession: jest.fn(),
    deleteChatSession: jest.fn(),
    saveChatSession: jest.fn(),
    concludeChatSession: jest.fn(),
    concludeCurrentAndStartNew: jest.fn(),
    concludeForResume: jest.fn(),
    sendChatMessage: jest.fn(),
    search: jest.fn(),
    processNotionWebhook: jest.fn(),
  }
}))

// Mock logger
jest.mock('@/lib/logger', () => ({
  logger: {
    info: jest.fn(),
    error: jest.fn(),
    warn: jest.fn(),
  }
}))

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>

describe('useChatSessions Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    
    // Default mock implementations
    mockApiClient.createChatSession.mockResolvedValue({
      id: 'new-session-id',
      title: 'New Chat Session',
      status: 'active',
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z',
      message_count: 0,
      last_message_at: '2023-01-01T00:00:00Z',
      session_context: {}
    })

    mockApiClient.getRecentChats.mockResolvedValue([
      {
        id: 'session-1',
        title: 'Recent Session',
        created_at: '2023-01-01T00:00:00Z',
        message_count: 5,
        last_message_at: '2023-01-01T01:00:00Z',
        status: 'active'
      }
    ])

    mockApiClient.addMessageToSession.mockResolvedValue({
      id: 'msg-1',
      session_id: 'session-1',
      role: 'user',
      content: 'Test message',
      created_at: '2023-01-01T00:00:00Z',
      message_order: 1,
      citations: [],
      context_used: {}
    })

    mockApiClient.deleteChatSession.mockResolvedValue({
      message: 'Session deleted successfully'
    })

    mockApiClient.updateChatSession.mockResolvedValue({
      id: 'current-session',
      title: 'Updated Session',
      status: 'concluded',
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z',
      message_count: 1,
      last_message_at: '2023-01-01T00:00:00Z',
      session_context: {}
    })
  })

  describe('Initial State', () => {
    it('should initialize with correct default values', () => {
      const { result } = renderHook(() => useChatSessions())

      expect(result.current.currentSession).toBeNull()
      expect(result.current.currentMessages).toEqual([])
      expect(result.current.isLoading).toBe(false)
      expect(result.current.error).toBeNull()
      expect(result.current.isTemporaryChat).toBe(false)
      expect(result.current.recentSessions).toEqual([])
    })
  })

  describe('Temporary Chat Creation', () => {
    it('should start temporary chat successfully', () => {
      const { result } = renderHook(() => useChatSessions())

      act(() => {
        result.current.startTemporaryChat()
      })

      expect(result.current.isTemporaryChat).toBe(true)
      expect(result.current.currentSession).toBeNull()
      expect(result.current.currentMessages).toEqual([])
    })

    it('should start temporary chat with context', () => {
      const { result } = renderHook(() => useChatSessions())
      const sessionContext = { database_filters: ['db-1'] }

      act(() => {
        result.current.startTemporaryChat(sessionContext)
      })

      expect(result.current.isTemporaryChat).toBe(true)
    })
  })

  describe('Message Management', () => {
    it('should add message to temporary chat and create session', async () => {
      const { result } = renderHook(() => useChatSessions())

      // Start temporary chat
      act(() => {
        result.current.startTemporaryChat()
      })

      const testMessage: ChatMessage = {
        role: 'user',
        content: 'Hello, this is a test message',
        id: 'temp-msg-1',
        timestamp: new Date()
      }

      // Add message (should create session)
      await act(async () => {
        await result.current.addMessage(testMessage)
      })

      await waitFor(() => {
        expect(mockApiClient.createChatSession).toHaveBeenCalledWith({
          title: 'New Chat',
          session_context: {}
        })
        expect(mockApiClient.addMessageToSession).toHaveBeenCalled()
        expect(result.current.isTemporaryChat).toBe(false)
      })
    })

    it('should add message to existing session', async () => {
      const { result } = renderHook(() => useChatSessions())

      // First create a session through the proper flow
      act(() => {
        result.current.startTemporaryChat()
      })

      const initialMessage: ChatMessage = {
        role: 'user',
        content: 'Initial message to create session',
        id: 'msg-1',
        timestamp: new Date()
      }

      // Create the session
      await act(async () => {
        await result.current.addMessage(initialMessage)
      })

      // Now add another message to the existing session
      const testMessage: ChatMessage = {
        role: 'user',
        content: 'Message for existing session',
        id: 'msg-2',
        timestamp: new Date()
      }

      await act(async () => {
        await result.current.addMessage(testMessage)
      })

      await waitFor(() => {
        expect(mockApiClient.addMessageToSession).toHaveBeenCalledWith(
          'new-session-id',
          expect.objectContaining({
            role: 'user',
            content: 'Message for existing session'
          })
        )
      })
    })

    it('should update message locally', async () => {
      const { result } = renderHook(() => useChatSessions())

      // Start temporary chat and add initial message
      act(() => {
        result.current.startTemporaryChat()
      })

      const initialMessage: ChatMessage = {
        role: 'user',
        content: 'Original content',
        id: 'msg-1',
        timestamp: new Date()
      }

      await act(async () => {
        await result.current.addMessage(initialMessage)
      })

      // Update message
      act(() => {
        result.current.updateMessage('msg-1', { content: 'Updated content' })
      })

      await waitFor(() => {
        expect(result.current.currentMessages.find(m => m.id === 'msg-1')?.content).toBe('Updated content')
      })
    })

    it('should clear messages', async () => {
      const { result } = renderHook(() => useChatSessions())

      // Start temporary chat and add messages
      act(() => {
        result.current.startTemporaryChat()
      })

      const message1: ChatMessage = {
        role: 'user',
        content: 'Message 1',
        id: 'msg-1',
        timestamp: new Date()
      }

      await act(async () => {
        await result.current.addMessage(message1)
      })

      // Clear messages
      act(() => {
        result.current.clearMessages()
      })

      expect(result.current.currentMessages).toEqual([])
    })
  })

  describe('Session Loading', () => {
    it('should load recent sessions successfully', async () => {
      const { result } = renderHook(() => useChatSessions())

      await act(async () => {
        await result.current.loadRecentSessions()
      })

      await waitFor(() => {
        expect(mockApiClient.getRecentChats).toHaveBeenCalled()
        expect(result.current.recentSessions).toHaveLength(1)
        expect(result.current.recentSessions[0].title).toBe('Recent Session')
      })
    })

    it('should load specific session', async () => {
      const { result } = renderHook(() => useChatSessions())

      mockApiClient.getChatSession.mockResolvedValue({
        session: {
          id: 'session-123',
          title: 'Loaded Session',
          status: 'active',
          created_at: '2023-01-01T00:00:00Z',
          updated_at: '2023-01-01T00:00:00Z',
          message_count: 1,
          last_message_at: '2023-01-01T00:00:00Z',
          session_context: {}
        },
        messages: [
          {
            id: 'msg-1',
            session_id: 'session-123',
            role: 'user',
            content: 'Previous message',
            created_at: '2023-01-01T00:00:00Z',
            message_order: 1,
            citations: [],
            context_used: {}
          }
        ]
      })

      await act(async () => {
        await result.current.loadSession('session-123')
      })

      await waitFor(() => {
        expect(mockApiClient.getChatSession).toHaveBeenCalledWith('session-123')
        expect(result.current.currentSession?.id).toBe('session-123')
        expect(result.current.currentMessages).toHaveLength(1)
        expect(result.current.isTemporaryChat).toBe(false)
      })
    })
  })

  describe('Session Management', () => {
    it('should delete session successfully', async () => {
      const { result } = renderHook(() => useChatSessions())

      await act(async () => {
        await result.current.deleteSession('session-to-delete')
      })

      await waitFor(() => {
        expect(mockApiClient.deleteChatSession).toHaveBeenCalledWith('session-to-delete', true)
      })
    })

    it('should conclude current session', async () => {
      const { result } = renderHook(() => useChatSessions())

      // First create a session through the proper flow
      act(() => {
        result.current.startTemporaryChat()
      })

      const initialMessage: ChatMessage = {
        role: 'user',
        content: 'Initial message to create session',
        id: 'msg-1',
        timestamp: new Date()
      }

      // Create the session
      await act(async () => {
        await result.current.addMessage(initialMessage)
      })

      mockApiClient.concludeChatSession.mockResolvedValue({
        message: 'Session concluded successfully',
        title: 'Generated Session Title',
        summary: 'Generated session summary'
      })

      await act(async () => {
        await result.current.concludeCurrentSession('Session completed')
      })

      await waitFor(() => {
        expect(mockApiClient.concludeChatSession).toHaveBeenCalledWith(
          'new-session-id',
          'Session completed'
        )
      })
    })
  })

  describe('Error Handling', () => {
    it('should handle API errors gracefully', async () => {
      const { result } = renderHook(() => useChatSessions())

      mockApiClient.getRecentChats.mockRejectedValue(new Error('API Error'))

      await act(async () => {
        await result.current.loadRecentSessions()
      })

      // The hook catches errors but doesn't set an error state for loadRecentSessions
      // Instead it just logs and sets empty array
      await waitFor(() => {
        expect(result.current.recentSessions).toEqual([])
      })
    })

    it('should handle session creation errors', async () => {
      const { result } = renderHook(() => useChatSessions())

      mockApiClient.createChatSession.mockRejectedValue(new Error('Session creation failed'))

      act(() => {
        result.current.startTemporaryChat()
      })

      const testMessage: ChatMessage = {
        role: 'user',
        content: 'Test message',
        id: 'msg-1',
        timestamp: new Date()
      }

      await act(async () => {
        await result.current.addMessage(testMessage)
      })

      // The hook catches session creation errors but continues with temporary chat
      // So the message should still be added to currentMessages
      await waitFor(() => {
        expect(result.current.currentMessages).toHaveLength(1)
        expect(result.current.isTemporaryChat).toBe(true)
      })
    })
  })

  describe('Callback Management', () => {
    it('should set and trigger session created callback', async () => {
      const { result } = renderHook(() => useChatSessions())
      const onSessionCreated = jest.fn()

      act(() => {
        result.current.setOnSessionCreated(onSessionCreated)
      })

      act(() => {
        result.current.startTemporaryChat()
      })

      const testMessage: ChatMessage = {
        role: 'user',
        content: 'Test message',
        id: 'msg-1',
        timestamp: new Date()
      }

      await act(async () => {
        await result.current.addMessage(testMessage)
      })

      await waitFor(() => {
        expect(onSessionCreated).toHaveBeenCalledWith('new-session-id')
      })
    })
  })
})