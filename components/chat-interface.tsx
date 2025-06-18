'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  Send, 
  Bot, 
  User, 
  Loader2, 
  ExternalLink,
  Copy,
  ThumbsUp,
  ThumbsDown,
  ArrowLeft,
  ChevronDown,
  Check
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { MessageCitations } from '@/components/message-citations';
import { ChatFilterBar, ChatFilter } from '@/components/chat-filter-bar';
import { ChatMessage } from '@/types/chat';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { apiClient } from '@/lib/api';
import { useNotionConnection } from '@/hooks/use-notion-connection';
import { useNotionDatabases } from '@/hooks/use-notion-databases';

interface ChatInterfaceProps {
  onBackToHome?: () => void;
}

interface AIModel {
  id: string;
  name: string;
  description: string;
  badge: string;
  cost: string;
}

const availableModels: AIModel[] = [
  {
    id: 'gpt-4.1-mini',
    name: 'GPT-4.1 Mini',
    description: 'Fast and efficient for most tasks',
    badge: 'GPT-4.1 Mini',
    cost: 'Low cost'
  },
  {
    id: 'gpt-4',
    name: 'GPT-4',
    description: 'Most capable model for complex reasoning',
    badge: 'GPT-4',
    cost: 'Higher cost'
  },
  {
    id: 'gpt-4-turbo',
    name: 'GPT-4 Turbo',
    description: 'Faster responses with good quality',
    badge: 'GPT-4 Turbo',
    cost: 'Medium cost'
  },
  {
    id: 'claude-3-sonnet',
    name: 'Claude 3 Sonnet',
    description: 'Excellent for analysis and writing',
    badge: 'Claude 3',
    cost: 'Medium cost'
  },
  {
    id: 'claude-3-haiku',
    name: 'Claude 3 Haiku',
    description: 'Fast and cost-effective',
    badge: 'Claude 3 Haiku',
    cost: 'Low cost'
  }
];

