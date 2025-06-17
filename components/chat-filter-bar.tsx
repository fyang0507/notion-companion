'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Checkbox } from '@/components/ui/checkbox';
import { 
  Filter, 
  X, 
  Search, 
  Database, 
  FileText, 
  Calendar,
  User,
  Tag,
  Globe,
  ChevronDown,
  Check
} from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ChatFilter {
  workspaces: string[];
  documentTypes: string[];
  dateRange: {
    from?: Date;
    to?: Date;
  };
  authors: string[];
  tags: string[];
  searchQuery: string;
}

interface WorkspaceMetadata {
  documentTypes: Array<{ id: string; name: string; count: number }>;
  authors: Array<{ id: string; name: string; count: number }>;
  tags: Array<{ id: string; name: string; color: string; count: number }>;
  dateRange: { earliest: Date; latest: Date };
}

interface ChatFilterBarProps {
  filters: ChatFilter;
  onFiltersChange: (filters: ChatFilter) => void;
  availableWorkspaces: Array<{
    id: string;
    name: string;
    documentCount: number;
    metadata?: WorkspaceMetadata;
  }>;
}

export function ChatFilterBar({ filters, onFiltersChange, availableWorkspaces }: ChatFilterBarProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [searchQuery, setSearchQuery] = useState(filters.searchQuery || '');
  const [workspaceSelectOpen, setWorkspaceSelectOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Check if mobile
  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Mock metadata for demo - in real app this would come from the database
  const getMockMetadata = (workspaceId: string): WorkspaceMetadata => {
    const metadataMap: Record<string, WorkspaceMetadata> = {
      'ws-1': {
        documentTypes: [
          { id: 'page', name: 'Pages', count: 89 },
          { id: 'database', name: 'Databases', count: 34 },
          { id: 'template', name: 'Templates', count: 23 },
          { id: 'wiki', name: 'Wiki Pages', count: 10 }
        ],
        authors: [
          { id: 'john', name: 'John Smith', count: 67 },
          { id: 'sarah', name: 'Sarah Johnson', count: 45 },
          { id: 'mike', name: 'Mike Chen', count: 32 },
          { id: 'emma', name: 'Emma Davis', count: 12 }
        ],
        tags: [
          { id: 'api', name: 'API', color: 'text-blue-600', count: 45 },
          { id: 'docs', name: 'Documentation', color: 'text-green-600', count: 78 },
          { id: 'guide', name: 'Guide', color: 'text-purple-600', count: 23 },
          { id: 'reference', name: 'Reference', color: 'text-orange-600', count: 10 }
        ],
        dateRange: { earliest: new Date('2023-01-01'), latest: new Date() }
      },
      'ws-2': {
        documentTypes: [
          { id: 'meeting', name: 'Meeting Notes', count: 28 },
          { id: 'action', name: 'Action Items', count: 15 }
        ],
        authors: [
          { id: 'alex', name: 'Alex Wilson', count: 25 },
          { id: 'lisa', name: 'Lisa Brown', count: 18 }
        ],
        tags: [
          { id: 'urgent', name: 'Urgent', color: 'text-red-600', count: 12 },
          { id: 'followup', name: 'Follow-up', color: 'text-yellow-600', count: 31 }
        ],
        dateRange: { earliest: new Date('2023-06-01'), latest: new Date() }
      },
      'ws-3': {
        documentTypes: [
          { id: 'roadmap', name: 'Roadmap Items', count: 8 },
          { id: 'milestone', name: 'Milestones', count: 4 }
        ],
        authors: [
          { id: 'david', name: 'David Kim', count: 12 }
        ],
        tags: [
          { id: 'q4', name: 'Q4 2024', color: 'text-indigo-600', count: 8 },
          { id: 'feature', name: 'Feature', color: 'text-cyan-600', count: 4 }
        ],
        dateRange: { earliest: new Date('2023-09-01'), latest: new Date() }
      }
    };

    return metadataMap[workspaceId] || {
      documentTypes: [],
      authors: [],
      tags: [],
      dateRange: { earliest: new Date(), latest: new Date() }
    };
  };

  // Update search query with debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      onFiltersChange({
        ...filters,
        searchQuery
      });
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  const updateFilter = (key: keyof ChatFilter, value: any) => {
    onFiltersChange({
      ...filters,
      [key]: value
    });
  };

  const toggleWorkspace = (workspaceId: string) => {
    const newWorkspaces = filters.workspaces.includes(workspaceId)
      ? filters.workspaces.filter(id => id !== workspaceId)
      : [...filters.workspaces, workspaceId];
    
    // Clear dependent filters when workspaces change
    onFiltersChange({
      ...filters,
      workspaces: newWorkspaces,
      documentTypes: [],
      authors: [],
      tags: []
    });
  };

  const selectAllWorkspaces = () => {
    onFiltersChange({
      ...filters,
      workspaces: availableWorkspaces.map(w => w.id),
      documentTypes: [],
      authors: [],
      tags: []
    });
  };

  const clearWorkspaces = () => {
    onFiltersChange({
      ...filters,
      workspaces: [],
      documentTypes: [],
      authors: [],
      tags: []
    });
  };

  const toggleDocumentType = (typeId: string) => {
    const newTypes = filters.documentTypes.includes(typeId)
      ? filters.documentTypes.filter(id => id !== typeId)
      : [...filters.documentTypes, typeId];
    updateFilter('documentTypes', newTypes);
  };

  const toggleAuthor = (authorId: string) => {
    const newAuthors = filters.authors.includes(authorId)
      ? filters.authors.filter(id => id !== authorId)
      : [...filters.authors, authorId];
    updateFilter('authors', newAuthors);
  };

  const toggleTag = (tagId: string) => {
    const newTags = filters.tags.includes(tagId)
      ? filters.tags.filter(id => id !== tagId)
      : [...filters.tags, tagId];
    updateFilter('tags', newTags);
  };

  const clearAllFilters = () => {
    setSearchQuery('');
    onFiltersChange({
      workspaces: [],
      documentTypes: [],
      dateRange: {},
      authors: [],
      tags: [],
      searchQuery: ''
    });
  };

  // Get aggregated metadata from selected workspaces
  const getAggregatedMetadata = (): WorkspaceMetadata => {
    const selectedWorkspaces = filters.workspaces.length > 0 
      ? filters.workspaces
      : availableWorkspaces.map(w => w.id); // If no workspaces selected, use all

    const aggregated: WorkspaceMetadata = {
      documentTypes: [],
      authors: [],
      tags: [],
      dateRange: { earliest: new Date(), latest: new Date() }
    };

    // Aggregate document types
    const typeMap = new Map<string, { name: string; count: number }>();
    selectedWorkspaces.forEach(workspaceId => {
      const metadata = getMockMetadata(workspaceId);
      metadata.documentTypes.forEach(type => {
        const existing = typeMap.get(type.id);
        typeMap.set(type.id, {
          name: type.name,
          count: (existing?.count || 0) + type.count
        });
      });
    });
    aggregated.documentTypes = Array.from(typeMap.entries()).map(([id, data]) => ({
      id,
      name: data.name,
      count: data.count
    }));

    // Aggregate authors
    const authorMap = new Map<string, { name: string; count: number }>();
    selectedWorkspaces.forEach(workspaceId => {
      const metadata = getMockMetadata(workspaceId);
      metadata.authors.forEach(author => {
        const existing = authorMap.get(author.id);
        authorMap.set(author.id, {
          name: author.name,
          count: (existing?.count || 0) + author.count
        });
      });
    });
    aggregated.authors = Array.from(authorMap.entries()).map(([id, data]) => ({
      id,
      name: data.name,
      count: data.count
    }));

    // Aggregate tags
    const tagMap = new Map<string, { name: string; color: string; count: number }>();
    selectedWorkspaces.forEach(workspaceId => {
      const metadata = getMockMetadata(workspaceId);
      metadata.tags.forEach(tag => {
        const existing = tagMap.get(tag.id);
        tagMap.set(tag.id, {
          name: tag.name,
          color: tag.color,
          count: (existing?.count || 0) + tag.count
        });
      });
    });
    aggregated.tags = Array.from(tagMap.entries()).map(([id, data]) => ({
      id,
      name: data.name,
      color: data.color,
      count: data.count
    }));

    return aggregated;
  };

  const getActiveFilterCount = () => {
    return filters.workspaces.length + 
           filters.documentTypes.length + 
           filters.authors.length + 
           filters.tags.length +
           (filters.searchQuery ? 1 : 0) +
           (filters.dateRange.from || filters.dateRange.to ? 1 : 0);
  };

  const activeFilterCount = getActiveFilterCount();
  const isGlobalMode = filters.workspaces.length === 0;
  const aggregatedMetadata = getAggregatedMetadata();

  const getWorkspaceDisplayText = () => {
    if (isGlobalMode) return 'All Content';
    if (filters.workspaces.length === 1) {
      const workspace = availableWorkspaces.find(w => w.id === filters.workspaces[0]);
      return workspace?.name || 'Unknown Workspace';
    }
    return `${filters.workspaces.length} Workspaces`;
  };

  // Determine if filters are active (excluding workspace selection)
  const hasActiveFilters = activeFilterCount > 0;

  return (
    <div className="border-b bg-muted/30 p-3 md:p-4 space-y-3">
      {/* Main Filter Bar */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center gap-3">
        {/* Workspace Selector */}
        <Popover open={workspaceSelectOpen} onOpenChange={setWorkspaceSelectOpen}>
          <PopoverTrigger asChild>
            <Button 
              variant="outline" 
              className={cn(
                "gap-2 justify-between h-10 md:min-w-[200px]",
                filters.workspaces.length > 0 && "border-primary bg-primary/5"
              )}
            >
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <Globe className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                <span className="text-sm font-medium truncate">{getWorkspaceDisplayText()}</span>
                {filters.workspaces.length > 0 && (
                  <Badge variant="secondary" className="h-5 px-1.5 text-xs flex-shrink-0">
                    {filters.workspaces.length}
                  </Badge>
                )}
              </div>
              <ChevronDown className="h-4 w-4 flex-shrink-0" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-80" align="start">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="font-medium">Select Workspaces</h4>
                <div className="flex gap-2">
                  <Button variant="ghost" size="sm" onClick={selectAllWorkspaces}>
                    Select All
                  </Button>
                  <Button variant="ghost" size="sm" onClick={clearWorkspaces}>
                    Clear
                  </Button>
                </div>
              </div>
              
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {/* All Workspaces Option */}
                <div className="flex items-center space-x-2 p-2 rounded-lg border bg-muted/50">
                  <Checkbox
                    id="all-workspaces"
                    checked={isGlobalMode}
                    onCheckedChange={() => clearWorkspaces()}
                  />
                  <label
                    htmlFor="all-workspaces"
                    className="flex-1 text-sm font-medium leading-none cursor-pointer"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Globe className="h-4 w-4" />
                        <span>All Content</span>
                      </div>
                      <Badge variant="outline" className="text-xs">
                        {availableWorkspaces.reduce((sum, w) => sum + w.documentCount, 0)} docs
                      </Badge>
                    </div>
                  </label>
                </div>

                <Separator />

                {/* Individual Workspaces */}
                {availableWorkspaces.map(workspace => (
                  <div key={workspace.id} className="flex items-center space-x-2">
                    <Checkbox
                      id={workspace.id}
                      checked={filters.workspaces.includes(workspace.id)}
                      onCheckedChange={() => toggleWorkspace(workspace.id)}
                    />
                    <label
                      htmlFor={workspace.id}
                      className="flex-1 text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 min-w-0 flex-1">
                          <Database className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                          <span className="truncate">{workspace.name}</span>
                        </div>
                        <Badge variant="outline" className="text-xs flex-shrink-0">
                          {workspace.documentCount} docs
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
          />
        </div>

        {/* Filter Toggle */}
        <div className="flex gap-2">
          <Button
            variant={hasActiveFilters ? "default" : "outline"}
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="gap-2 shrink-0 h-10"
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
            <Button variant="ghost" size="sm" onClick={clearAllFilters} className="shrink-0 h-10">
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Active Filters Display */}
      {activeFilterCount > 0 && (
        <div className="flex flex-wrap gap-2">
          {filters.workspaces.map(workspaceId => {
            const workspace = availableWorkspaces.find(w => w.id === workspaceId);
            return workspace ? (
              <Badge key={workspaceId} variant="secondary" className="gap-1 text-xs">
                <Database className="h-3 w-3" />
                <span className="truncate max-w-[100px]">{workspace.name}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-4 w-4 p-0 hover:bg-transparent"
                  onClick={() => toggleWorkspace(workspaceId)}
                >
                  <X className="h-3 w-3" />
                </Button>
              </Badge>
            ) : null;
          })}

          {filters.documentTypes.map(typeId => {
            const type = aggregatedMetadata.documentTypes.find(t => t.id === typeId);
            return type ? (
              <Badge key={typeId} variant="secondary" className="gap-1 text-xs">
                <FileText className="h-3 w-3" />
                {type.name}
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-4 w-4 p-0 hover:bg-transparent"
                  onClick={() => toggleDocumentType(typeId)}
                >
                  <X className="h-3 w-3" />
                </Button>
              </Badge>
            ) : null;
          })}

          {filters.authors.map(authorId => {
            const author = aggregatedMetadata.authors.find(a => a.id === authorId);
            return author ? (
              <Badge key={authorId} variant="secondary" className="gap-1 text-xs">
                <User className="h-3 w-3" />
                {author.name}
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-4 w-4 p-0 hover:bg-transparent"
                  onClick={() => toggleAuthor(authorId)}
                >
                  <X className="h-3 w-3" />
                </Button>
              </Badge>
            ) : null;
          })}

          {filters.tags.map(tagId => {
            const tag = aggregatedMetadata.tags.find(t => t.id === tagId);
            return tag ? (
              <Badge key={tagId} variant="secondary" className="gap-1 text-xs">
                <Tag className="h-3 w-3" />
                {tag.name}
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-4 w-4 p-0 hover:bg-transparent"
                  onClick={() => toggleTag(tagId)}
                >
                  <X className="h-3 w-3" />
                </Button>
              </Badge>
            ) : null;
          })}
        </div>
      )}

      {/* Expanded Filters - Dynamically populated based on selected workspaces */}
      {isExpanded && (
        <Card>
          <CardContent className="p-4">
            {(aggregatedMetadata.documentTypes.length > 0 || 
              aggregatedMetadata.authors.length > 0 || 
              aggregatedMetadata.tags.length > 0) ? (
              <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {/* Document Types */}
                {aggregatedMetadata.documentTypes.length > 0 && (
                  <div className="space-y-3">
                    <h4 className="font-medium text-sm flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      Document Types
                    </h4>
                    <div className="space-y-2">
                      {aggregatedMetadata.documentTypes.map(type => (
                        <div key={type.id} className="flex items-center space-x-2">
                          <Checkbox
                            id={`type-${type.id}`}
                            checked={filters.documentTypes.includes(type.id)}
                            onCheckedChange={() => toggleDocumentType(type.id)}
                          />
                          <label
                            htmlFor={`type-${type.id}`}
                            className="flex-1 text-sm leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                          >
                            <div className="flex items-center justify-between">
                              <span>{type.name}</span>
                              <Badge variant="outline" className="text-xs">
                                {type.count}
                              </Badge>
                            </div>
                          </label>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Authors */}
                {aggregatedMetadata.authors.length > 0 && (
                  <div className="space-y-3">
                    <h4 className="font-medium text-sm flex items-center gap-2">
                      <User className="h-4 w-4" />
                      Authors
                    </h4>
                    <div className="space-y-2">
                      {aggregatedMetadata.authors.map(author => (
                        <div key={author.id} className="flex items-center space-x-2">
                          <Checkbox
                            id={`author-${author.id}`}
                            checked={filters.authors.includes(author.id)}
                            onCheckedChange={() => toggleAuthor(author.id)}
                          />
                          <label
                            htmlFor={`author-${author.id}`}
                            className="flex-1 text-sm leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                          >
                            <div className="flex items-center justify-between">
                              <span>{author.name}</span>
                              <Badge variant="outline" className="text-xs">
                                {author.count}
                              </Badge>
                            </div>
                          </label>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Tags */}
                {aggregatedMetadata.tags.length > 0 && (
                  <div className="space-y-3">
                    <h4 className="font-medium text-sm flex items-center gap-2">
                      <Tag className="h-4 w-4" />
                      Tags
                    </h4>
                    <div className="space-y-2">
                      {aggregatedMetadata.tags.map(tag => (
                        <div key={tag.id} className="flex items-center space-x-2">
                          <Checkbox
                            id={`tag-${tag.id}`}
                            checked={filters.tags.includes(tag.id)}
                            onCheckedChange={() => toggleTag(tag.id)}
                          />
                          <label
                            htmlFor={`tag-${tag.id}`}
                            className="flex-1 text-sm leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                          >
                            <div className="flex items-center justify-between">
                              <Badge variant="outline" className={cn("text-xs", tag.color)}>
                                {tag.name}
                              </Badge>
                              <span className="text-xs text-muted-foreground">{tag.count}</span>
                            </div>
                          </label>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <Filter className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No additional filters available</p>
                <p className="text-xs">Select specific workspaces to see available filter options</p>
              </div>
            )}

            {/* Date Range - Always available when filters are present */}
            {(aggregatedMetadata.documentTypes.length > 0 || 
              aggregatedMetadata.authors.length > 0 || 
              aggregatedMetadata.tags.length > 0) && (
              <>
                <Separator className="my-4" />
                <div className="space-y-3">
                  <h4 className="font-medium text-sm flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    Date Range
                  </h4>
                  <div className="flex gap-2">
                    <Input
                      type="date"
                      placeholder="From"
                      value={filters.dateRange.from?.toISOString().split('T')[0] || ''}
                      onChange={(e) => updateFilter('dateRange', {
                        ...filters.dateRange,
                        from: e.target.value ? new Date(e.target.value) : undefined
                      })}
                      className="flex-1"
                    />
                    <Input
                      type="date"
                      placeholder="To"
                      value={filters.dateRange.to?.toISOString().split('T')[0] || ''}
                      onChange={(e) => updateFilter('dateRange', {
                        ...filters.dateRange,
                        to: e.target.value ? new Date(e.target.value) : undefined
                      })}
                      className="flex-1"
                    />
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}