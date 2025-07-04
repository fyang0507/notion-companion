/**
 * React hooks for dynamic metadata loading
 * 
 * Provides hooks for fetching and managing metadata for the chat filter bar,
 * replacing the mock data with real API calls.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  getDatabaseSchemas,
  getFilterOptions,
  getAggregatedFields,
  getMetadataStats,
  refreshMetadataCache,
  transformFilterOptionsForUI,
  withErrorHandling,
  type DatabaseSchema,
  type FilterOptions,
  type AggregatedFieldInfo,
  type MetadataStats
} from '@/lib/metadata-api';

// ============================================================================
// TYPES
// ============================================================================

interface UseMetadataOptions {
  autoRefresh?: boolean;
  refreshInterval?: number; // in milliseconds
  includeSampleValues?: boolean;
}

interface MetadataState {
  databases: DatabaseSchema[];
  filterOptions: FilterOptions | null;
  aggregatedFields: AggregatedFieldInfo[];
  stats: MetadataStats | null;
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
}

interface UseMetadataReturn extends MetadataState {
  refresh: () => Promise<void>;
  refreshCache: (databaseId?: string) => Promise<boolean>;
  isStale: boolean;
}

// ============================================================================
// MAIN METADATA HOOK
// ============================================================================

/**
 * Main hook for fetching and managing all metadata
 */
export function useMetadata(options: UseMetadataOptions = {}): UseMetadataReturn {
  const {
    autoRefresh = false,
    refreshInterval = 5 * 60 * 1000, // 5 minutes
    includeSampleValues = false
  } = options;

  const [state, setState] = useState<MetadataState>({
    databases: [],
    filterOptions: null,
    aggregatedFields: [],
    stats: null,
    loading: true,
    error: null,
    lastUpdated: null
  });

  // Check if data is stale (older than refresh interval)
  const isStale = useMemo(() => {
    if (!state.lastUpdated) return true;
    return Date.now() - state.lastUpdated.getTime() > refreshInterval;
  }, [state.lastUpdated, refreshInterval]);

  // Fetch all metadata
  const fetchMetadata = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));

    try {
      const [databases, filterOptions, aggregatedFields, stats] = await Promise.all([
        withErrorHandling(() => getDatabaseSchemas(includeSampleValues)),
        withErrorHandling(() => getFilterOptions()),
        withErrorHandling(() => getAggregatedFields(['tags', 'status', 'select'])),
        withErrorHandling(() => getMetadataStats())
      ]);

      setState({
        databases: databases || [],
        filterOptions: filterOptions || null,
        aggregatedFields: aggregatedFields || [],
        stats: stats || null,
        loading: false,
        error: null,
        lastUpdated: new Date()
      });
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to fetch metadata',
        lastUpdated: new Date()
      }));
    }
  }, [includeSampleValues]);

  // Refresh cache and refetch data
  const refreshCache = useCallback(async (databaseId?: string): Promise<boolean> => {
    const result = await withErrorHandling(() => refreshMetadataCache(databaseId));
    if (result?.success) {
      await fetchMetadata();
      return true;
    }
    return false;
  }, [fetchMetadata]);

  // Initial fetch
  useEffect(() => {
    fetchMetadata();
  }, [fetchMetadata]);

  // Auto-refresh setup
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      if (isStale) {
        fetchMetadata();
      }
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, isStale, fetchMetadata]);

  return {
    ...state,
    refresh: fetchMetadata,
    refreshCache,
    isStale
  };
}

// ============================================================================
// SPECIALIZED HOOKS
// ============================================================================

/**
 * Hook specifically for filter options used by the chat filter bar
 */
export function useFilterOptions() {
  const [filterOptions, setFilterOptions] = useState<FilterOptions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchFilterOptions = useCallback(async () => {
    setLoading(true);
    setError(null);

    const options = await withErrorHandling(() => getFilterOptions());
    if (options) {
      setFilterOptions(options);
    } else {
      setError('Failed to fetch filter options');
    }

    setLoading(false);
  }, []);

  useEffect(() => {
    fetchFilterOptions();
  }, [fetchFilterOptions]);

  // Transform for UI compatibility
  const uiFilterOptions = useMemo(() => {
    return filterOptions ? transformFilterOptionsForUI(filterOptions) : null;
  }, [filterOptions]);

  return {
    filterOptions,
    uiFilterOptions,
    loading,
    error,
    refresh: fetchFilterOptions
  };
}

