'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { 
  Plus, 
  Book, 
  Clock, 
  Settings,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  Zap,
  MessageSquarePlus,
  BarChart3
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { WorkspaceList } from '@/components/workspace-list';
import { RecentChats } from '@/components/recent-chats';
import Link from 'next/link';

interface SidebarProps {
  selectedWorkspace: string | 'global' | null;
  onSelectWorkspace: (id: string) => void;
  onNewChat?: () => void;
  onStartGlobalChat?: () => void;
}

export function Sidebar({ selectedWorkspace, onSelectWorkspace, onNewChat, onStartGlobalChat }: SidebarProps) {
  const [syncStatus, setSyncStatus] = useState<'idle' | 'syncing' | 'success' | 'error'>('idle');

  const handleSync = async () => {
    setSyncStatus('syncing');
    // Simulate sync process
    setTimeout(() => {
      setSyncStatus('success');
      setTimeout(() => setSyncStatus('idle'), 2000);
    }, 2000);
  };

  const handleWorkspaceSelect = (workspaceId: string) => {
    // When selecting a workspace, always start a new chat in that workspace
    onSelectWorkspace(workspaceId);
    if (onNewChat) {
      onNewChat();
    }
  };

  const handleStartChat = () => {
    if (onStartGlobalChat) {
      onStartGlobalChat();
    }
  };

  const handleChatSelect = (chatId: string, workspaceId?: string) => {
    // If the chat has a workspace, select that workspace first
    if (workspaceId) {
      onSelectWorkspace(workspaceId);
    }
    
    // In a real app, you would load the specific chat history here
    // For now, we'll just start a new chat in the workspace
    if (onNewChat) {
      onNewChat();
    }
  };

  return (
    <div className="flex flex-col h-full border-r bg-muted/50">
      {/* Header */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-lg">Workspaces</h2>
          <Button 
            variant="ghost" 
            size="icon"
            onClick={handleSync}
            disabled={syncStatus === 'syncing'}
          >
            <RefreshCw className={cn(
              "h-4 w-4",
              syncStatus === 'syncing' && "animate-spin"
            )} />
          </Button>
        </div>
        
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            {syncStatus === 'syncing' && <RefreshCw className="h-3 w-3 animate-spin" />}
            {syncStatus === 'success' && <CheckCircle className="h-3 w-3 text-green-500" />}
            {syncStatus === 'error' && <AlertCircle className="h-3 w-3 text-red-500" />}
            {syncStatus === 'idle' && <CheckCircle className="h-3 w-3 text-green-500" />}
            
            <span>
              {syncStatus === 'syncing' && 'Syncing...'}
              {syncStatus === 'success' && 'Synced'}
              {syncStatus === 'error' && 'Sync failed'}
              {syncStatus === 'idle' && 'Up to date'}
            </span>
          </div>
          <Badge variant="outline" className="text-xs">
            <Zap className="h-3 w-3 mr-1" />
            Real-time
          </Badge>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-6">
          {/* Quick Actions */}
          <div className="space-y-2">
            <Button 
              className="w-full justify-start" 
              variant={selectedWorkspace === 'global' ? "default" : "ghost"}
              onClick={handleStartChat}
            >
              <MessageSquarePlus className="mr-2 h-4 w-4" />
              Start Chat
            </Button>

            {selectedWorkspace && selectedWorkspace !== 'global' && (
              <Button 
                className="w-full justify-start" 
                variant="ghost"
                onClick={() => onNewChat?.()}
              >
                <MessageSquarePlus className="mr-2 h-4 w-4" />
                New Chat in Workspace
              </Button>
            )}
            
            <Link href="/workspaces">
              <Button className="w-full justify-start" variant="ghost">
                <Plus className="mr-2 h-4 w-4" />
                Connect Notion
              </Button>
            </Link>
          </div>

          <Separator />

          {/* Workspaces */}
          <WorkspaceList 
            selectedWorkspace={selectedWorkspace}
            onSelectWorkspace={handleWorkspaceSelect}
            onNewChat={onNewChat}
          />

          <Separator />

          {/* Recent Chats */}
          <RecentChats onChatSelect={handleChatSelect} />

          <Separator />

          {/* Settings */}
          <div className="space-y-2">
            <Link href="/setup">
              <Button className="w-full justify-start" variant="ghost">
                <Settings className="mr-2 h-4 w-4" />
                Settings
              </Button>
            </Link>
            
            <Link href="/analytics">
              <Button className="w-full justify-start" variant="ghost">
                <BarChart3 className="mr-2 h-4 w-4" />
                Analytics & Usage
              </Button>
            </Link>
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}