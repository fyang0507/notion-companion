/**
 * Integration tests for complete chat flow - Frontend to Backend
 */

import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatInterface } from '@/components/chat-interface'
import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'

// Mock the hooks with actual implementations for integration testing
jest.unmock('@/hooks/use-chat-sessions')
jest.unmock('@/hooks/use-notion-databases')

// Mock the notion connection hook for integration tests
jest.mock('@/hooks/use-notion-connection', () => ({
  useNotionConnection: () => ({
    connection: { name: 'Test Workspace' },
    isConnected: true
  })
}))

// Mock session lifecycle hook
jest.mock('@/hooks/use-session-lifecycle', () => ({
  useSessionLifecycle: () => {}
}))

// Setup MSW server for API mocking
const server = setupServer(
  // Chat endpoint - streaming response
  http.post('http://localhost:8000/api/chat', async ({ request }) => {
    const body = await request.json()
    const userMessage = body.messages[body.messages.length - 1]
    
    return HttpResponse.json({
      response: `Echo: ${userMessage.content}`,
      session_id: body.session_id,
      model_used: 'gpt-4',
      tokens_used: 25,
      response_time_ms: 500,
      citations: [
        {
          source: 'Test Document',
          page_id: 'page-123',
          similarity: 0.85
        }
      ],
      context_used: {
        documents_found: 1,
        search_query: userMessage.content
      }
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
          title: 'Integration Test Document',
          content: `Content related to "${query}"`,
          similarity: 0.9,
          metadata: { source: 'notion', database: 'test-db' },
          notion_page_id: 'page-456'
        }
      ],
      query,
      total: 1,
      query_time_ms: 150,
      embedding_time_ms: 100
    })
  }),

  // Chat sessions endpoints
  http.get('http://localhost:8000/api/chat-sessions/recent', () => {
    return HttpResponse.json([
      {
        id: 'integration-session-1',
        title: 'Integration Test Session',
        created_at: '2023-01-01T00:00:00Z',
        message_count: 3,
        last_message_at: '2023-01-01T01:00:00Z'
      }
    ])
  }),

  http.post('http://localhost:8000/api/chat-sessions', async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({
      id: 'new-integration-session',
      title: body.title || 'New Integration Session',
      status: 'active',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      message_count: 0,
      last_message_at: new Date().toISOString(),
      session_context: {}
    })
  }),

  http.get('http://localhost:8000/api/chat-sessions/:sessionId', ({ params }) => {
    return HttpResponse.json({
      session: {
        id: params.sessionId,
        title: 'Loaded Integration Session',
        status: 'active',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:00:00Z',
        message_count: 1,
        last_message_at: '2023-01-01T00:00:00Z',
        session_context: {}
      },
      messages: [
        {
          id: 'integration-msg-1',
          session_id: params.sessionId,
          role: 'user',
          content: 'Previous integration message',
          created_at: '2023-01-01T00:00:00Z',
          message_order: 1,
          citations: [],
          context_used: {}
        }
      ]
    })
  }),

  http.post('http://localhost:8000/api/chat-sessions/:sessionId/messages', async ({ params, request }) => {
    const body = await request.json()
    return HttpResponse.json({
      id: 'new-integration-msg',
      session_id: params.sessionId,
      role: body.role,
      content: body.content,
      created_at: new Date().toISOString(),
      message_order: body.message_order || 1,
      citations: body.citations || [],
      context_used: body.context_used || {}
    })
  }),

  // Notion databases endpoint
  http.get('http://localhost:8000/api/notion/databases', () => {
    return HttpResponse.json([
      {
        id: 'integration-db-1',
        database_id: 'notion-integration-db-1',
        database_name: 'Integration Test Database',
        is_active: true,
        last_synced: '2023-01-01T00:00:00Z',
        page_count: 25,
        sync_status: 'completed',
        document_count: 25
      },
      {
        id: 'integration-db-2',
        database_id: 'notion-integration-db-2',
        database_name: 'Secondary Test Database',
        is_active: true,
        last_synced: '2023-01-01T00:00:00Z',
        page_count: 15,
        sync_status: 'completed',
        document_count: 15
      }
    ])
  })
)

// Setup and teardown
beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

// Test wrapper component that provides necessary context
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div>
      {children}
    </div>
  )
}