/**
 * Hook for database schemas with document counts
 */
export function useDatabaseSchemas(includeSampleValues = false) {
  const [databases, setDatabases] = useState<DatabaseSchema[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDatabases = useCallback(async () => {
    setLoading(true);
    setError(null);

    const schemas = await withErrorHandling(() => getDatabaseSchemas(includeSampleValues));
    if (schemas) {
      setDatabases(schemas);
    } else {
      setError('Failed to fetch database schemas');
    }

    setLoading(false);
  }, [includeSampleValues]);

  useEffect(() => {
    fetchDatabases();
  }, [fetchDatabases]);

  // Transform for UI compatibility (availableWorkspaces format)
  const availableWorkspaces = useMemo(() => {
    return databases.map(db => ({
      id: db.database_id,
      name: db.database_name,
      documentCount: db.total_documents,
      metadata: {
        documentTypes: [], // Would need additional API call for detailed breakdown
        authors: [],
        tags: [],
        dateRange: { earliest: new Date(), latest: new Date() }
      }
    }));
  }, [databases]);

  return {
    databases,
    availableWorkspaces,
    loading,
    error,
    refresh: fetchDatabases
  };
}

/**
 * Hook for aggregated field information
 */
export function useAggregatedFields(fieldNames?: string[]) {
  const [fields, setFields] = useState<AggregatedFieldInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Memoize field names to prevent infinite loops
  const memoizedFieldNames = useMemo(() => fieldNames, [fieldNames ? JSON.stringify(fieldNames) : fieldNames]);

  const fetchFields = useCallback(async () => {
    setLoading(true);
    setError(null);

    const aggregatedFields = await withErrorHandling(() => getAggregatedFields(memoizedFieldNames));
    if (aggregatedFields) {
      setFields(aggregatedFields);
    } else {
      setError('Failed to fetch aggregated fields');
    }

    setLoading(false);
  }, [memoizedFieldNames]);

  useEffect(() => {
    fetchFields();
  }, [fetchFields]);

  // Extract specific field data for easy access
  const fieldData = useMemo(() => {
    const data: Record<string, AggregatedFieldInfo> = {};
    fields.forEach(field => {
      data[field.field_name] = field;
    });
    return data;
  }, [fields]);

  return {
    fields,
    fieldData,
    loading,
    error,
    refresh: fetchFields
  };
}

/**
 * Hook for metadata statistics
 */
export function useMetadataStats() {
  const [stats, setStats] = useState<MetadataStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);

    const metadata = await withErrorHandling(() => getMetadataStats());
    if (metadata) {
      setStats(metadata);
    } else {
      setError('Failed to fetch metadata stats');
    }

    setLoading(false);
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return {
    stats,
    loading,
    error,
    refresh: fetchStats
  };
}

// ============================================================================
// UTILITY HOOKS
// ============================================================================

/**
 * Hook that provides a debounced function for refreshing metadata
 */
export function useMetadataRefresh(delay = 1000) {
  const [refreshTimer, setRefreshTimer] = useState<NodeJS.Timeout | null>(null);

  const debouncedRefresh = useCallback((refreshFn: () => Promise<void>) => {
    // Use a ref to access current timer value without dependency issues
    setRefreshTimer(prevTimer => {
      if (prevTimer) {
        clearTimeout(prevTimer);
      }
      
      const timer = setTimeout(() => {
        refreshFn();
      }, delay);

      return timer;
    });
  }, [delay]); // Removed refreshTimer from dependencies

  useEffect(() => {
    return () => {
      if (refreshTimer) {
        clearTimeout(refreshTimer);
      }
    };
  }, [refreshTimer]);

  return debouncedRefresh;
}

/**
 * Hook for checking metadata freshness and showing staleness indicators
 */
export function useMetadataFreshness(lastUpdated: Date | null, maxAge = 5 * 60 * 1000) {
  const [isStale, setIsStale] = useState(false);

  useEffect(() => {
    if (!lastUpdated) {
      setIsStale(true);
      return;
    }

    const checkFreshness = () => {
      const age = Date.now() - lastUpdated.getTime();
      setIsStale(age > maxAge);
    };

    checkFreshness();
    const interval = setInterval(checkFreshness, 30000); // Check every 30 seconds

    return () => clearInterval(interval);
  }, [lastUpdated, maxAge]);

  return isStale;
} 