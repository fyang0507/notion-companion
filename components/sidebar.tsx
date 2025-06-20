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
  BarChart3,
  Database
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useNotionConnection } from '@/hooks/use-notion-connection';
import { useNotionDatabases } from '@/hooks/use-notion-databases';
import { RecentChats } from '@/components/recent-chats';
import Link from 'next/link';

interface SidebarProps {
  selectedWorkspace: string | 'global' | null;
  onSelectWorkspace: (id: string) => void;
  onNewChat?: () => void;
  onStartGlobalChat?: () => void;
  onChatSelect?: (chatId: string) => void;
}

export function Sidebar({ selectedWorkspace, onSelectWorkspace, onNewChat, onStartGlobalChat, onChatSelect }: SidebarProps) {
  const [syncStatus, setSyncStatus] = useState<'idle' | 'syncing' | 'success' | 'error'>('idle');
  const { connection, isConnected, syncNotion } = useNotionConnection();
  const { databases, loading: databasesLoading } = useNotionDatabases();

  const handleSync = async () => {
    if (!isConnected) return;
    
    setSyncStatus('syncing');
    try {
      await syncNotion();
      setSyncStatus('success');
      setTimeout(() => setSyncStatus('idle'), 2000);
    } catch (error) {
      setSyncStatus('error');
      setTimeout(() => setSyncStatus('idle'), 2000);
    }
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
    // In single workspace model, we don't need workspaceId
    if (onChatSelect) {
      onChatSelect(chatId);
    }
  };

  return (
    <div className="flex flex-col h-full border-r bg-muted/50">
      {/* Header */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-lg">Notion</h2>
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
                New Chat
              </Button>
            )}
            
            <Link href="/setup">
              <Button className="w-full justify-start" variant="ghost">
                <Plus className="mr-2 h-4 w-4" />
                Connect Databases
              </Button>
            </Link>
          </div>

          <Separator />

          {/* Databases */}
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">Your Databases</h3>
            {isConnected && connection ? (
              <div className="space-y-2">
                {/* Workspace Header */}
                <div className="p-3 rounded-lg border bg-accent/50">
                  <div className="flex items-center gap-2 mb-1">
                    <Book className="h-4 w-4" />
                    <span className="font-medium text-sm">{connection.name}</span>
                    <Badge variant="outline" className="text-xs">
                      <CheckCircle className="h-3 w-3 mr-1 text-green-500" />
                      Connected
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {connection.document_count || 0} documents • {connection.last_sync_at ? new Date(connection.last_sync_at).toLocaleDateString() : 'Never synced'}
                  </p>
                </div>

                {/* Databases List */}
                {databasesLoading ? (
                  <div className="p-3 rounded-lg border bg-muted/30">
                    <div className="flex items-center gap-2">
                      <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">Loading databases...</span>
                    </div>
                  </div>
                ) : databases.length > 0 ? (
                  <div className="space-y-1">
                    {databases.map((database) => (
                      <div key={database.database_id} className="p-2 rounded-lg border bg-background hover:bg-accent/30 transition-colors">
                        <div className="flex items-center gap-2 mb-1">
                          <Database className="h-3 w-3 text-muted-foreground" />
                          <span className="text-sm font-medium truncate">{database.database_name}</span>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {database.document_count || 0} documents
                          {database.last_analyzed_at && ` • ${new Date(database.last_analyzed_at).toLocaleDateString()}`}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-3 rounded-lg border bg-muted/30">
                    <div className="flex items-center gap-2 mb-1">
                      <Database className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">No databases found</span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Sync your databases to see available databases
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-3 rounded-lg border bg-muted/30">
                <div className="flex items-center gap-2 mb-1">
                  <Book className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium text-sm text-muted-foreground">No databases connected</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Connect your Notion databases to get started
                </p>
              </div>
            )}
          </div>

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