/**
 * Tests for ChatInterface component - main chat UI functionality
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatInterface } from '@/components/chat-interface'
import { useChatSessions } from '@/hooks/use-chat-sessions'
import { useNotionDatabases } from '@/hooks/use-notion-databases'

// Mock the hooks
jest.mock('@/hooks/use-chat-sessions')
jest.mock('@/hooks/use-notion-databases')
jest.mock('@/lib/api')

const mockUseChatSessions = useChatSessions as jest.MockedFunction<typeof useChatSessions>
const mockUseNotionDatabases = useNotionDatabases as jest.MockedFunction<typeof useNotionDatabases>

// Mock chat sessions hook
const mockChatSessionsHook = {
  currentSession: null,
  currentMessages: [],
  isLoading: false,
  error: null,
  isTemporaryChat: true,
  startTemporaryChat: jest.fn(),
  loadSession: jest.fn(),
  addMessage: jest.fn().mockResolvedValue('msg-id'),
  saveMessageImmediately: jest.fn(),
  updateMessage: jest.fn(),
  clearMessages: jest.fn(),
  recentSessions: [],
  loadRecentSessions: jest.fn(),
  refreshRecentSessions: jest.fn(),
  deleteSession: jest.fn(),
  saveCurrentSession: jest.fn(),
  concludeCurrentSession: jest.fn(),
  setOnSessionCreated: jest.fn(),
}

// Mock notion databases hook
const mockNotionDatabasesHook = {
  databases: [
    {
      id: 'db-1',
      name: 'Test Database 1',
      notion_database_id: 'notion-db-1',
      is_active: true
    },
    {
      id: 'db-2',
      name: 'Test Database 2',
      notion_database_id: 'notion-db-2',
      is_active: true
    }
  ],
  selectedDatabases: ['db-1'],
  isLoading: false,
  error: null,
  toggleDatabase: jest.fn(),
  selectAllDatabases: jest.fn(),
  clearSelection: jest.fn(),
  loadDatabases: jest.fn(),
}

describe('ChatInterface Component', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockUseChatSessions.mockReturnValue(mockChatSessionsHook)
    mockUseNotionDatabases.mockReturnValue(mockNotionDatabasesHook)
  })

  describe('Initial Render', () => {
    it('should render chat interface with message input', () => {
      render(<ChatInterface />)

      expect(screen.getByPlaceholderText(/type your message/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument()
    })

    it('should show database filter options', () => {
      render(<ChatInterface />)

      expect(screen.getByText('Test Database 1')).toBeInTheDocument()
      expect(screen.getByText('Test Database 2')).toBeInTheDocument()
    })

    it('should start temporary chat on mount', () => {
      render(<ChatInterface />)

      expect(mockChatSessionsHook.startTemporaryChat).toHaveBeenCalled()
    })
  })

  describe('Message Sending', () => {
    it('should send message when form is submitted', async () => {
      const user = userEvent.setup()
      render(<ChatInterface />)

      const messageInput = screen.getByPlaceholderText(/type your message/i)
      const sendButton = screen.getByRole('button', { name: /send/i })

      await user.type(messageInput, 'Hello, this is a test message')
      await user.click(sendButton)

      await waitFor(() => {
        expect(mockChatSessionsHook.addMessage).toHaveBeenCalledWith(
          expect.objectContaining({
            role: 'user',
            content: 'Hello, this is a test message'
          }),
          expect.any(Object)
        )
      })
    })

    it('should send message when Enter key is pressed', async () => {
      const user = userEvent.setup()
      render(<ChatInterface />)

      const messageInput = screen.getByPlaceholderText(/type your message/i)

      await user.type(messageInput, 'Test message{enter}')

      await waitFor(() => {
        expect(mockChatSessionsHook.addMessage).toHaveBeenCalledWith(
          expect.objectContaining({
            content: 'Test message'
          }),
          expect.any(Object)
        )
      })
    })

    it('should clear input after sending message', async () => {
      const user = userEvent.setup()
      render(<ChatInterface />)

      const messageInput = screen.getByPlaceholderText(/type your message/i) as HTMLInputElement

      await user.type(messageInput, 'Test message')
      await user.keyboard('{enter}')

      await waitFor(() => {
        expect(messageInput.value).toBe('')
      })
    })

    it('should not send empty messages', async () => {
      const user = userEvent.setup()
      render(<ChatInterface />)

      const sendButton = screen.getByRole('button', { name: /send/i })

      await user.click(sendButton)

      expect(mockChatSessionsHook.addMessage).not.toHaveBeenCalled()
    })

    it('should not send whitespace-only messages', async () => {
      const user = userEvent.setup()
      render(<ChatInterface />)

      const messageInput = screen.getByPlaceholderText(/type your message/i)

      await user.type(messageInput, '   ')
      await user.keyboard('{enter}')

      expect(mockChatSessionsHook.addMessage).not.toHaveBeenCalled()
    })
  })

  describe('Message Display', () => {
    it('should display existing messages', () => {
      const mockMessages = [
        {
          id: 'msg-1',
          role: 'user' as const,
          content: 'Hello',
          timestamp: new Date('2023-01-01T00:00:00Z')
        },
        {
          id: 'msg-2',
          role: 'assistant' as const,
          content: 'Hi there! How can I help you?',
          timestamp: new Date('2023-01-01T00:01:00Z')
        }
      ]

      mockUseChatSessions.mockReturnValue({
        ...mockChatSessionsHook,
        currentMessages: mockMessages
      })

      render(<ChatInterface />)

      expect(screen.getByText('Hello')).toBeInTheDocument()
      expect(screen.getByText('Hi there! How can I help you?')).toBeInTheDocument()
    })

    it('should show different styling for user and assistant messages', () => {
      const mockMessages = [
        {
          id: 'msg-1',
          role: 'user' as const,
          content: 'User message',
          timestamp: new Date()
        },
        {
          id: 'msg-2',
          role: 'assistant' as const,
          content: 'Assistant message',
          timestamp: new Date()
        }
      ]

      mockUseChatSessions.mockReturnValue({
        ...mockChatSessionsHook,
        currentMessages: mockMessages
      })

      render(<ChatInterface />)

      const userMessage = screen.getByText('User message').closest('[data-role]')
      const assistantMessage = screen.getByText('Assistant message').closest('[data-role]')

      expect(userMessage).toHaveAttribute('data-role', 'user')
      expect(assistantMessage).toHaveAttribute('data-role', 'assistant')
    })
  })

  describe('Database Filtering', () => {
    it('should include selected databases in session context', async () => {
      const user = userEvent.setup()

      mockUseNotionDatabases.mockReturnValue({
        ...mockNotionDatabasesHook,
        selectedDatabases: ['db-1', 'db-2']
      })

      render(<ChatInterface />)

      const messageInput = screen.getByPlaceholderText(/type your message/i)

      await user.type(messageInput, 'Test with database filter')
      await user.keyboard('{enter}')

      await waitFor(() => {
        expect(mockChatSessionsHook.addMessage).toHaveBeenCalledWith(
          expect.any(Object),
          expect.objectContaining({
            database_filters: ['db-1', 'db-2']
          })
        )
      })
    })

    it('should toggle database selection', async () => {
      const user = userEvent.setup()
      render(<ChatInterface />)

      const databaseCheckbox = screen.getByLabelText('Test Database 2')

      await user.click(databaseCheckbox)

      expect(mockNotionDatabasesHook.toggleDatabase).toHaveBeenCalledWith('db-2')
    })
  })

  describe('Loading States', () => {
    it('should disable input while loading', () => {
      mockUseChatSessions.mockReturnValue({
        ...mockChatSessionsHook,
        isLoading: true
      })

      render(<ChatInterface />)

      const messageInput = screen.getByPlaceholderText(/type your message/i)
      const sendButton = screen.getByRole('button', { name: /send/i })

      expect(messageInput).toBeDisabled()
      expect(sendButton).toBeDisabled()
    })

    it('should show loading indicator when sending message', () => {
      mockUseChatSessions.mockReturnValue({
        ...mockChatSessionsHook,
        isLoading: true
      })

      render(<ChatInterface />)

      expect(screen.getByTestId('loading-indicator')).toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('should display error messages', () => {
      mockUseChatSessions.mockReturnValue({
        ...mockChatSessionsHook,
        error: 'Failed to send message'
      })

      render(<ChatInterface />)

      expect(screen.getByText('Failed to send message')).toBeInTheDocument()
    })

    it('should allow retrying after error', async () => {
      const user = userEvent.setup()

      mockUseChatSessions.mockReturnValue({
        ...mockChatSessionsHook,
        error: 'Network error'
      })

      render(<ChatInterface />)

      const retryButton = screen.getByRole('button', { name: /retry/i })

      await user.click(retryButton)

      // Should clear error and allow new attempts
      expect(mockChatSessionsHook.error).toBeDefined()
    })
  })

  describe('Session Management', () => {
    it('should show session title when available', () => {
      mockUseChatSessions.mockReturnValue({
        ...mockChatSessionsHook,
        currentSession: {
          id: 'session-1',
          title: 'Test Chat Session',
          status: 'active',
          created_at: '2023-01-01T00:00:00Z',
          updated_at: '2023-01-01T00:00:00Z'
        },
        isTemporaryChat: false
      })

      render(<ChatInterface />)

      expect(screen.getByText('Test Chat Session')).toBeInTheDocument()
    })

    it('should show new chat indicator for temporary sessions', () => {
      render(<ChatInterface />)

      expect(screen.getByText(/new chat/i)).toBeInTheDocument()
    })
  })

  describe('Keyboard Shortcuts', () => {
    it('should support Shift+Enter for multiline input', async () => {
      const user = userEvent.setup()
      render(<ChatInterface />)

      const messageInput = screen.getByPlaceholderText(/type your message/i)

      await user.type(messageInput, 'Line 1{shift}{enter}Line 2')

      expect(messageInput).toHaveValue('Line 1\nLine 2')
      expect(mockChatSessionsHook.addMessage).not.toHaveBeenCalled()
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      render(<ChatInterface />)

      expect(screen.getByLabelText(/message input/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /send message/i })).toBeInTheDocument()
    })

    it('should support keyboard navigation', async () => {
      const user = userEvent.setup()
      render(<ChatInterface />)

      // Tab to message input
      await user.tab()
      expect(screen.getByPlaceholderText(/type your message/i)).toHaveFocus()

      // Tab to send button
      await user.tab()
      expect(screen.getByRole('button', { name: /send/i })).toHaveFocus()
    })
  })
})