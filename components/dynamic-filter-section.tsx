'use client';

import { useState } from 'react';
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
  X
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
    default: return 'text-gray-600';
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
  
  const IconComponent = getFieldIcon(fieldDefinition.field_type);
  const colorClass = getFieldColor(fieldDefinition.field_type);

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
                  // Auto-apply on change
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
                  // Auto-apply on change
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

  // For other field types, render checkbox options
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
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3].map(i => (
                <div key={i} className="flex items-center space-x-2">
                  <div className="h-4 w-4 bg-muted animate-pulse rounded" />
                  <div className="h-4 flex-1 bg-muted animate-pulse rounded" />
                </div>
              ))}
            </div>
          ) : (
            <>
              {availableOptions.map((value, index) => {
                const stringValue = String(value);
                const count = fieldOptions?.value_counts[stringValue] || 0;
                
                return (
                  <div key={`${fieldDefinition.field_name}-${index}`} className="flex items-center space-x-2">
                    <Checkbox
                      id={`${fieldDefinition.field_name}-${index}`}
                      checked={selectedValues.includes(stringValue)}
                      onCheckedChange={() => toggleValue(stringValue)}
                    />
                    <label
                      htmlFor={`${fieldDefinition.field_name}-${index}`}
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
              
              {selectedValues.length > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onSelectionChange(fieldDefinition.field_name, [])}
                  className="h-6 text-xs text-muted-foreground w-full justify-start"
                >
                  <X className="h-3 w-3 mr-1" />
                  Clear all selections
                </Button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
} 