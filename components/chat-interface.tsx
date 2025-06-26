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
  ArrowLeft,
  ChevronDown,
  Check,
  Plus
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { MessageCitations } from '@/components/message-citations';
import { ChatFilterBar, ChatFilter } from '@/components/chat-filter-bar';
import { ChatMessage } from '@/types/chat';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { apiClient } from '@/lib/api';
import { useNotionConnection } from '@/hooks/use-notion-connection';
import { useNotionDatabases } from '@/hooks/use-notion-databases';
import { ChatSessionHook } from '@/hooks/use-chat-sessions';
import { useSessionLifecycle } from '@/hooks/use-session-lifecycle';

interface ChatInterfaceProps {
  onBackToHome?: () => void;
  chatSessions?: ChatSessionHook;
  chatOperationLoading?: boolean;
  chatOperationStatus?: string;
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
    id: 'gpt-4o-mini',
    name: 'GPT-4o Mini',
    description: 'Fast and efficient for most tasks',
    badge: 'GPT-4o Mini',
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

export function ChatInterface({ onBackToHome, chatSessions, chatOperationLoading, chatOperationStatus }: ChatInterfaceProps) {
  const { connection, isConnected } = useNotionConnection();
  const { databases } = useNotionDatabases();
  
  // Set up session lifecycle management (window close, idle detection, etc.)
  useSessionLifecycle({ chatSessions: chatSessions || null });
  
  // Use messages from chat sessions if available, otherwise use local state
  const [localMessages, setLocalMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      role: 'bot',
      content: 'Hello! I\'m your Notion Companion. I can help you search through your workspace and answer questions about your content. Use the filters above to narrow down the scope of my search, or ask me anything about your knowledge base.',
      timestamp: new Date(),
      citations: []
    }
  ]);

  // Use chat session messages when available, otherwise fall back to local state
  const [fallbackMessages, setFallbackMessages] = useState<ChatMessage[]>(localMessages);
  
  // Get messages from chat sessions if available, otherwise use local state
  const messages = chatSessions?.currentMessages || fallbackMessages;
  
  // Sync local messages when chat sessions change (for session loading)
  useEffect(() => {
    if (chatSessions?.currentMessages) {
      setFallbackMessages(chatSessions.currentMessages);
    }
  }, [chatSessions?.currentMessages]);

  // Initialize temporary chat mode if no session exists
  useEffect(() => {
    if (chatSessions && !chatSessions.currentSession && !chatSessions.isTemporaryChat && !hasInitialized.current) {
      console.log('Chat interface loaded without session - starting temporary chat mode');
      hasInitialized.current = true;
      chatSessions.startTemporaryChat();
    }
  }, [chatSessions, chatSessions?.currentSession, chatSessions?.isTemporaryChat]);
  
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<AIModel>(availableModels[0]); // Default to GPT-4o Mini
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
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);

  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const hasInitialized = useRef(false);

  // Check if mobile
  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const handleCopyMessage = async (text: string, messageId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedMessageId(messageId);
      // Reset the copied state after 1 second
      setTimeout(() => setCopiedMessageId(null), 500);
    } catch (err) {
      console.error('Failed to copy text:', err);
    }
  };

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

    console.log('handleSend called', { 
      hasChatSessions: !!chatSessions, 
      isTemporaryChat: chatSessions?.isTemporaryChat,
      currentSession: chatSessions?.currentSession?.id 
    });

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
      citations: []
    };

    // Add message through chat sessions if available
    // addMessage will handle session creation if we're in temporary chat mode
    let sessionId: string | null = null;
    if (chatSessions) {
      const sessionContext = {
        database_filters: filters.workspaces,
        model_used: selectedModel.id,
        initial_filters: filters
      };
      sessionId = await chatSessions.addMessage(userMessage, sessionContext);
    } else {
      setFallbackMessages(prev => [...prev, userMessage]);
    }

    const currentInput = input;
    setInput('');
    setIsLoading(true);

    // Create placeholder for bot response with streaming indicator
    const botMessageId = `bot-${Date.now()}`;
    const botMessage: ChatMessage = {
      id: botMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      citations: []
    };

    // Add empty bot message immediately for streaming visualization
    if (chatSessions) {
      const currentMessages = chatSessions.currentMessages;
      setFallbackMessages([...currentMessages, botMessage]);
    } else {
      setFallbackMessages(prev => [...prev, botMessage]);
    }

    setStreamingMessageId(botMessageId);

    try {
      const finalSessionId = sessionId || 'temp-session';
      
      const response = await apiClient.sendChatMessage({
        messages: [
          { role: 'user', content: currentInput }
        ],
        database_filters: filters.workspaces,
        session_id: finalSessionId
      });

      const reader = response.getReader();
      const decoder = new TextDecoder();
      let accumulatedContent = '';
      let citations: any[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim();
            if (data === '[DONE]') continue;

            try {
              const parsed = JSON.parse(data);
              
              if (parsed.content) {
                accumulatedContent += parsed.content;
                
                // Update the streaming message
                const updateMessage = (msgs: ChatMessage[]) => 
                  msgs.map(msg => 
                    msg.id === botMessageId 
                      ? { ...msg, content: accumulatedContent, citations: parsed.citations || citations }
                      : msg
                  );

                if (chatSessions) {
                  setFallbackMessages(updateMessage(chatSessions.currentMessages.concat([botMessage])));
                } else {
                  setFallbackMessages(updateMessage);
                }
              }

              if (parsed.citations) {
                citations = parsed.citations;
              }
            } catch (e) {
              // Skip malformed JSON
            }
          }
        }
      }

      // Finalize the message
      const finalBotMessage: ChatMessage = {
        id: botMessageId,
        role: 'assistant',
        content: accumulatedContent,
        timestamp: new Date(),
        citations: citations
      };

      // Save the final bot message to session if available
      if (chatSessions && sessionId) {
        await chatSessions.saveMessageImmediately(finalBotMessage);
      }

      // Update final state
      const updateFinalMessage = (msgs: ChatMessage[]) => 
        msgs.map(msg => 
          msg.id === botMessageId 
            ? finalBotMessage
            : msg
        );

      if (chatSessions) {
        const allMessages = chatSessions.currentMessages.some(m => m.id === botMessageId) 
          ? chatSessions.currentMessages 
          : [...chatSessions.currentMessages, botMessage];
        setFallbackMessages(updateFinalMessage(allMessages));
      } else {
        setFallbackMessages(updateFinalMessage);
      }

    } catch (error) {
      console.error('Chat error:', error);
      
      // Remove the empty bot message on error
      const removeFailedMessage = (msgs: ChatMessage[]) => 
        msgs.filter(msg => msg.id !== botMessageId);

      if (chatSessions) {
        setFallbackMessages(removeFailedMessage(chatSessions.currentMessages.concat([botMessage])));
      } else {
        setFallbackMessages(removeFailedMessage);
      }
    } finally {
      setIsLoading(false);
      setStreamingMessageId(null);
    }
  };

  const getFilterContext = () => {
    const parts = [];
    
    if (filters.workspaces.length > 0) {
      const workspaceNames = filters.workspaces.map(id => {
        const workspace = availableWorkspaces.find(w => w.id === id);
        return workspace ? workspace.name : id;
      });
      parts.push(`in ${workspaceNames.join(', ')}`);
    }
    
    if (filters.documentTypes.length > 0) {
      parts.push(`${filters.documentTypes.join(', ')} documents`);
    }
    
    if (filters.authors.length > 0) {
      parts.push(`by ${filters.authors.join(', ')}`);
    }
    
    if (filters.tags.length > 0) {
      parts.push(`tagged ${filters.tags.join(', ')}`);
    }
    
    return parts.length > 0 ? ` ${parts.join(' ')}` : '';
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleBackToHome = () => {
    onBackToHome?.();
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
    <div className="flex flex-col h-full relative">
      {/* Chat Operation Loading Overlay */}
      {chatOperationLoading && (
        <div className="absolute inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-card border rounded-lg p-6 shadow-lg max-w-sm mx-4">
            <div className="flex items-center gap-3 mb-2">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <h3 className="font-medium">Processing...</h3>
            </div>
            <p className="text-sm text-muted-foreground">
              {chatOperationStatus || 'Preparing your chat session...'}
            </p>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="border-b p-3 md:p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <Button 
              variant="ghost" 
              size="icon"
              onClick={handleBackToHome}
              className="hover:bg-accent flex-shrink-0"
              disabled={chatOperationLoading}
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            
            <div className="min-w-0 flex-1">
              <h2 className="font-semibold text-base md:text-lg truncate">
                {chatSessions?.currentSession?.title || getWorkspaceDisplayName()}
              </h2>
              <p className="text-xs md:text-sm text-muted-foreground">
                {chatSessions?.currentSession?.title ? 'Chat Session' : 'AI-powered search with intelligent filtering'}
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
                  disabled={chatOperationLoading}
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
        disabled={chatOperationLoading}
      />

      {/* Messages */}
      <ScrollArea className="flex-1 p-3 md:p-4" ref={scrollAreaRef}>
        <div className="space-y-4 md:space-y-6 max-w-4xl mx-auto">
          {messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                "flex gap-3 md:gap-4",
                message.role === 'user' ? "justify-end" : "justify-start"
              )}
            >
              {message.role === 'bot' && (
                <div className="w-8 h-8 rounded-full gradient-bg flex items-center justify-center flex-shrink-0">
                  <Bot className="h-4 w-4 text-white" />
                </div>
              )}

              <div className={cn(
                "flex flex-col gap-2 max-w-[85%] md:max-w-[70%]",
                message.role === 'user' ? "items-end" : "items-start"
              )}>
                <Card className={cn(
                  "message-stream",
                  message.role === 'user' 
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
                {message.role === 'bot' && message.citations && message.citations.length > 0 && message.content && (
                  <MessageCitations citations={message.citations} />
                )}

                {/* Message Actions */}
                {message.role === 'bot' && !streamingMessageId && message.content && !isMobile && (
                  <div className="flex items-center gap-1">
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className="h-6 w-6"
                      onClick={() => handleCopyMessage(message.content, message.id)}
                      title={copiedMessageId === message.id ? "Copied!" : "Copy message"}
                    >
                      {copiedMessageId === message.id ? (
                        <Check className="h-3 w-3 text-600 animate-in fade-in-0 zoom-in-75 duration-50" />
                      ) : (
                        <Copy className="h-3 w-3" />
                      )}
                    </Button>
                  </div>
                )}
              </div>

              {message.role === 'user' && (
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
              disabled={isLoading || chatOperationLoading}
              className="flex-1"
            />
            <Button 
              onClick={handleSend} 
              disabled={!input.trim() || isLoading || chatOperationLoading}
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