export function ChatInterface({ onBackToHome }: ChatInterfaceProps) {
  const { connection, isConnected } = useNotionConnection();
  const { databases } = useNotionDatabases();
  
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      type: 'bot',
      content: 'Hello! I\'m your Notion Companion. I can help you search through your workspace and answer questions about your content. Use the filters above to narrow down the scope of my search, or ask me anything about your knowledge base.',
      timestamp: new Date(),
      citations: []
    }
  ]);
  
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<AIModel>(availableModels[0]); // Default to GPT-4.1 Mini
  const [modelSelectorOpen, setModelSelectorOpen] = useState(false);
  const [filters, setFilters] = useState<ChatFilter>({
    workspaces: [], // Single workspace model - filters work within the connected workspace
    documentTypes: [],
    dateRange: {},
    authors: [],
    tags: [],
    searchQuery: ''
  });
  const [isMobile, setIsMobile] = useState(false);

  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Check if mobile
  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Convert databases to workspace format for filter bar compatibility
  // In single workspace model, each database acts like a "workspace" for filtering
  const availableWorkspaces = databases.map(db => ({
    id: db.database_id,
    name: db.database_name,
    documentCount: db.document_count || 0
  }));

  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: input,
      timestamp: new Date(),
      citations: []
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    // Create bot message immediately but with empty content
    const botMessageId = (Date.now() + 1).toString();
    const botMessage: ChatMessage = {
      id: botMessageId,
      type: 'bot',
      content: '',
      timestamp: new Date(),
      citations: [
        {
          id: '1',
          title: 'Product Roadmap Q4',
          url: 'https://notion.so/example-page-1',
          preview: 'Our Q4 roadmap focuses on three key areas: performance optimization, new integrations, and user experience improvements...',
          score: 0.95
        },
        {
          id: '2', 
          title: 'API Documentation',
          url: 'https://notion.so/example-page-2',
          preview: 'The authentication endpoint requires a Bearer token in the Authorization header. Rate limits apply...',
          score: 0.87
        }
      ]
    };

    // Add the empty bot message and start streaming
    setMessages(prev => [...prev, botMessage]);
    setStreamingMessageId(botMessageId);

    try {
      // Prepare API request
      const apiMessages = messages.concat(userMessage).map(msg => ({
        role: msg.type === 'bot' ? 'assistant' : 'user',
        content: msg.content
      }));

      const stream = await apiClient.sendChatMessage({
        messages: apiMessages
        // Single-user, single-workspace app - no IDs needed
      });

      const reader = stream.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') {
              setIsLoading(false);
              setStreamingMessageId(null);
              break;
            }

            try {
              const parsed = JSON.parse(data);
              if (parsed.content) {
                setMessages(prev => 
                  prev.map(msg => 
                    msg.id === botMessageId 
                      ? { ...msg, content: msg.content + parsed.content }
                      : msg
                  )
                );
              }
            } catch (e) {
              // Skip invalid JSON
            }
          }
        }
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => 
        prev.map(msg => 
          msg.id === botMessageId 
            ? { ...msg, content: 'Sorry, I encountered an error. Please try again.' }
            : msg
        )
      );
      setIsLoading(false);
      setStreamingMessageId(null);
    }
  };

  const getFilterContext = () => {
    const activeFilters = [];
    
    if (filters.workspaces.length > 0) {
      const databaseNames = filters.workspaces.map(id => 
        availableWorkspaces.find(w => w.id === id)?.name
      ).filter(Boolean);
      activeFilters.push(`in ${databaseNames.join(', ')}`);
    } else if (isConnected && connection) {
      activeFilters.push(`across ${connection.name}`);
    } else {
      activeFilters.push('across all content');
    }

    if (filters.documentTypes.length > 0) {
      activeFilters.push(`filtering by ${filters.documentTypes.join(', ')}`);
    }

    if (filters.searchQuery) {
      activeFilters.push(`matching "${filters.searchQuery}"`);
    }

    return activeFilters.length > 0 ? ` (${activeFilters.join(', ')})` : '';
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleBackToHome = () => {
    if (onBackToHome) {
      onBackToHome();
    }
  };

  const handleModelSelect = (model: AIModel) => {
    setSelectedModel(model);
    setModelSelectorOpen(false);
  };

  const getWorkspaceDisplayName = () => {
    if (filters.workspaces.length === 0) {
      return isConnected && connection ? connection.name : 'AI Chat';
    }
    
    if (filters.workspaces.length === 1) {
      const database = availableWorkspaces.find(w => w.id === filters.workspaces[0]);
      return database ? `${database.name}` : 'AI Chat';
    }
    
    return `${filters.workspaces.length} Databases`;
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b p-3 md:p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <Button 
              variant="ghost" 
              size="icon"
              onClick={handleBackToHome}
              className="hover:bg-accent flex-shrink-0"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            
            <div className="min-w-0 flex-1">
              <h2 className="font-semibold text-base md:text-lg truncate">{getWorkspaceDisplayName()}</h2>
              <p className="text-xs md:text-sm text-muted-foreground">
                AI-powered search with intelligent filtering
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-2 flex-shrink-0">
            {/* Model Selector */}
            <Popover open={modelSelectorOpen} onOpenChange={setModelSelectorOpen}>
              <PopoverTrigger asChild>
                <Button 
                  variant="outline" 
                  className="gap-2 h-8 px-3 text-xs hover:bg-accent transition-colors"
                >
                  <Bot className="h-3 w-3" />
                  <span className="hidden sm:inline">{selectedModel.badge}</span>
                  <span className="sm:hidden">{selectedModel.badge.split(' ')[0]}</span>
                  <ChevronDown className="h-3 w-3" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-80" align="end">
                <div className="space-y-4">
                  <div>
                    <h4 className="font-medium text-sm mb-1">Select AI Model</h4>
                    <p className="text-xs text-muted-foreground">
                      Choose the AI model that best fits your needs
                    </p>
                  </div>
                  
                  <div className="space-y-2">
                    {availableModels.map((model) => (
                      <div
                        key={model.id}
                        className={cn(
                          "flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors hover:bg-accent",
                          selectedModel.id === model.id && "border-primary bg-primary/5"
                        )}
                        onClick={() => handleModelSelect(model)}
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <p className="font-medium text-sm">{model.name}</p>
                            {selectedModel.id === model.id && (
                              <Check className="h-4 w-4 text-primary" />
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground mb-1">
                            {model.description}
                          </p>
                          <Badge variant="secondary" className="text-xs">
                            {model.cost}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                  
                  <div className="pt-2 border-t">
                    <p className="text-xs text-muted-foreground">
                      Model selection affects response quality, speed, and token usage.
                    </p>
                  </div>
                </div>
              </PopoverContent>
            </Popover>
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <ChatFilterBar
        filters={filters}
        onFiltersChange={setFilters}
        availableWorkspaces={availableWorkspaces}
      />

      {/* Messages */}
      <ScrollArea className="flex-1 p-3 md:p-4" ref={scrollAreaRef}>
        <div className="space-y-4 md:space-y-6 max-w-4xl mx-auto">
          {messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                "flex gap-3 md:gap-4",
                message.type === 'user' ? "justify-end" : "justify-start"
              )}
            >
              {message.type === 'bot' && (
                <div className="w-8 h-8 rounded-full gradient-bg flex items-center justify-center flex-shrink-0">
                  <Bot className="h-4 w-4 text-white" />
                </div>
              )}

              <div className={cn(
                "flex flex-col gap-2 max-w-[85%] md:max-w-[70%]",
                message.type === 'user' ? "items-end" : "items-start"
              )}>
                <Card className={cn(
                  "message-stream",
                  message.type === 'user' 
                    ? "bg-primary text-primary-foreground" 
                    : "bg-muted/50"
                )}>
                  <CardContent className="p-3 md:p-4">
                    <div className="whitespace-pre-wrap text-sm">
                      {message.content}
                      {streamingMessageId === message.id && message.content && (
                        <span className="inline-block w-2 h-4 bg-current ml-1 animate-pulse" />
                      )}
                    </div>
                    
                    {/* Show thinking indicator for empty bot messages that are streaming */}
                    {streamingMessageId === message.id && !message.content && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span>Searching through your filtered content...</span>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Citations */}
                {message.type === 'bot' && message.citations.length > 0 && message.content && (
                  <MessageCitations citations={message.citations} />
                )}

                {/* Message Actions */}
                {message.type === 'bot' && !streamingMessageId && message.content && !isMobile && (
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" size="icon" className="h-6 w-6">
                      <Copy className="h-3 w-3" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-6 w-6">
                      <ThumbsUp className="h-3 w-3" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-6 w-6">
                      <ThumbsDown className="h-3 w-3" />
                    </Button>
                  </div>
                )}
              </div>

              {message.type === 'user' && (
                <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                  <User className="h-4 w-4 text-primary-foreground" />
                </div>
              )}
            </div>
          ))}
        </div>
      </ScrollArea>

      {/* Input */}
      <div className="border-t p-3 md:p-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-2">
            <Input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={`Ask me anything${getFilterContext()}...`}
              disabled={isLoading}
              className="flex-1"
            />
            <Button 
              onClick={handleSend} 
              disabled={!input.trim() || isLoading}
              size="icon"
              className="flex-shrink-0"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
          
          <p className="text-xs text-muted-foreground mt-2 text-center">
            AI can make mistakes. Verify important information from original sources.
          </p>
        </div>
      </div>
    </div>
  );
}