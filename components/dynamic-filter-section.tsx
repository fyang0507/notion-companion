'use client';

import { useState, useMemo } from 'react';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Calendar, 
  User, 
  Tag, 
  FileText,
  CheckCircle2,
  Type,
  Hash,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  X,
  Search,
  SortAsc,
  SortDesc
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { DatabaseFieldDefinition, FieldFilterOptions } from '@/types/chat';

interface DynamicFilterSectionProps {
  fieldDefinition: DatabaseFieldDefinition;
  fieldOptions?: FieldFilterOptions;
  selectedValues: string[];
  onSelectionChange: (fieldName: string, values: string[]) => void;
  loading?: boolean;
}

// Map field types to appropriate icons
const getFieldIcon = (fieldType: string) => {
  switch (fieldType) {
    case 'text': return Type;
    case 'date': return Calendar;
    case 'status': return CheckCircle2;
    case 'select': return FileText;
    case 'multi_select': return Tag;
    case 'number': return Hash;
    case 'checkbox': return CheckCircle2;
    default: return FileText;
  }
};

// Map field types to colors for better visual distinction
const getFieldColor = (fieldType: string) => {
  switch (fieldType) {
    case 'text': return 'text-blue-600';
    case 'date': return 'text-green-600';
    case 'status': return 'text-purple-600';
    case 'select': return 'text-orange-600';
    case 'multi_select': return 'text-pink-600';
    case 'number': return 'text-indigo-600';
    case 'checkbox': return 'text-emerald-600';
    default: return 'text-gray-600';
  }
};

// Sort options for different field types
const getSortOptions = (fieldType: string) => {
  switch (fieldType) {
    case 'number':
      return [
        { value: 'value_asc', label: 'Value (Low to High)' },
        { value: 'value_desc', label: 'Value (High to Low)' },
        { value: 'count_desc', label: 'Most Common' },
        { value: 'count_asc', label: 'Least Common' }
      ];
    case 'date':
      return [
        { value: 'value_asc', label: 'Date (Oldest First)' },
        { value: 'value_desc', label: 'Date (Newest First)' },
        { value: 'count_desc', label: 'Most Common' },
        { value: 'count_asc', label: 'Least Common' }
      ];
    default:
      return [
        { value: 'alpha_asc', label: 'Alphabetical (A-Z)' },
        { value: 'alpha_desc', label: 'Alphabetical (Z-A)' },
        { value: 'count_desc', label: 'Most Common' },
        { value: 'count_asc', label: 'Least Common' }
      ];
  }
};

