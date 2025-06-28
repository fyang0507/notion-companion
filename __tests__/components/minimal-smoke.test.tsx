import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'

// Mock all dependencies
vi.mock('@/hooks/use-chat-sessions', () => ({
  useChatSessions: () => ({
    currentSession: null,
    currentMessages: [],
    isLoading: false,
    error: null,
    isTemporaryChat: true,
    addMessage: vi.fn(),
    startTemporaryChat: vi.fn(),
    setOnSessionCreated: vi.fn(),
  })
}))

vi.mock('@/hooks/use-notion-databases', () => ({
  useNotionDatabases: () => ({
    databases: [],
    loading: false,
    error: null
  })
}))

vi.mock('@/hooks/use-notion-connection', () => ({
  useNotionConnection: () => ({
    connection: null,
    isConnected: false
  })
}))

vi.mock('@/lib/api', () => ({
  apiClient: {
    sendChatMessage: vi.fn()
  }
}))

vi.mock('@/lib/logger', () => ({
  logger: {
    info: vi.fn(),
    error: vi.fn(),
    generateAndSetRequestId: vi.fn(() => 'test-request-id')
  }
}))

vi.mock('next-themes', () => ({
  useTheme: () => ({ theme: 'light' })
}))

import { ChatInterface } from '@/components/chat-interface'

describe('Component Smoke Tests', () => {
  it('ChatInterface renders without crashing', () => {
    const { container } = render(<ChatInterface />)
    expect(container).toBeTruthy()
    expect(container.firstChild).toBeTruthy()
  })

  it('ChatInterface renders basic structure', () => {
    const { container } = render(<ChatInterface />)
    const chatInterface = container.firstChild as HTMLElement
    
    // Should have the main container class
    expect(chatInterface).toHaveClass('flex', 'flex-col', 'h-full')
  })
})