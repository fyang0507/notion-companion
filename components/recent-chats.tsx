'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  MessageCircle, 
  Clock,
  MoreHorizontal,
  Trash2,
  RefreshCw
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { apiClient, RecentChatSummary } from '@/lib/api';

interface RecentChatsProps {
  onChatSelect?: (chatId: string, workspaceId?: string) => void;
}

export function RecentChats({ onChatSelect }: RecentChatsProps) {
  const [chats, setChats] = useState<RecentChatSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load recent chats on component mount
  useEffect(() => {
    loadRecentChats();
  }, []);

  const loadRecentChats = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Add timeout to the API call
      const timeoutPromise = new Promise<never>((_, reject) => {
        setTimeout(() => reject(new Error('Request timeout')), 5000);
      });
      
      const recentChats = await Promise.race([
        apiClient.getRecentChats(20),
        timeoutPromise
      ]);
      
      setChats(recentChats);
    } catch (err) {
      console.error('Failed to load recent chats:', err);
      
      // For any error (timeout, network, server, etc.), just show empty state
      setError(null);
      setChats([]);
    } finally {
      setLoading(false);
    }
  };

  const deleteChat = async (chatId: string) => {
    try {
      await apiClient.deleteChatSession(chatId, true); // Soft delete
      setChats(chats.filter(chat => chat.id !== chatId));
    } catch (err) {
      console.error('Failed to delete chat:', err);
      // Optionally show error message to user
    }
  };

  const handleChatClick = (chat: RecentChatSummary) => {
    if (onChatSelect) {
      // In single workspace model, we don't need workspace ID
      onChatSelect(chat.id);
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInMs = now.getTime() - date.getTime();
    const diffInHours = diffInMs / (1000 * 60 * 60);
    const diffInDays = diffInMs / (1000 * 60 * 60 * 24);

    if (diffInHours < 1) {
      return 'Just now';
    } else if (diffInHours < 24) {
      return `${Math.floor(diffInHours)}h ago`;
    } else if (diffInDays < 7) {
      return `${Math.floor(diffInDays)}d ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  return (
    <div className="space-y-4">
      {/* Recent Chats */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 justify-between">
          <div className="flex items-center gap-2">
            <Clock className="h-3 w-3 text-muted-foreground" />
            <h3 className="text-sm font-medium text-muted-foreground">Recent</h3>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={loadRecentChats}
            disabled={loading}
          >
            <RefreshCw className={cn("h-3 w-3", loading && "animate-spin")} />
          </Button>
        </div>
        
        <div className="space-y-1">
          {loading ? (
            <div className="text-center p-4 text-muted-foreground">
              <RefreshCw className="h-6 w-6 mx-auto mb-2 animate-spin" />
              <p className="text-sm">Loading chats...</p>
            </div>
          ) : error ? (
            <div className="text-center p-4 text-muted-foreground">
              <MessageCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm text-red-500">{error}</p>
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={loadRecentChats}
                className="mt-2"
              >
                Try again
              </Button>
            </div>
          ) : chats.length > 0 ? (
            chats.map((chat) => (
              <ChatItem 
                key={chat.id}
                chat={chat}
                onDelete={deleteChat}
                onClick={() => handleChatClick(chat)}
                formatTimestamp={formatTimestamp}
              />
            ))
          ) : (
            <div className="text-center p-4 text-muted-foreground">
              <MessageCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No recent chats</p>
              <p className="text-xs">
                Start a conversation to see your chat history here
              </p>
              <div className="mt-3 p-2 bg-muted/30 rounded text-xs">
                <p className="font-medium text-foreground mb-1">💡 Enable chat history</p>
                <p>Deploy the chat sessions schema in Supabase to save and continue conversations</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface ChatItemProps {
  chat: RecentChatSummary;
  onDelete: (chatId: string) => void;
  onClick: () => void;
  formatTimestamp: (timestamp: string) => string;
}

function ChatItem({ chat, onDelete, onClick, formatTimestamp }: ChatItemProps) {
  return (
    <div 
      className="group relative rounded-lg border p-3 hover:bg-accent cursor-pointer transition-colors"
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-2 flex-1 min-w-0">
          <MessageCircle className="h-4 w-4 mt-0.5 flex-shrink-0 text-muted-foreground" />
          
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <p className="font-medium text-sm truncate">{chat.title}</p>
            </div>
            
            <p className="text-xs text-muted-foreground truncate mb-1">
              {chat.last_message_preview || 'No preview available'}
            </p>
            
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>{chat.message_count} messages</span>
              <span>•</span>
              <span>{formatTimestamp(chat.last_message_at)}</span>
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
            <DropdownMenuItem 
              onClick={(e) => {
                e.stopPropagation();
                onDelete(chat.id);
              }}
              className="text-red-600"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}