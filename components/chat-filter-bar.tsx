'use client';

import { useState, useEffect, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Card, CardContent } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Checkbox } from '@/components/ui/checkbox';
import { 
  Filter, 
  X, 
  Search, 
  Database, 
  Globe,
  ChevronDown,
  RefreshCw,
  AlertCircle
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useDatabaseSchemas, useAggregatedFields } from '@/hooks/use-metadata';
import { DynamicFilterSection } from '@/components/dynamic-filter-section';
import { ChatFilter, DatabaseFieldDefinition, FieldFilterOptions } from '@/types/chat';
import { FieldDefinition } from '@/lib/metadata-api';

interface ChatFilterBarProps {
  filters: ChatFilter;
  onFiltersChange: (filters: ChatFilter) => void;
  disabled?: boolean;
}

export function ChatFilterBar({ filters, onFiltersChange, disabled = false }: ChatFilterBarProps) {
  const [searchQuery, setSearchQuery] = useState(filters.searchQuery || '');
  const [isExpanded, setIsExpanded] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Get database schemas with field definitions
  const { 
    databases, 
    loading: databasesLoading, 
    error: databasesError,
    refresh: refreshDatabases 
  } = useDatabaseSchemas();

  // Get aggregated field data for the selected databases
  const selectedDatabaseFieldNames = useMemo(() => {
    if (!databases || filters.workspaces.length === 0) return [];
    
    const selectedDatabases = databases.filter(db => filters.workspaces.includes(db.database_id));
    const fieldNames = new Set<string>();
    
    selectedDatabases.forEach(db => {
      db.field_definitions?.forEach(field => {
        if (field.is_filterable && field.field_type !== 'date') {
          fieldNames.add(field.field_name);
        }
      });
    });
    
    return Array.from(fieldNames);
  }, [databases, filters.workspaces]);

  const {
    fields: aggregatedFieldData,
    loading: fieldsLoading
  } = useAggregatedFields(selectedDatabaseFieldNames);

  // Mobile detection
  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Update search query with debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      onFiltersChange({
        ...filters,
        searchQuery
      });
    }, 300);

    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery]); // Intentionally omitting filters and onFiltersChange to prevent infinite loops

  // Get available filter fields from selected databases
  const availableFilterFields = useMemo(() => {
    if (!databases || filters.workspaces.length === 0) return [];
    
    const selectedDatabases = databases.filter(db => filters.workspaces.includes(db.database_id));
    
    // Collect all unique fields from selected databases
    const fieldMap = new Map<string, DatabaseFieldDefinition>();
    
    selectedDatabases.forEach(db => {
      db.field_definitions?.forEach(field => {
        if (field.is_filterable) {
          // Convert FieldDefinition to DatabaseFieldDefinition
          const databaseFieldDef: DatabaseFieldDefinition = {
            ...field,
            description: field.description || field.notion_field || field.field_name
          };
          fieldMap.set(field.field_name, databaseFieldDef);
        }
      });
    });
    
    return Array.from(fieldMap.values());
  }, [databases, filters.workspaces]);

  // Update filter state
  const updateFilter = (key: keyof ChatFilter, value: any) => {
    onFiltersChange({
      ...filters,
      [key]: value
    });
  };

  const updateMetadataFilter = (fieldName: string, values: string[]) => {
    onFiltersChange({
      ...filters,
      metadataFilters: {
        ...filters.metadataFilters,
        [fieldName]: values
      }
    });
  };

  const toggleWorkspace = (workspaceId: string) => {
    const newWorkspaces = filters.workspaces.includes(workspaceId)
      ? filters.workspaces.filter(id => id !== workspaceId)
      : [...filters.workspaces, workspaceId];
    
    // Clear metadata filters when workspaces change
    onFiltersChange({
      ...filters,
      workspaces: newWorkspaces,
      metadataFilters: {}
    });
  };

  const selectAllWorkspaces = () => {
    onFiltersChange({
      ...filters,
      workspaces: databases?.map(db => db.database_id) || [],
      metadataFilters: {}
    });
  };

  const clearWorkspaces = () => {
    onFiltersChange({
      ...filters,
      workspaces: [],
      metadataFilters: {}
    });
  };

  const clearAllFilters = () => {
    setSearchQuery('');
    onFiltersChange({
      workspaces: [],
      dateRange: {},
      searchQuery: '',
      metadataFilters: {}
    });
  };

  // Calculate active filter count
  const getActiveFilterCount = () => {
    let count = 0;
    if (filters.workspaces.length > 0) count += filters.workspaces.length;
    if (filters.dateRange.from || filters.dateRange.to) count += 1;
    if (filters.searchQuery) count += 1;
    
    // Count metadata filters
    Object.values(filters.metadataFilters).forEach(values => {
      if (values.length > 0) count += values.length;
    });
    
    return count;
  };

  const activeFilterCount = getActiveFilterCount();
  const hasActiveFilters = activeFilterCount > 0;

  const getWorkspaceDisplayText = () => {
    if (filters.workspaces.length === 0) return "All Databases";
    if (filters.workspaces.length === 1) {
      const db = databases?.find(db => db.database_id === filters.workspaces[0]);
      return db?.database_name || "1 Database";
    }
    return `${filters.workspaces.length} Databases`;
  };

  // Create a function to get field options for a specific field
  const getFieldOptions = (fieldName: string): FieldFilterOptions | undefined => {
    const fieldData = aggregatedFieldData?.find(f => f.field_name === fieldName);
    const fieldDefinition = availableFilterFields.find(f => f.field_name === fieldName);
    
    if (!fieldData || !fieldDefinition) return undefined;
    
    return {
      field_name: fieldName,
      unique_values: fieldData.unique_values || [],
      value_counts: fieldData.value_counts || {},
      field_definition: fieldDefinition
    };
  };

  const isLoading = databasesLoading || fieldsLoading;
  const hasError = databasesError;

  return (
    <div className="border-b bg-muted/30 p-3 md:p-4 space-y-3">
      {/* Show loading state while fetching metadata */}
      {isLoading && !databases?.length ? (
        <div className="flex items-center justify-center gap-2 text-muted-foreground">
          <RefreshCw className="h-4 w-4 animate-spin" />
          <span>Loading metadata...</span>
        </div>
      ) : hasError && !databases?.length ? (
        <div className="flex items-center justify-center gap-2 text-red-600">
          <AlertCircle className="h-4 w-4" />
          <span>Failed to load metadata. Using fallback data.</span>
        </div>
      ) : (
        <>
          {/* Main Filter Bar */}
          <div className="flex flex-col md:flex-row gap-3 md:gap-4 md:items-center">
            {/* Database Selector */}
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant={filters.workspaces.length > 0 ? "default" : "outline"}
                  className="justify-between gap-2 md:min-w-[200px] h-10"
                  disabled={disabled}
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    {filters.workspaces.length === 0 ? (
                      <Globe className="h-4 w-4 flex-shrink-0" />
                    ) : (
                      <Database className="h-4 w-4 flex-shrink-0" />
                    )}
                    <span className="truncate">{getWorkspaceDisplayText()}</span>
                  </div>
                  <ChevronDown className="h-4 w-4 flex-shrink-0" />
                </Button>
              </PopoverTrigger>
              <PopoverContent align="start" className="w-80 p-0">
                <div className="p-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-medium">Select Databases</h3>
                    <div className="flex gap-2">
                      <Button variant="ghost" size="sm" onClick={selectAllWorkspaces}>
                        All
                      </Button>
                      <Button variant="ghost" size="sm" onClick={clearWorkspaces}>
                        None
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-3">
                    {/* All Databases Option */}
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="all-databases"
                        checked={filters.workspaces.length === 0}
                        onCheckedChange={(checked) => {
                          if (checked) clearWorkspaces();
                        }}
                      />
                      <label
                        htmlFor="all-databases"
                        className="flex-1 text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 min-w-0 flex-1">
                            <Globe className="h-4 w-4" />
                            <span>All Databases</span>
                          </div>
                          <Badge variant="outline" className="text-xs">
                            {databases?.reduce((sum, db) => sum + db.total_documents, 0) || 0} docs
                          </Badge>
                        </div>
                      </label>
                    </div>

                    <Separator />

                    {/* Individual Databases */}
                    {databases?.map(database => (
                      <div key={database.database_id} className="flex items-center space-x-2">
                        <Checkbox
                          id={database.database_id}
                          checked={filters.workspaces.includes(database.database_id)}
                          onCheckedChange={() => toggleWorkspace(database.database_id)}
                        />
                        <label
                          htmlFor={database.database_id}
                          className="flex-1 text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2 min-w-0 flex-1">
                              <Database className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                              <span className="truncate">{database.database_name}</span>
                            </div>
                            <Badge variant="outline" className="text-xs flex-shrink-0">
                              {database.total_documents} docs
                            </Badge>
                          </div>
                        </label>
                      </div>
                    ))}
                  </div>
                </div>
              </PopoverContent>
            </Popover>

            {!isMobile && <Separator orientation="vertical" className="h-6" />}

            {/* Search Input */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder={isMobile ? "Search..." : "Search within filtered content..."}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className={cn(
                  "pl-10 bg-background h-10",
                  filters.searchQuery && "border-primary bg-primary/5"
                )}
                disabled={disabled}
              />
            </div>

            {/* Filter Toggle */}
            <div className="flex gap-2">
              <Button
                variant={hasActiveFilters ? "default" : "outline"}
                size="sm"
                onClick={() => setIsExpanded(!isExpanded)}
                className="gap-2 shrink-0 h-10"
                disabled={disabled}
              >
                <Filter className="h-4 w-4" />
                {!isMobile && "Filters"}
                {activeFilterCount > 0 && (
                  <div className="flex items-center justify-center w-5 h-5 rounded-full bg-background text-foreground text-xs font-medium ml-1">
                    {activeFilterCount}
                  </div>
                )}
                <ChevronDown className={cn("h-4 w-4 transition-transform", isExpanded && "rotate-180")} />
              </Button>

              {/* Clear Filters */}
              {activeFilterCount > 0 && (
                <Button variant="ghost" size="sm" onClick={clearAllFilters} className="shrink-0 h-10" disabled={disabled}>
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>

          {/* Active Filters Display */}
          {activeFilterCount > 0 && (
            <div className="flex flex-wrap gap-2">
              {filters.workspaces.map(databaseId => {
                const database = databases?.find(db => db.database_id === databaseId);
                return database ? (
                  <Badge key={databaseId} variant="secondary" className="gap-1 text-xs">
                    <Database className="h-3 w-3" />
                    <span className="truncate max-w-[100px]">{database.database_name}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-4 w-4 p-0 hover:bg-transparent"
                      onClick={() => toggleWorkspace(databaseId)}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </Badge>
                ) : null;
              })}

              {/* Metadata Filter Badges */}
              {Object.entries(filters.metadataFilters).map(([fieldName, values]) => {
                const field = availableFilterFields.find(f => f.field_name === fieldName);
                return values.map((value, index) => (
                  <Badge key={`${fieldName}-${index}`} variant="secondary" className="gap-1 text-xs">
                    <span className="truncate max-w-[80px]">{field?.description || fieldName}</span>
                    <span className="truncate max-w-[60px]">: {value}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-4 w-4 p-0 hover:bg-transparent"
                      onClick={() => {
                        const newValues = values.filter(v => v !== value);
                        updateMetadataFilter(fieldName, newValues);
                      }}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </Badge>
                ));
              })}
            </div>
          )}

          {/* Expanded Filters - Dynamic sections based on selected databases */}
          {isExpanded && (
            <Card>
              <CardContent className="p-4">
                {availableFilterFields.length > 0 ? (
                  <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {availableFilterFields.map(field => (
                      <DynamicFilterSection
                        key={field.field_name}
                        fieldDefinition={field}
                        fieldOptions={getFieldOptions(field.field_name)}
                        selectedValues={filters.metadataFilters[field.field_name] || []}
                        onSelectionChange={updateMetadataFilter}
                        loading={isLoading}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <Filter className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No filters available</p>
                    <p className="text-xs">Select one or more databases to see available filter options</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}