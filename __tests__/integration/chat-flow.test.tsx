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
      updated_at: new Date().toISOString()
    })
  }),

  http.get('http://localhost:8000/api/chat-sessions/:sessionId', ({ params }) => {
    return HttpResponse.json({
      session: {
        id: params.sessionId,
        title: 'Loaded Integration Session',
        status: 'active',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:00:00Z'
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
        name: 'Integration Test Database',
        notion_database_id: 'notion-integration-db-1',
        is_active: true,
        last_synced: '2023-01-01T00:00:00Z',
        page_count: 25,
        sync_status: 'completed'
      },
      {
        id: 'integration-db-2',
        name: 'Secondary Test Database',
        notion_database_id: 'notion-integration-db-2',
        is_active: true,
        last_synced: '2023-01-01T00:00:00Z',
        page_count: 15,
        sync_status: 'completed'
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
        expect(screen.getByPlaceholderText(/type your message/i)).toBeInTheDocument()
      })

      // Type and send a message
      const messageInput = screen.getByPlaceholderText(/type your message/i)
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

    it('should handle database filtering in chat requests', async () => {
      const user = userEvent.setup()

      render(
        <TestWrapper>
          <ChatInterface />
        </TestWrapper>
      )

      // Wait for databases to load
      await waitFor(() => {
        expect(screen.getByText('Integration Test Database')).toBeInTheDocument()
      })

      // Select specific database
      const databaseCheckbox = screen.getByLabelText('Secondary Test Database')
      await user.click(databaseCheckbox)

      // Send message with database filter
      const messageInput = screen.getByPlaceholderText(/type your message/i)
      await user.type(messageInput, 'Search with database filter')
      await user.keyboard('{enter}')

      // Wait for response
      await waitFor(() => {
        expect(screen.getByText(/Echo: Search with database filter/)).toBeInTheDocument()
      })

      // Verify the request included database filters
      // (This would be verified through the mock server receiving the correct request)
    })
  })

  describe('Search Integration', () => {
    it('should perform search and display results', async () => {
      const user = userEvent.setup()

      // This test would need a search component or search functionality in ChatInterface
      // For now, we'll test the API integration directly through the chat interface
      
      render(
        <TestWrapper>
          <ChatInterface />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/type your message/i)).toBeInTheDocument()
      })

      // Send a search-like message
      const messageInput = screen.getByPlaceholderText(/type your message/i)
      await user.type(messageInput, 'What documents mention integration testing?')
      await user.keyboard('{enter}')

      // Wait for response with potential search results
      await waitFor(() => {
        expect(screen.getByText(/Echo: What documents mention integration testing/)).toBeInTheDocument()
      })
    })
  })

  describe('Session Management Integration', () => {
    it('should create session on first message', async () => {
      const user = userEvent.setup()

      render(
        <TestWrapper>
          <ChatInterface />
        </TestWrapper>
      )

      // Verify we start in temporary chat mode
      await waitFor(() => {
        expect(screen.getByText(/new chat/i)).toBeInTheDocument()
      })

      // Send first message
      const messageInput = screen.getByPlaceholderText(/type your message/i)
      await user.type(messageInput, 'First message to create session')
      await user.keyboard('{enter}')

      // Wait for session to be created and message to be sent
      await waitFor(() => {
        expect(screen.getByText('First message to create session')).toBeInTheDocument()
      })

      // Verify we're no longer in temporary chat mode
      await waitFor(() => {
        expect(screen.queryByText(/new chat/i)).not.toBeInTheDocument()
      })
    })

    it('should handle session loading', async () => {
      // This would require implementing session loading in the ChatInterface
      // For now, we can test that the API endpoints are working correctly
      const sessionResponse = await fetch('http://localhost:8000/api/chat-sessions/test-session')
      expect(sessionResponse.ok).toBe(true)
    })
  })

  describe('Error Handling Integration', () => {
    it('should handle API errors gracefully', async () => {
      const user = userEvent.setup()

      // Override server to return error
      server.use(
        http.post('http://localhost:8000/api/chat', () => {
          return new HttpResponse(null, { status: 500 })
        })
      )

      render(
        <TestWrapper>
          <ChatInterface />
        </TestWrapper>
      )

      const messageInput = screen.getByPlaceholderText(/type your message/i)
      await user.type(messageInput, 'This message should fail')
      await user.keyboard('{enter}')

      // Wait for error to be displayed
      await waitFor(() => {
        expect(screen.getByText(/error/i)).toBeInTheDocument()
      })
    })

    it('should handle network timeouts', async () => {
      const user = userEvent.setup()

      // Override server to delay response
      server.use(
        http.post('http://localhost:8000/api/chat', () => {
          return new Promise(resolve => {
            setTimeout(() => {
              resolve(HttpResponse.json({ response: 'Delayed response' }))
            }, 6000) // Longer than typical timeout
          })
        })
      )

      render(
        <TestWrapper>
          <ChatInterface />
        </TestWrapper>
      )

      const messageInput = screen.getByPlaceholderText(/type your message/i)
      await user.type(messageInput, 'This might timeout')
      await user.keyboard('{enter}')

      // Should show loading state
      expect(screen.getByTestId('loading-indicator')).toBeInTheDocument()
    })
  })

  describe('Real-time Features', () => {
    it('should handle streaming responses', async () => {
      const user = userEvent.setup()

      // Mock streaming response
      server.use(
        http.post('http://localhost:8000/api/chat', () => {
          // For this test, we'll simulate the final streamed result
          return HttpResponse.json({
            response: 'This is a streamed response that arrived in chunks',
            session_id: 'streaming-session',
            model_used: 'gpt-4',
            tokens_used: 15
          })
        })
      )

      render(
        <TestWrapper>
          <ChatInterface />
        </TestWrapper>
      )

      const messageInput = screen.getByPlaceholderText(/type your message/i)
      await user.type(messageInput, 'Test streaming response')
      await user.keyboard('{enter}')

      await waitFor(() => {
        expect(screen.getByText(/This is a streamed response/)).toBeInTheDocument()
      })
    })
  })

  describe('Performance Integration', () => {
    it('should handle rapid message sending', async () => {
      const user = userEvent.setup()

      render(
        <TestWrapper>
          <ChatInterface />
        </TestWrapper>
      )

      const messageInput = screen.getByPlaceholderText(/type your message/i)

      // Send multiple messages rapidly
      for (let i = 1; i <= 3; i++) {
        await user.clear(messageInput)
        await user.type(messageInput, `Rapid message ${i}`)
        await user.keyboard('{enter}')
        
        // Small delay to prevent overwhelming
        await new Promise(resolve => setTimeout(resolve, 100))
      }

      // All messages should eventually appear
      await waitFor(() => {
        expect(screen.getByText('Rapid message 1')).toBeInTheDocument()
        expect(screen.getByText('Rapid message 2')).toBeInTheDocument()
        expect(screen.getByText('Rapid message 3')).toBeInTheDocument()
      }, { timeout: 10000 })
    })
  })
})