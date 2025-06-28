import { vi } from 'vitest'
import { 
  ChatSession, 
  ChatSessionMessage, 
  RecentChatSummary, 
  SearchResponse,
  ChatSessionWithMessages 
} from '@/lib/api'

// Mock data generators
export const createMockChatSession = (overrides?: Partial<ChatSession>): ChatSession => ({
  id: 'test-session-123',
  title: 'Test Chat Session',
  summary: 'A test chat session',
  status: 'active',
  message_count: 0,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  last_message_at: '2024-01-01T00:00:00Z',
  session_context: {},
  ...overrides
})

export const createMockChatMessage = (overrides?: Partial<ChatSessionMessage>): ChatSessionMessage => ({
  id: 'test-message-123',
  session_id: 'test-session-123',
  role: 'user',
  content: 'Hello, this is a test message',
  citations: [],
  context_used: {},
  created_at: '2024-01-01T00:00:00Z',
  message_order: 1,
  ...overrides
})

export const createMockSessionWithMessages = (overrides?: Partial<ChatSessionWithMessages>): ChatSessionWithMessages => ({
  session: createMockChatSession(),
  messages: [createMockChatMessage()],
  ...overrides
})

export const createMockRecentChats = (): RecentChatSummary[] => [
  {
    id: 'recent-1',
    title: 'Recent Chat 1',
    status: 'active',
    message_count: 5,
    last_message_at: '2024-01-01T01:00:00Z',
    created_at: '2024-01-01T00:00:00Z',
    last_message_preview: 'Last message preview...'
  },
  {
    id: 'recent-2',
    title: 'Recent Chat 2',
    status: 'concluded',
    message_count: 3,
    last_message_at: '2024-01-01T00:30:00Z',
    created_at: '2024-01-01T00:00:00Z',
    last_message_preview: 'Another message preview...'
  }
]

export const createMockSearchResponse = (): SearchResponse => ({
  results: [
    {
      id: 'result-1',
      title: 'Test Document 1',
      content: 'This is test content for document 1',
      similarity: 0.85,
      metadata: { source: 'notion' },
      notion_page_id: 'notion-page-1'
    },
    {
      id: 'result-2',
      title: 'Test Document 2',
      content: 'This is test content for document 2',
      similarity: 0.75,
      metadata: { source: 'notion' },
      notion_page_id: 'notion-page-2'
    }
  ],
  query: 'test query',
  total: 2
})

// Mock ReadableStream for chat streaming
export class MockReadableStream extends ReadableStream {
  constructor() {
    super({
      start(controller) {
        // Simulate streaming chat response
        const chunks = [
          'data: {"content": "Hello"}\n\n',
          'data: {"content": " there!"}\n\n',
          'data: [DONE]\n\n'
        ]
        
        chunks.forEach((chunk, index) => {
          setTimeout(() => {
            controller.enqueue(new TextEncoder().encode(chunk))
            if (index === chunks.length - 1) {
              controller.close()
            }
          }, index * 10)
        })
      }
    })
  }
}

// ApiClient mock factory
export const createMockApiClient = () => ({
  // Core chat methods
  sendChatMessage: vi.fn().mockResolvedValue(new MockReadableStream()),
  search: vi.fn().mockResolvedValue(createMockSearchResponse()),
  
  // Session management
  createChatSession: vi.fn().mockResolvedValue(createMockChatSession()),
  getChatSession: vi.fn().mockResolvedValue(createMockSessionWithMessages()),
  updateChatSession: vi.fn().mockResolvedValue(createMockChatSession()),
  deleteChatSession: vi.fn().mockResolvedValue({ message: 'Session deleted' }),
  getRecentChats: vi.fn().mockResolvedValue(createMockRecentChats()),
  
  // Message management
  addMessageToSession: vi.fn().mockResolvedValue(createMockChatMessage()),
  
  // Session lifecycle
  concludeChatSession: vi.fn().mockResolvedValue({ 
    message: 'Session concluded', 
    title: 'Concluded Chat',
    summary: 'Chat summary'
  }),
  concludeForResume: vi.fn().mockResolvedValue({ 
    message: 'Session concluded for resume', 
    title: 'Previous Chat',
    summary: 'Previous chat summary'
  }),
  concludeForNewChat: vi.fn().mockResolvedValue({ 
    message: 'Session concluded for new chat' 
  }),
  
  // Webhook
  processNotionWebhook: vi.fn().mockResolvedValue({ success: true })
})

// Global fetch mock setup
export const setupFetchMocks = () => {
  const mockFetch = vi.fn()
  global.fetch = mockFetch
  return mockFetch
}

// Reset all mocks
export const resetAllMocks = () => {
  vi.clearAllMocks()
}