export function DynamicFilterSection({
  fieldDefinition,
  fieldOptions,
  selectedValues,
  onSelectionChange,
  loading = false
}: DynamicFilterSectionProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [numberMin, setNumberMin] = useState('');
  const [numberMax, setNumberMax] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('count_desc');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [showAllSelected, setShowAllSelected] = useState(false);
  
  const IconComponent = getFieldIcon(fieldDefinition.field_type);
  const colorClass = getFieldColor(fieldDefinition.field_type);
  const sortOptions = getSortOptions(fieldDefinition.field_type);

  const toggleValue = (value: string) => {
    const newValues = selectedValues.includes(value)
      ? selectedValues.filter(v => v !== value)
      : [...selectedValues, value];
    onSelectionChange(fieldDefinition.field_name, newValues);
  };

  const handleDateRangeChange = () => {
    const values = [];
    if (dateFrom) values.push(`from:${dateFrom}`);
    if (dateTo) values.push(`to:${dateTo}`);
    onSelectionChange(fieldDefinition.field_name, values);
  };

  const handleNumberRangeChange = () => {
    const values = [];
    if (numberMin) values.push(`min:${numberMin}`);
    if (numberMax) values.push(`max:${numberMax}`);
    onSelectionChange(fieldDefinition.field_name, values);
  };

  // Process and filter available options
  const processedOptions = useMemo(() => {
    const availableOptions = fieldOptions?.unique_values || fieldDefinition.sample_values || [];
    
    // Filter by search term
    let filtered = availableOptions.filter(option => {
      const stringValue = String(option).toLowerCase();
      return stringValue.includes(searchTerm.toLowerCase());
    });

    // Sort options
    filtered = [...filtered].sort((a, b) => {
      const aStr = String(a);
      const bStr = String(b);
      const aCount = fieldOptions?.value_counts[aStr] || 0;
      const bCount = fieldOptions?.value_counts[bStr] || 0;

      switch (sortBy) {
        case 'alpha_asc':
          return aStr.localeCompare(bStr);
        case 'alpha_desc':
          return bStr.localeCompare(aStr);
        case 'count_desc':
          return bCount - aCount;
        case 'count_asc':
          return aCount - bCount;
        case 'value_asc':
          if (fieldDefinition.field_type === 'number') {
            return Number(a) - Number(b);
          } else if (fieldDefinition.field_type === 'date') {
            return new Date(aStr).getTime() - new Date(bStr).getTime();
          }
          return aStr.localeCompare(bStr);
        case 'value_desc':
          if (fieldDefinition.field_type === 'number') {
            return Number(b) - Number(a);
          } else if (fieldDefinition.field_type === 'date') {
            return new Date(bStr).getTime() - new Date(aStr).getTime();
          }
          return bStr.localeCompare(aStr);
        default:
          return 0;
      }
    });

    return filtered;
  }, [fieldOptions, fieldDefinition, searchTerm, sortBy]);

  // Handle pagination
  const totalPages = Math.ceil(processedOptions.length / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const paginatedOptions = processedOptions.slice(startIndex, startIndex + pageSize);

  // Selected values that might not be in current page
  const selectedValuesInCurrentData = selectedValues.filter(value => 
    processedOptions.some(option => String(option) === value)
  );

  const selectedValuesNotInCurrentPage = selectedValues.filter(value => 
    !paginatedOptions.some(option => String(option) === value)
  );

  // For date fields, render date inputs
  if (fieldDefinition.field_type === 'date') {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="font-medium text-sm flex items-center gap-2">
            <IconComponent className={cn("h-4 w-4", colorClass)} />
            {fieldDefinition.description || fieldDefinition.notion_field}
          </h4>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="h-6 w-6 p-0"
          >
            <ChevronDown className={cn("h-3 w-3 transition-transform", !isExpanded && "-rotate-90")} />
          </Button>
        </div>
        
        {isExpanded && (
          <div className="space-y-2">
            <div className="flex gap-2">
              <Input
                type="date"
                placeholder="From"
                value={dateFrom}
                onChange={(e) => {
                  setDateFrom(e.target.value);
                  setTimeout(handleDateRangeChange, 100);
                }}
                className="flex-1 text-sm"
              />
              <Input
                type="date"
                placeholder="To"
                value={dateTo}
                onChange={(e) => {
                  setDateTo(e.target.value);
                  setTimeout(handleDateRangeChange, 100);
                }}
                className="flex-1 text-sm"
              />
            </div>
            {(dateFrom || dateTo) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setDateFrom('');
                  setDateTo('');
                  onSelectionChange(fieldDefinition.field_name, []);
                }}
                className="h-6 text-xs text-muted-foreground"
              >
                <X className="h-3 w-3 mr-1" />
                Clear date range
              </Button>
            )}
          </div>
        )}
      </div>
    );
  }

  // For number fields, render min/max inputs
  if (fieldDefinition.field_type === 'number') {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="font-medium text-sm flex items-center gap-2">
            <IconComponent className={cn("h-4 w-4", colorClass)} />
            {fieldDefinition.description || fieldDefinition.notion_field}
          </h4>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="h-6 w-6 p-0"
          >
            <ChevronDown className={cn("h-3 w-3 transition-transform", !isExpanded && "-rotate-90")} />
          </Button>
        </div>
        
        {isExpanded && (
          <div className="space-y-2">
            <div className="flex gap-2">
              <Input
                type="number"
                placeholder="Min"
                value={numberMin}
                onChange={(e) => {
                  setNumberMin(e.target.value);
                  setTimeout(handleNumberRangeChange, 100);
                }}
                className="flex-1 text-sm"
              />
              <Input
                type="number"
                placeholder="Max"
                value={numberMax}
                onChange={(e) => {
                  setNumberMax(e.target.value);
                  setTimeout(handleNumberRangeChange, 100);
                }}
                className="flex-1 text-sm"
              />
            </div>
            {(numberMin || numberMax) && (
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setNumberMin('');
                    setNumberMax('');
                    onSelectionChange(fieldDefinition.field_name, []);
                  }}
                  className="h-6 text-xs text-muted-foreground"
                >
                  <X className="h-3 w-3 mr-1" />
                  Clear range
                </Button>
                {(numberMin || numberMax) && (
                  <div className="text-xs text-muted-foreground">
                    Range: {numberMin || '∞'} to {numberMax || '∞'}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  // For checkbox fields, render simple toggle
  if (fieldDefinition.field_type === 'checkbox') {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="font-medium text-sm flex items-center gap-2">
            <IconComponent className={cn("h-4 w-4", colorClass)} />
            {fieldDefinition.description || fieldDefinition.notion_field}
          </h4>
        </div>
        
        <div className="flex items-center space-x-2">
          <Checkbox
            id={fieldDefinition.field_name}
            checked={selectedValues.includes('true')}
            onCheckedChange={(checked) => {
              onSelectionChange(fieldDefinition.field_name, checked ? ['true'] : []);
            }}
          />
          <label
            htmlFor={fieldDefinition.field_name}
            className="text-sm leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
          >
            Enabled
          </label>
        </div>
      </div>
    );
  }

  // For other field types, render enhanced options list
  const availableOptions = fieldOptions?.unique_values || fieldDefinition.sample_values || [];
  
  if (availableOptions.length === 0 && !loading) {
    return (
      <div className="space-y-3">
        <h4 className="font-medium text-sm flex items-center gap-2 text-muted-foreground">
          <IconComponent className={cn("h-4 w-4", colorClass)} />
          {fieldDefinition.description || fieldDefinition.notion_field}
        </h4>
        <p className="text-xs text-muted-foreground">No options available</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-sm flex items-center gap-2">
          <IconComponent className={cn("h-4 w-4", colorClass)} />
          {fieldDefinition.description || fieldDefinition.notion_field}
        </h4>
        <div className="flex items-center gap-2">
          {selectedValues.length > 0 && (
            <Badge variant="secondary" className="text-xs">
              {selectedValues.length} selected
            </Badge>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="h-6 w-6 p-0"
          >
            <ChevronDown className={cn("h-3 w-3 transition-transform", !isExpanded && "-rotate-90")} />
          </Button>
        </div>
      </div>
      
      {isExpanded && (
        <div className="space-y-3">
          {/* Search and Controls */}
          {availableOptions.length > 10 && (
            <div className="space-y-2">
              {/* Search Input */}
              <div className="relative">
                <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 h-3 w-3 text-muted-foreground" />
                <Input
                  placeholder={`Search ${fieldDefinition.description || fieldDefinition.notion_field}...`}
                  value={searchTerm}
                  onChange={(e) => {
                    setSearchTerm(e.target.value);
                    setCurrentPage(1); // Reset to first page on search
                  }}
                  className="pl-7 h-8 text-sm"
                />
              </div>

              {/* Sort and Page Size Controls */}
              <div className="flex items-center gap-2 text-xs">
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="text-xs border rounded px-2 py-1 bg-background"
                >
                  {sortOptions.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="text-xs border rounded px-2 py-1 bg-background"
                >
                  <option value={10}>10 per page</option>
                  <option value={20}>20 per page</option>
                  <option value={50}>50 per page</option>
                  <option value={100}>100 per page</option>
                </select>
              </div>

              {/* Results summary */}
              <div className="text-xs text-muted-foreground">
                {searchTerm ? (
                  <>Showing {processedOptions.length} of {availableOptions.length} options</>
                ) : (
                  <>Showing {availableOptions.length} options</>
                )}
              </div>
            </div>
          )}

          {/* Selected values not in current page */}
          {selectedValuesNotInCurrentPage.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs text-muted-foreground flex items-center gap-2">
                <Badge variant="outline" className="text-xs">
                  {selectedValuesNotInCurrentPage.length} selected items not shown
                </Badge>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowAllSelected(!showAllSelected)}
                  className="h-5 text-xs"
                >
                  {showAllSelected ? 'Hide' : 'Show'}
                </Button>
              </div>
              
              {showAllSelected && (
                <div className="space-y-1 p-2 bg-muted/50 rounded-md">
                  {selectedValuesNotInCurrentPage.map((value, index) => (
                    <div key={`selected-${index}`} className="flex items-center space-x-2">
                      <Checkbox
                        id={`selected-${fieldDefinition.field_name}-${index}`}
                        checked={true}
                        onCheckedChange={() => toggleValue(value)}
                      />
                      <label
                        htmlFor={`selected-${fieldDefinition.field_name}-${index}`}
                        className="flex-1 text-sm leading-none cursor-pointer"
                      >
                        <div className="flex items-center justify-between">
                          <span className="truncate">{value}</span>
                          <Badge variant="outline" className="text-xs ml-2">
                            {fieldOptions?.value_counts[value] || 0}
                          </Badge>
                        </div>
                      </label>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Options List */}
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {loading ? (
              <div className="space-y-2">
                {Array.from({ length: pageSize }).map((_, i) => (
                  <div key={i} className="flex items-center space-x-2">
                    <div className="h-4 w-4 bg-muted animate-pulse rounded" />
                    <div className="h-4 flex-1 bg-muted animate-pulse rounded" />
                  </div>
                ))}
              </div>
            ) : processedOptions.length === 0 ? (
              <div className="text-center py-4 text-muted-foreground text-sm">
                {searchTerm ? 'No options match your search' : 'No options available'}
              </div>
            ) : (
              <>
                {paginatedOptions.map((value, index) => {
                  const stringValue = String(value);
                  const count = fieldOptions?.value_counts[stringValue] || 0;
                  const globalIndex = startIndex + index;
                  
                  return (
                    <div key={`${fieldDefinition.field_name}-${globalIndex}`} className="flex items-center space-x-2">
                      <Checkbox
                        id={`${fieldDefinition.field_name}-${globalIndex}`}
                        checked={selectedValues.includes(stringValue)}
                        onCheckedChange={() => toggleValue(stringValue)}
                      />
                      <label
                        htmlFor={`${fieldDefinition.field_name}-${globalIndex}`}
                        className="flex-1 text-sm leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                      >
                        <div className="flex items-center justify-between">
                          <span className="truncate">{stringValue}</span>
                          {count > 0 && (
                            <Badge variant="outline" className="text-xs ml-2">
                              {count}
                            </Badge>
                          )}
                        </div>
                      </label>
                    </div>
                  );
                })}
              </>
            )}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-2">
              <div className="text-xs text-muted-foreground">
                Page {currentPage} of {totalPages}
              </div>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                  className="h-6 w-6 p-0"
                >
                  <ChevronLeft className="h-3 w-3" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                  disabled={currentPage === totalPages}
                  className="h-6 w-6 p-0"
                >
                  <ChevronRight className="h-3 w-3" />
                </Button>
              </div>
            </div>
          )}

          {/* Clear selections */}
          {selectedValues.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onSelectionChange(fieldDefinition.field_name, [])}
              className="h-6 text-xs text-muted-foreground w-full justify-start"
            >
              <X className="h-3 w-3 mr-1" />
              Clear all selections ({selectedValues.length})
            </Button>
          )}
        </div>
      )}
    </div>
  );
} 