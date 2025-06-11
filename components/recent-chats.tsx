'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  MessageCircle, 
  Clock,
  MoreHorizontal,
  Trash2
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';

interface Chat {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: string;
  messageCount: number;
  workspaceId?: string;
}

interface RecentChatsProps {
  onChatSelect?: (chatId: string, workspaceId?: string) => void;
}

export function RecentChats({ onChatSelect }: RecentChatsProps) {
  const [chats, setChats] = useState<Chat[]>([
    {
      id: 'chat-1',
      title: 'Product roadmap Q4',
      lastMessage: 'What are the key milestones for...',
      timestamp: '2h ago',
      messageCount: 12,
      workspaceId: 'ws-1'
    },
    {
      id: 'chat-2',
      title: 'API documentation',
      lastMessage: 'How do I implement authentication...',
      timestamp: '1d ago',
      messageCount: 6,
      workspaceId: 'ws-1'
    },
    {
      id: 'chat-3',
      title: 'Meeting notes analysis',
      lastMessage: 'Summarize the key decisions from...',
      timestamp: '3d ago',
      messageCount: 4,
      workspaceId: 'ws-2'
    }
  ]);

  const deleteChat = (chatId: string) => {
    setChats(chats.filter(chat => chat.id !== chatId));
  };

  const handleChatClick = (chat: Chat) => {
    if (onChatSelect) {
      onChatSelect(chat.id, chat.workspaceId);
    }
  };

  return (
    <div className="space-y-4">
      {/* Recent Chats */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Clock className="h-3 w-3 text-muted-foreground" />
          <h3 className="text-sm font-medium text-muted-foreground">Recent</h3>
        </div>
        
        <div className="space-y-1">
          {chats.map((chat) => (
            <ChatItem 
              key={chat.id}
              chat={chat}
              onDelete={deleteChat}
              onClick={() => handleChatClick(chat)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

interface ChatItemProps {
  chat: Chat;
  onDelete: (chatId: string) => void;
  onClick: () => void;
}

function ChatItem({ chat, onDelete, onClick }: ChatItemProps) {
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
              {chat.lastMessage}
            </p>
            
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>{chat.messageCount} messages</span>
              <span>•</span>
              <span>{chat.timestamp}</span>
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