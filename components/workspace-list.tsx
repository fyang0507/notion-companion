'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Book, Database, FileText, Folder, MoreHorizontal, FolderSync as Sync, Users } from 'lucide-react';
import { cn } from '@/lib/utils';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';

interface Workspace {
  id: string;
  name: string;
  type: 'page' | 'database' | 'workspace';
  documentCount: number;
  lastSync: string;
  status: 'active' | 'syncing' | 'error';
}

interface WorkspaceListProps {
  selectedWorkspace: string | null;
  onSelectWorkspace: (id: string) => void;
  onNewChat?: () => void;
}

export function WorkspaceList({ selectedWorkspace, onSelectWorkspace, onNewChat }: WorkspaceListProps) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([
    {
      id: 'ws-1',
      name: 'Product Documentation',
      type: 'workspace',
      documentCount: 156,
      lastSync: '2 minutes ago',
      status: 'active'
    },
    {
      id: 'ws-2', 
      name: 'Meeting Notes',
      type: 'database',
      documentCount: 43,
      lastSync: '5 minutes ago',
      status: 'active'
    },
    {
      id: 'ws-3',
      name: 'Project Roadmap',
      type: 'page',
      documentCount: 12,
      lastSync: '1 hour ago',
      status: 'syncing'
    }
  ]);

  const getIcon = (type: string) => {
    switch (type) {
      case 'workspace': return <Users className="h-4 w-4" />;
      case 'database': return <Database className="h-4 w-4" />;
      case 'page': return <FileText className="h-4 w-4" />;
      default: return <Folder className="h-4 w-4" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-500';
      case 'syncing': return 'bg-yellow-500 animate-pulse';
      case 'error': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const handleWorkspaceClick = (workspaceId: string) => {
    // If clicking on the same workspace and we're in a chat, start a new chat
    if (selectedWorkspace === workspaceId && onNewChat) {
      onNewChat();
    } else {
      // Otherwise, select the workspace (which will start a new chat in that workspace)
      onSelectWorkspace(workspaceId);
    }
  };

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-muted-foreground mb-3">Connected Workspaces</h3>
      
      <div className="space-y-1">
        {workspaces.map((workspace) => (
          <div
            key={workspace.id}
            className={cn(
              "group relative rounded-lg border p-3 hover:bg-accent cursor-pointer transition-colors",
              selectedWorkspace === workspace.id && "bg-accent border-primary"
            )}
            onClick={() => handleWorkspaceClick(workspace.id)}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3 flex-1 min-w-0">
                <div className="flex-shrink-0 mt-0.5">
                  {getIcon(workspace.type)}
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="font-medium text-sm truncate">{workspace.name}</p>
                    <div className={cn("w-2 h-2 rounded-full", getStatusColor(workspace.status))} />
                  </div>
                  
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span>{workspace.documentCount} docs</span>
                    <span>•</span>
                    <span>{workspace.lastSync}</span>
                  </div>
                </div>
              </div>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button 
                    variant="ghost" 
                    size="icon"
                    className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <MoreHorizontal className="h-3 w-3" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem>
                    <Sync className="mr-2 h-4 w-4" />
                    Force Sync
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <Book className="mr-2 h-4 w-4" />
                    View in Notion
                  </DropdownMenuItem>
                  <DropdownMenuItem className="text-red-600">
                    Disconnect
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}