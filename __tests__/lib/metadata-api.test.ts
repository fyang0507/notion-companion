/**
 * Tests for metadata API client functions
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  getDatabaseSchemas,
  getFilterOptions,
  getAggregatedFields,
  getMetadataStats,
  refreshMetadataCache,
  transformFilterOptionsForUI
} from '@/lib/metadata-api'

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('Metadata API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('getDatabaseSchemas', () => {
    it('fetches database schemas without sample values', async () => {
      const mockResponse = [
        {
          database_id: 'db-1',
          database_name: 'Test Database',
          field_definitions: [
            {
              field_name: 'author',
              field_type: 'text',
              notion_field: 'Author',
              description: 'Article author',
              is_filterable: true
            }
          ],
          document_count: 10,
          last_analyzed: '2024-01-01T00:00:00Z'
        }
      ]

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      })

      const result = await getDatabaseSchemas(false)

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/metadata/databases?include_sample_values=false')
      )
      expect(result).toEqual(mockResponse)
    })

    it('fetches database schemas with sample values', async () => {
      const mockResponse = [
        {
          database_id: 'db-1',
          database_name: 'Test Database',
          field_definitions: [
            {
              field_name: 'author',
              field_type: 'text',
              notion_field: 'Author',
              description: 'Article author',
              is_filterable: true,
              sample_values: ['John Doe', 'Jane Smith']
            }
          ],
          document_count: 10,
          last_analyzed: '2024-01-01T00:00:00Z'
        }
      ]

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      })

      const result = await getDatabaseSchemas(true)

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/metadata/databases?include_sample_values=true')
      )
      expect(result).toEqual(mockResponse)
    })

    it('handles fetch errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error'
      })

      await expect(getDatabaseSchemas()).rejects.toThrow(
        'Failed to fetch database schemas: Internal Server Error'
      )
    })

    it('handles network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'))

      await expect(getDatabaseSchemas()).rejects.toThrow('Network error')
    })
  })

  describe('getFilterOptions', () => {
    it('fetches filter options without search', async () => {
      const mockResponse = {
        authors: ['John Doe', 'Jane Smith'],
        tags: ['AI', 'Tech'],
        statuses: ['published', 'draft'],
        content_types: ['article', 'note'],
        databases: [{ id: 'db-1', name: 'Test Database' }],
        date_ranges: { earliest: '2024-01-01', latest: '2024-12-31' }
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      })

      const result = await getFilterOptions()

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/metadata/filter-options')
      )
      expect(result).toEqual(mockResponse)
    })

    it('fetches filter options with search', async () => {
      const mockResponse = {
        authors: ['John Doe'],
        tags: ['AI'],
        statuses: ['published'],
        content_types: ['article'],
        databases: [{ id: 'db-1', name: 'Test Database' }],
        date_ranges: { earliest: '2024-01-01', latest: '2024-12-31' }
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      })

      const result = await getFilterOptions('john')

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/metadata/filter-options?search=john')
      )
      expect(result).toEqual(mockResponse)
    })

    it('handles fetch errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error'
      })

      await expect(getFilterOptions()).rejects.toThrow(
        'Failed to fetch filter options: Internal Server Error'
      )
    })
  })

  describe('getAggregatedFields', () => {
    it('fetches aggregated fields', async () => {
      const mockResponse = [
        {
          field_name: 'author',
          field_type: 'text',
          databases: ['db-1'],
          unique_values: ['John Doe', 'Jane Smith'],
          value_counts: { 'John Doe': 5, 'Jane Smith': 3 },
          total_values: 2
        }
      ]

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      })

      const result = await getAggregatedFields(['author', 'tags'])

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/metadata/aggregated-fields')
      )
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('field_names=author')
      )
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('field_names=tags')
      )
      expect(result).toEqual(mockResponse)
    })

    it('fetches aggregated fields with options', async () => {
      const mockResponse = [
        {
          field_name: 'author',
          field_type: 'text',
          databases: ['db-1'],
          unique_values: ['John Doe'],
          value_counts: { 'John Doe': 5 },
          total_values: 1
        }
      ]

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      })

      const result = await getAggregatedFields(
        ['author'],
        { search: 'john', limitPerField: 50 }
      )

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/metadata/aggregated-fields')
      )
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('field_names=author')
      )
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('search=john')
      )
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('limit_per_field=50')
      )
      expect(result).toEqual(mockResponse)
    })

    it('handles empty field names', async () => {
      const mockResponse = []

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      })

      const result = await getAggregatedFields([])

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/metadata/aggregated-fields')
      )
      expect(result).toEqual([])
    })

    it('handles fetch errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error'
      })

      await expect(getAggregatedFields(['author'])).rejects.toThrow(
        'Failed to fetch aggregated fields: Internal Server Error'
      )
    })
  })

  describe('getMetadataStats', () => {
    it('fetches metadata statistics', async () => {
      const mockResponse = {
        total_documents: 100,
        total_databases: 2,
        last_sync: '2024-01-01T00:00:00Z'
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      })

      const result = await getMetadataStats()

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/metadata/stats')
      )
      expect(result).toEqual(mockResponse)
    })

    it('handles fetch errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error'
      })

      await expect(getMetadataStats()).rejects.toThrow(
        'Failed to fetch metadata stats: Internal Server Error'
      )
    })
  })

  describe('refreshMetadataCache', () => {
    it('refreshes cache for all databases', async () => {
      const mockResponse = { success: true }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      })

      const result = await refreshMetadataCache()

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/metadata/cache/refresh'),
        expect.objectContaining({
          method: 'POST'
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('refreshes cache for specific database', async () => {
      const mockResponse = { success: true }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      })

      const result = await refreshMetadataCache('db-1')

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/metadata/cache/refresh?database_id=db-1'),
        expect.objectContaining({
          method: 'POST'
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('handles fetch errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error'
      })

      await expect(refreshMetadataCache()).rejects.toThrow(
        'Failed to refresh metadata cache: Internal Server Error'
      )
    })
  })

  describe('transformFilterOptionsForUI', () => {
    it('transforms filter options to UI format', () => {
      const filterOptions = {
        authors: ['John Doe', 'Jane Smith'],
        tags: ['AI', 'Tech'],
        statuses: ['published', 'draft'],
        content_types: ['article', 'note'],
        databases: [
          { id: 'db-1', name: 'Test Database' },
          { id: 'db-2', name: 'Another Database' }
        ],
        date_ranges: { 
          earliest: '2024-01-01', 
          latest: '2024-12-31' 
        }
      }

      const result = transformFilterOptionsForUI(filterOptions)

      // Check databases transformation
      expect(result.databases).toHaveLength(2)
      expect(result.databases[0]).toEqual({
        id: 'db-1',
        name: 'Test Database',
        documentCount: 0
      })

      // Check document types transformation
      expect(result.documentTypes).toHaveLength(2)
      expect(result.documentTypes[0]).toEqual({
        id: 'article',
        name: 'Article',
        count: 0
      })

      // Check authors transformation
      expect(result.authors).toHaveLength(2)
      expect(result.authors[0]).toEqual({
        id: 'author-0',
        name: 'John Doe',
        count: 0
      })

      // Check tags transformation
      expect(result.tags).toHaveLength(2)
      expect(result.tags[0]).toEqual({
        id: 'tag-0',
        name: 'AI',
        color: expect.any(String),
        count: 0
      })

      // Check statuses transformation
      expect(result.statuses).toHaveLength(2)
      expect(result.statuses[0]).toEqual({
        id: 'status-0',
        name: 'published',
        count: 0
      })

      // Check date range transformation
      expect(result.dateRange).toEqual({
        earliest: new Date('2024-01-01'),
        latest: new Date('2024-12-31')
      })
    })

    it('handles empty filter options', () => {
      const filterOptions = {
        authors: [],
        tags: [],
        statuses: [],
        content_types: [],
        databases: [],
        date_ranges: {}
      }

      const result = transformFilterOptionsForUI(filterOptions)

      expect(result.databases).toHaveLength(0)
      expect(result.documentTypes).toHaveLength(0)
      expect(result.authors).toHaveLength(0)
      expect(result.tags).toHaveLength(0)
      expect(result.statuses).toHaveLength(0)
      expect(result.dateRange.earliest).toBeInstanceOf(Date)
      expect(result.dateRange.latest).toBeInstanceOf(Date)
    })

    it('handles missing date ranges', () => {
      const filterOptions = {
        authors: [],
        tags: [],
        statuses: [],
        content_types: [],
        databases: [],
        date_ranges: { earliest: undefined, latest: undefined }
      }

      const result = transformFilterOptionsForUI(filterOptions)

      expect(result.dateRange.earliest).toBeInstanceOf(Date)
      expect(result.dateRange.latest).toBeInstanceOf(Date)
    })
  })

  describe('Error handling and edge cases', () => {
    it('handles malformed JSON responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.reject(new Error('Invalid JSON'))
      })

      await expect(getDatabaseSchemas()).rejects.toThrow('Invalid JSON')
    })

    it('handles empty responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(null)
      })

      const result = await getDatabaseSchemas()
      expect(result).toBeNull()
    })

    it('handles timeout errors', async () => {
      mockFetch.mockImplementationOnce(() => 
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Timeout')), 100)
        )
      )

      await expect(getDatabaseSchemas()).rejects.toThrow('Timeout')
    })

    it('handles unicode characters in search', async () => {
      const mockResponse = {
        authors: ['张三', '李四'],
        tags: ['人工智能'],
        statuses: [],
        content_types: [],
        databases: [],
        date_ranges: {}
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      })

      const result = await getFilterOptions('张三')

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/metadata/filter-options?search=%E5%BC%A0%E4%B8%89')
      )
      expect(result).toEqual(mockResponse)
    })

    it('handles special characters in field names', async () => {
      const mockResponse = [
        {
          field_name: 'field-with-dashes',
          field_type: 'text',
          databases: ['db-1'],
          unique_values: ['value1', 'value2'],
          value_counts: { 'value1': 1, 'value2': 2 },
          total_values: 2
        }
      ]

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      })

      const result = await getAggregatedFields(['field-with-dashes', 'field_with_underscores'])

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('field_names=field-with-dashes')
      )
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('field_names=field_with_underscores')
      )
      expect(result).toEqual(mockResponse)
    })
  })
}) 