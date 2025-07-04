/**
 * Metadata API Client
 * 
 * Provides functions to interact with the metadata discovery endpoints
 * for dynamic filtering in the chat interface.
 */

const API_BASE = process.env.NODE_ENV === 'production' 
  ? process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  : 'http://localhost:8000';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

export interface FieldDefinition {
  field_name: string;
  field_type: 'text' | 'number' | 'select' | 'multi_select' | 'date' | 'checkbox' | 'status';
  notion_field: string;
  description?: string;
  is_filterable: boolean;
  sample_values?: any[];
}

export interface DatabaseSchema {
  database_id: string;
  database_name: string;
  field_definitions: FieldDefinition[];
  total_documents: number;
  last_analyzed_at?: string;
  is_active: boolean;
}

export interface AggregatedFieldInfo {
  field_name: string;
  field_type: string;
  databases: string[];
  unique_values: any[];
  value_counts: Record<string, number>;
  total_values: number;
}

export interface FilterOptions {
  authors: string[];
  tags: string[];
  statuses: string[];
  content_types: string[];
  databases: Array<{ id: string; name: string }>;
  date_ranges: { earliest?: string; latest?: string };
}

export interface MetadataStats {
  total_databases: number;
  total_documents: number;
  total_fields: number;
  field_coverage: Record<string, number>;
  last_updated: string;
}

export interface FieldValuesResponse {
  field_name: string;
  database_id: string;
  unique_values: any[];
  total_unique: number;
  value_counts?: Record<string, number>;
}

// ============================================================================
// API CLIENT FUNCTIONS
// ============================================================================

/**
 * Get metadata schemas for all configured databases
 */
export async function getDatabaseSchemas(includeSampleValues = false): Promise<DatabaseSchema[]> {
  const response = await fetch(`${API_BASE}/api/metadata/databases?include_sample_values=${includeSampleValues}`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch database schemas: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get detailed field definitions for a specific database
 */
export async function getDatabaseFields(
  databaseId: string, 
  includeSampleValues = true
): Promise<FieldDefinition[]> {
  const response = await fetch(
    `${API_BASE}/api/metadata/databases/${databaseId}/fields?include_sample_values=${includeSampleValues}`
  );
  
  if (!response.ok) {
    throw new Error(`Failed to fetch database fields: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get unique values for a specific field in a database
 */
export async function getFieldValues(
  databaseId: string,
  fieldName: string,
  includeCounts = true,
  limit = 100
): Promise<FieldValuesResponse> {
  const response = await fetch(
    `${API_BASE}/api/metadata/databases/${databaseId}/field-values/${fieldName}?include_counts=${includeCounts}&limit=${limit}`
  );
  
  if (!response.ok) {
    throw new Error(`Failed to fetch field values: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get aggregated metadata fields across all databases
 */
export async function getAggregatedFields(fieldNames?: string[]): Promise<AggregatedFieldInfo[]> {
  let url = `${API_BASE}/api/metadata/aggregated-fields`;
  
  if (fieldNames && fieldNames.length > 0) {
    // FastAPI expects repeated parameter names for arrays: field_names=tags&field_names=status
    const searchParams = new URLSearchParams();
    fieldNames.forEach(name => searchParams.append('field_names', name));
    url += `?${searchParams.toString()}`;
  }
  
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch aggregated fields: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get all available filter options for the UI
 */
export async function getFilterOptions(): Promise<FilterOptions> {
  const response = await fetch(`${API_BASE}/api/metadata/filter-options`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch filter options: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get overall metadata statistics
 */
export async function getMetadataStats(): Promise<MetadataStats> {
  const response = await fetch(`${API_BASE}/api/metadata/stats`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch metadata stats: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Refresh metadata cache for databases
 */
export async function refreshMetadataCache(databaseId?: string): Promise<{ message: string; success: boolean }> {
  const params = databaseId ? `?database_id=${databaseId}` : '';
  const response = await fetch(`${API_BASE}/api/metadata/cache/refresh${params}`, {
    method: 'POST'
  });
  
  if (!response.ok) {
    throw new Error(`Failed to refresh metadata cache: ${response.statusText}`);
  }
  
  return response.json();
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Transform backend FilterOptions to the format expected by chat-filter-bar
 */
export function transformFilterOptionsForUI(filterOptions: FilterOptions) {
  return {
    databases: filterOptions.databases.map(db => ({
      id: db.id,
      name: db.name,
      documentCount: 0 // This would need to be fetched separately if needed
    })),
    documentTypes: filterOptions.content_types.map((type, index) => ({
      id: type,
      name: type.charAt(0).toUpperCase() + type.slice(1),
      count: 0 // This would need to be calculated from actual data
    })),
    authors: filterOptions.authors.map((author, index) => ({
      id: `author-${index}`, // Generate ID since backend doesn't provide one
      name: author,
      count: 0 // This would need to be calculated from actual data
    })),
    tags: filterOptions.tags.map((tag, index) => ({
      id: `tag-${index}`, // Generate ID since backend doesn't provide one
      name: tag,
      color: getTagColor(index), // Generate color based on index
      count: 0 // This would need to be calculated from actual data
    })),
    statuses: filterOptions.statuses.map((status, index) => ({
      id: `status-${index}`, // Generate ID since backend doesn't provide one
      name: status,
      count: 0 // This would need to be calculated from actual data
    })),
    dateRange: {
      earliest: filterOptions.date_ranges.earliest ? new Date(filterOptions.date_ranges.earliest) : new Date(),
      latest: filterOptions.date_ranges.latest ? new Date(filterOptions.date_ranges.latest) : new Date()
    }
  };
}

/**
 * Generate consistent tag colors based on index
 */
function getTagColor(index: number): string {
  const colors = [
    'text-blue-600',
    'text-green-600', 
    'text-purple-600',
    'text-orange-600',
    'text-red-600',
    'text-yellow-600',
    'text-indigo-600',
    'text-cyan-600',
    'text-pink-600',
    'text-teal-600'
  ];
  
  return colors[index % colors.length];
}

/**
 * Error handling wrapper for API calls
 */
export async function withErrorHandling<T>(apiCall: () => Promise<T>): Promise<T | null> {
  try {
    return await apiCall();
  } catch (error) {
    console.error('Metadata API Error:', error);
    return null;
  }
} 