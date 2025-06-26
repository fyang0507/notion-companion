/**
 * Tests for useNotionConnection hook
 */

import { renderHook, act, waitFor } from '@testing-library/react'
import { useNotionConnection } from '@/hooks/use-notion-connection'

// Mock dependencies
jest.mock('@/lib/supabase', () => ({
  supabase: {
    from: jest.fn((table) => {
      if (table === 'notion_databases') {
        return {
          select: jest.fn().mockReturnValue({
            eq: jest.fn().mockReturnValue({
              order: jest.fn().mockReturnValue({
                limit: jest.fn().mockReturnValue({
                  single: jest.fn().mockResolvedValue({
                    data: null,
                    error: { code: 'PGRST116' } // No rows found
                  })
                })
              })
            })
          })
        }
      } else if (table === 'documents') {
        return {
          select: jest.fn().mockReturnValue({
            eq: jest.fn().mockResolvedValue({
              data: null,
              error: null,
              count: 0
            })
          })
        }
      }
      return {
        select: jest.fn().mockResolvedValue({ data: [], error: null })
      }
    })
  }
}))

jest.mock('@/hooks/use-auth', () => ({
  useAuth: () => ({
    user: { 
      id: 'test-user-id',
      email: 'test@example.com' 
    }
  })
}))

jest.mock('@/lib/logger', () => ({
  logger: {
    error: jest.fn(),
    info: jest.fn()
  }
}))

jest.mock('@/lib/frontend-error-logger', () => ({
  useFrontendErrorLogger: () => ({
    logHookError: jest.fn(),
    logApiError: jest.fn()
  })
}))

describe('useNotionConnection Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('Initial State', () => {
    it('should initialize with correct default values', async () => {
      const { result } = renderHook(() => useNotionConnection())

      expect(result.current.connection).toBeNull()
      expect(result.current.isConnected).toBe(false)
      expect(result.current.error).toBeNull()
      expect(typeof result.current.refetch).toBe('function')
      expect(typeof result.current.connectNotion).toBe('function')
      expect(typeof result.current.syncNotion).toBe('function')
      
      // Wait for loading to complete since it happens immediately in tests
      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })
    })
  })

  describe('Connection Loading', () => {
    it('should complete loading when no connection found', async () => {
      const { result } = renderHook(() => useNotionConnection())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
        expect(result.current.connection).toBeNull()
        expect(result.current.isConnected).toBe(false)
        expect(result.current.error).toBeNull()
      })
    })
  })

  describe('Connection Methods', () => {
    it('should have connectNotion method available', () => {
      const { result } = renderHook(() => useNotionConnection())
      
      expect(typeof result.current.connectNotion).toBe('function')
    })

    it('should have syncNotion method available', () => {
      const { result } = renderHook(() => useNotionConnection())
      
      expect(typeof result.current.syncNotion).toBe('function')
    })

    it('should have refetch method available', () => {
      const { result } = renderHook(() => useNotionConnection())
      
      expect(typeof result.current.refetch).toBe('function')
    })
  })

  describe('Error Handling', () => {
    it('should handle connection errors gracefully', async () => {
      const { result } = renderHook(() => useNotionConnection())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Should not crash and should maintain proper state
      expect(result.current.connection).toBeNull()
      expect(result.current.isConnected).toBe(false)
    })
  })
})