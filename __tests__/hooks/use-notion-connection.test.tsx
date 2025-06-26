/**
 * Tests for useNotionConnection hook - Notion API integration
 */

import { renderHook, act, waitFor } from '@testing-library/react'
import { useNotionConnection } from '@/hooks/use-notion-connection'
import { apiClient } from '@/lib/api'

// Mock the API client
jest.mock('@/lib/api', () => ({
  apiClient: {
    getNotionDatabases: jest.fn(),
    syncNotionDatabase: jest.fn(),
    testNotionConnection: jest.fn(),
  }
}))

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>

describe('useNotionConnection Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    
    // Default mock implementations
    mockApiClient.getNotionDatabases.mockResolvedValue([
      {
        id: 'db-1',
        name: 'Test Database 1',
        notion_database_id: 'notion-db-1',
        is_active: true,
        last_synced: '2023-01-01T00:00:00Z',
        page_count: 10,
        sync_status: 'completed'
      },
      {
        id: 'db-2',
        name: 'Test Database 2',
        notion_database_id: 'notion-db-2',
        is_active: false,
        last_synced: '2023-01-01T00:00:00Z',
        page_count: 5,
        sync_status: 'pending'
      }
    ])

    mockApiClient.testNotionConnection.mockResolvedValue({
      connected: true,
      workspace_name: 'Test Workspace',
      accessible_databases: 2
    })
  })

  describe('Initial State', () => {
    it('should initialize with correct default values', () => {
      const { result } = renderHook(() => useNotionConnection())

      expect(result.current.databases).toEqual([])
      expect(result.current.isLoading).toBe(false)
      expect(result.current.error).toBeNull()
      expect(result.current.connectionStatus).toBe('unknown')
    })
  })

  describe('Database Loading', () => {
    it('should load databases successfully', async () => {
      const { result } = renderHook(() => useNotionConnection())

      await act(async () => {
        await result.current.loadDatabases()
      })

      await waitFor(() => {
        expect(mockApiClient.getNotionDatabases).toHaveBeenCalled()
        expect(result.current.databases).toHaveLength(2)
        expect(result.current.databases[0].name).toBe('Test Database 1')
        expect(result.current.databases[1].name).toBe('Test Database 2')
        expect(result.current.isLoading).toBe(false)
        expect(result.current.error).toBeNull()
      })
    })

    it('should handle loading errors', async () => {
      const { result } = renderHook(() => useNotionConnection())

      mockApiClient.getNotionDatabases.mockRejectedValue(new Error('Failed to load databases'))

      await act(async () => {
        await result.current.loadDatabases()
      })

      await waitFor(() => {
        expect(result.current.databases).toEqual([])
        expect(result.current.error).toBe('Failed to load databases')
        expect(result.current.isLoading).toBe(false)
      })
    })

    it('should set loading state during database fetch', async () => {
      const { result } = renderHook(() => useNotionConnection())

      // Mock a delayed response
      mockApiClient.getNotionDatabases.mockImplementation(
        () => new Promise(resolve => 
          setTimeout(() => resolve([]), 100)
        )
      )

      act(() => {
        result.current.loadDatabases()
      })

      expect(result.current.isLoading).toBe(true)

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })
    })
  })

  describe('Connection Testing', () => {
    it('should test connection successfully', async () => {
      const { result } = renderHook(() => useNotionConnection())

      await act(async () => {
        await result.current.testConnection()
      })

      await waitFor(() => {
        expect(mockApiClient.testNotionConnection).toHaveBeenCalled()
        expect(result.current.connectionStatus).toBe('connected')
        expect(result.current.error).toBeNull()
      })
    })

    it('should handle connection failure', async () => {
      const { result } = renderHook(() => useNotionConnection())

      mockApiClient.testNotionConnection.mockRejectedValue(new Error('Connection failed'))

      await act(async () => {
        await result.current.testConnection()
      })

      await waitFor(() => {
        expect(result.current.connectionStatus).toBe('disconnected')
        expect(result.current.error).toBe('Connection failed')
      })
    })

    it('should handle unauthorized connection', async () => {
      const { result } = renderHook(() => useNotionConnection())

      mockApiClient.testNotionConnection.mockResolvedValue({
        connected: false,
        error: 'Unauthorized access'
      })

      await act(async () => {
        await result.current.testConnection()
      })

      await waitFor(() => {
        expect(result.current.connectionStatus).toBe('disconnected')
        expect(result.current.error).toBe('Unauthorized access')
      })
    })
  })

  describe('Database Synchronization', () => {
    it('should sync database successfully', async () => {
      const { result } = renderHook(() => useNotionConnection())

      mockApiClient.syncNotionDatabase.mockResolvedValue({
        success: true,
        pages_synced: 15,
        sync_duration_ms: 5000
      })

      await act(async () => {
        await result.current.syncDatabase('db-1')
      })

      await waitFor(() => {
        expect(mockApiClient.syncNotionDatabase).toHaveBeenCalledWith('db-1')
        expect(result.current.error).toBeNull()
      })
    })

    it('should handle sync errors', async () => {
      const { result } = renderHook(() => useNotionConnection())

      mockApiClient.syncNotionDatabase.mockRejectedValue(new Error('Sync failed'))

      await act(async () => {
        await result.current.syncDatabase('db-1')
      })

      await waitFor(() => {
        expect(result.current.error).toBe('Sync failed')
      })
    })
  })

  describe('Database Filtering', () => {
    it('should filter active databases', async () => {
      const { result } = renderHook(() => useNotionConnection())

      await act(async () => {
        await result.current.loadDatabases()
      })

      await waitFor(() => {
        const activeDatabases = result.current.getActiveDatabases()
        expect(activeDatabases).toHaveLength(1)
        expect(activeDatabases[0].id).toBe('db-1')
        expect(activeDatabases[0].is_active).toBe(true)
      })
    })

    it('should get database by id', async () => {
      const { result } = renderHook(() => useNotionConnection())

      await act(async () => {
        await result.current.loadDatabases()
      })

      await waitFor(() => {
        const database = result.current.getDatabaseById('db-1')
        expect(database).toBeDefined()
        expect(database?.name).toBe('Test Database 1')

        const nonExistentDb = result.current.getDatabaseById('non-existent')
        expect(nonExistentDb).toBeUndefined()
      })
    })
  })

  describe('Error Handling and Recovery', () => {
    it('should clear errors when retrying operations', async () => {
      const { result } = renderHook(() => useNotionConnection())

      // First call fails
      mockApiClient.getNotionDatabases.mockRejectedValueOnce(new Error('First failure'))

      await act(async () => {
        await result.current.loadDatabases()
      })

      expect(result.current.error).toBe('First failure')

      // Second call succeeds
      mockApiClient.getNotionDatabases.mockResolvedValueOnce([])

      await act(async () => {
        await result.current.loadDatabases()
      })

      await waitFor(() => {
        expect(result.current.error).toBeNull()
      })
    })

    it('should handle concurrent operations safely', async () => {
      const { result } = renderHook(() => useNotionConnection())

      // Start multiple operations concurrently
      const promises = [
        result.current.loadDatabases(),
        result.current.testConnection(),
        result.current.loadDatabases()
      ]

      await act(async () => {
        await Promise.all(promises)
      })

      // Should complete without errors
      await waitFor(() => {
        expect(result.current.error).toBeNull()
        expect(result.current.isLoading).toBe(false)
      })
    })
  })

  describe('Refresh Operations', () => {
    it('should refresh databases and reload data', async () => {
      const { result } = renderHook(() => useNotionConnection())

      // Initial load
      await act(async () => {
        await result.current.loadDatabases()
      })

      expect(mockApiClient.getNotionDatabases).toHaveBeenCalledTimes(1)

      // Refresh should call API again
      await act(async () => {
        await result.current.refreshDatabases()
      })

      expect(mockApiClient.getNotionDatabases).toHaveBeenCalledTimes(2)
    })
  })

  describe('Connection Status Management', () => {
    it('should update connection status based on API responses', async () => {
      const { result } = renderHook(() => useNotionConnection())

      expect(result.current.connectionStatus).toBe('unknown')

      // Test successful connection
      await act(async () => {
        await result.current.testConnection()
      })

      expect(result.current.connectionStatus).toBe('connected')

      // Test failed connection
      mockApiClient.testNotionConnection.mockRejectedValueOnce(new Error('Connection lost'))

      await act(async () => {
        await result.current.testConnection()
      })

      expect(result.current.connectionStatus).toBe('disconnected')
    })
  })
})