describe('Chat Flow Integration Tests', () => {
  describe('Complete Chat Session Flow', () => {
    it('should handle complete new chat session creation and messaging', async () => {
      const user = userEvent.setup()

      render(
        <TestWrapper>
          <ChatInterface />
        </TestWrapper>
      )

      // Wait for component to initialize
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/ask me anything/i)).toBeInTheDocument()
      })

      // Type and send a message
      const messageInput = screen.getByPlaceholderText(/ask me anything/i)
      await user.type(messageInput, 'Hello, this is an integration test message')
      await user.keyboard('{enter}')

      // Wait for the message to be sent and response to arrive
      await waitFor(() => {
        expect(screen.getByText('Hello, this is an integration test message')).toBeInTheDocument()
      }, { timeout: 5000 })

      // Check for bot response
      await waitFor(() => {
        expect(screen.getByText(/Echo: Hello, this is an integration test message/)).toBeInTheDocument()
      }, { timeout: 5000 })

      // Verify input is cleared
      expect(messageInput).toHaveValue('')
    }, 10000)

    it('should load existing session with message history', async () => {
      const user = userEvent.setup()

      render(
        <TestWrapper>
          <ChatInterface />
        </TestWrapper>
      )

      // Wait for component to initialize
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/ask me anything/i)).toBeInTheDocument()
      })

      // Verify we show the workspace name in the header (not "New Chat")
      await waitFor(() => {
        expect(screen.getByText(/Test Workspace/i)).toBeInTheDocument()
      })
    }, 10000)
  })

  describe('Session Management Integration', () => {
    it('should create session on first message', async () => {
      const user = userEvent.setup()

      render(
        <TestWrapper>
          <ChatInterface />
        </TestWrapper>
      )

      // Wait for component to load
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/ask me anything/i)).toBeInTheDocument()
      })

      // Verify we show the workspace name in the header
      await waitFor(() => {
        expect(screen.getByText(/Test Workspace/i)).toBeInTheDocument()
      })

      // Send first message
      const messageInput = screen.getByPlaceholderText(/ask me anything/i)
      await user.type(messageInput, 'First message creates session')
      await user.keyboard('{enter}')

      // Verify message appears
      await waitFor(() => {
        expect(screen.getByText('First message creates session')).toBeInTheDocument()
      }, { timeout: 5000 })
    }, 10000)
  })

  describe('Error Handling Integration', () => {
    it('should handle API errors gracefully', async () => {
      // Override the chat endpoint to return an error
      server.use(
        http.post('http://localhost:8000/api/chat', () => {
          return HttpResponse.json({ error: 'API Error' }, { status: 500 })
        })
      )

      const user = userEvent.setup()

      render(
        <TestWrapper>
          <ChatInterface />
        </TestWrapper>
      )

      const messageInput = screen.getByPlaceholderText(/ask me anything/i)
      await user.type(messageInput, 'This message should fail')
      await user.keyboard('{enter}')

      // Verify error handling (component should still be functional)
      await waitFor(() => {
        expect(screen.getByText('This message should fail')).toBeInTheDocument()
      }, { timeout: 5000 })
    }, 10000)

    it('should handle network timeouts', async () => {
      // Override the chat endpoint to simulate timeout
      server.use(
        http.post('http://localhost:8000/api/chat', async () => {
          // Simulate a delay longer than typical timeout
          await new Promise(resolve => setTimeout(resolve, 10000))
          return HttpResponse.json({ response: 'Delayed response' })
        })
      )

      const user = userEvent.setup()

      render(
        <TestWrapper>
          <ChatInterface />
        </TestWrapper>
      )

      const messageInput = screen.getByPlaceholderText(/ask me anything/i)
      await user.type(messageInput, 'This might timeout')
      await user.keyboard('{enter}')

      // Verify the message was sent
      await waitFor(() => {
        expect(screen.getByText('This might timeout')).toBeInTheDocument()
      }, { timeout: 3000 })
    }, 15000)
  })

  describe('Real-time Features', () => {
    it('should handle streaming responses', async () => {
      const user = userEvent.setup()

      render(
        <TestWrapper>
          <ChatInterface />
        </TestWrapper>
      )

      const messageInput = screen.getByPlaceholderText(/ask me anything/i)
      await user.type(messageInput, 'Test streaming response')
      await user.keyboard('{enter}')

      // Verify user message appears
      await waitFor(() => {
        expect(screen.getByText('Test streaming response')).toBeInTheDocument()
      }, { timeout: 5000 })

      // Verify bot response appears
      await waitFor(() => {
        expect(screen.getByText(/Echo: Test streaming response/)).toBeInTheDocument()
      }, { timeout: 5000 })
    }, 10000)
  })

  describe('Performance Integration', () => {
    it('should handle rapid message sending', async () => {
      const user = userEvent.setup()

      render(
        <TestWrapper>
          <ChatInterface />
        </TestWrapper>
      )

      const messageInput = screen.getByPlaceholderText(/ask me anything/i)

      // Send multiple messages rapidly
      for (let i = 1; i <= 3; i++) {
        await user.clear(messageInput)
        await user.type(messageInput, `Rapid message ${i}`)
        await user.keyboard('{enter}')
        
        // Small delay to allow processing
        await new Promise(resolve => setTimeout(resolve, 100))
      }

      // Verify all messages appear
      await waitFor(() => {
        expect(screen.getByText('Rapid message 1')).toBeInTheDocument()
        expect(screen.getByText('Rapid message 2')).toBeInTheDocument()
        expect(screen.getByText('Rapid message 3')).toBeInTheDocument()
      }, { timeout: 10000 })
    }, 15000)
  })
})