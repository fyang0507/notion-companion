'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
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
  Plus,
  RefreshCw,
  AlertCircle
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { MessageCitations } from '@/components/message-citations';
import { ChatFilterBar, ChatFilter } from '@/components/chat-filter-bar';
import { ChatMessage } from '@/types/chat';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { apiClient } from '@/lib/api';
import { useNotionConnection } from '@/hooks/use-notion-connection';
import { useNotionDatabases } from '@/hooks/use-notion-databases';
import { ChatSessionHook, useChatSessions } from '@/hooks/use-chat-sessions';
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
  
  // Use the hook as fallback when no chatSessions prop is provided
  const hookChatSessions = useChatSessions();
  const activeChatSessions = chatSessions || hookChatSessions;
  
  // Set up session lifecycle management (window close, idle detection, etc.)
  useSessionLifecycle({ chatSessions: activeChatSessions || null });
  
  // Use messages from chat sessions if available, otherwise use local state
  const [localMessages, setLocalMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hello! I\'m your Notion Companion. I can help you search through your workspace and answer questions about your content. Use the filters above to narrow down the scope of my search, or ask me anything about your knowledge base.',
      timestamp: new Date(),
      citations: []
    }
  ]);

  // Use chat session messages when available, otherwise fall back to local state
  const [fallbackMessages, setFallbackMessages] = useState<ChatMessage[]>(localMessages);
  
  // Initialize temporary chat mode if no session exists
  useEffect(() => {
    if (activeChatSessions && !activeChatSessions.currentSession && !activeChatSessions.isTemporaryChat && !hasInitialized.current) {
      console.log('Chat interface loaded without session - starting temporary chat mode');
      hasInitialized.current = true;
      activeChatSessions.startTemporaryChat();
    }
  }, [activeChatSessions, activeChatSessions?.currentSession, activeChatSessions?.isTemporaryChat]);
  
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
  
  // Sync local messages when chat sessions change (for session loading)
  // But DON'T sync during streaming to avoid overwriting the assistant placeholder
  useEffect(() => {
    if (activeChatSessions?.currentMessages && !streamingMessageId) {
      setFallbackMessages(activeChatSessions.currentMessages);
    }
  }, [activeChatSessions?.currentMessages, streamingMessageId]);
  
  // Get messages from chat sessions if available, otherwise use local state
  // During streaming, prioritize fallbackMessages to show real-time updates
  const messages = (streamingMessageId && fallbackMessages.length > 0) 
    ? fallbackMessages 
    : (activeChatSessions?.currentMessages || fallbackMessages);
  
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
  
  // Error handling state
  const [error, setError] = useState<string | null>(null);
  const [lastFailedMessage, setLastFailedMessage] = useState<string>('');

  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const hasInitialized = useRef(false);

  // Check if mobile
  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Removed redundant temporary chat initialization - handled by the main useEffect above

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

  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  const handleRetry = () => {
    if (lastFailedMessage) {
      setInput(lastFailedMessage);
      setError(null);
      setLastFailedMessage('');
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    // Clear any previous errors
    setError(null);

    // Debug logging removed to reduce console noise

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
      citations: []
    };

    // Store the message for potential retry
    setLastFailedMessage(input);

    // Add message through chat sessions if available
    // addMessage will handle session creation if we're in temporary chat mode
    let sessionId: string | null = null;
    if (activeChatSessions) {
      const sessionContext = {
        database_filters: filters.workspaces,
        document_type_filters: filters.documentTypes,
        author_filters: filters.authors,
        tag_filters: filters.tags,
        date_range_filter: filters.dateRange,
        search_query_filter: filters.searchQuery
      };
      
      sessionId = await activeChatSessions.addMessage(userMessage, sessionContext);
      
      // CRITICAL: Ensure fallback messages include the user message before adding assistant placeholder
      const messagesWithUser = [...fallbackMessages, userMessage];
      setFallbackMessages(messagesWithUser);
    } else {
      setFallbackMessages(prev => [...prev, userMessage]);
    }

    setInput('');
    setIsLoading(true);
    
    // Create assistant message placeholder
    const assistantMessageId = `assistant-${Date.now()}`;
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      citations: [],
      isStreaming: true
    };

    // CRITICAL: Set streaming ID FIRST to prevent sync effect from interfering
    setStreamingMessageId(assistantMessageId);

    // Add assistant message placeholder
    // Use the most recent messages state (either from session sync or manual user message addition)
    const currentFallback = activeChatSessions ? [...fallbackMessages] : fallbackMessages;
    const messagesWithAssistant = [...currentFallback, assistantMessage];
    setFallbackMessages(messagesWithAssistant);

    try {
      // Prepare request data using the existing ChatRequest interface
      const requestData: import('@/lib/api').ChatRequest = {
        messages: [
          { role: 'user', content: userMessage.content }
        ],
        database_filters: filters.workspaces,
        session_id: sessionId || 'temp-session'
      };

      const responseStream = await apiClient.sendChatMessage(requestData);
      
      const reader = responseStream.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';
      let citations: any[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataContent = line.slice(6);
            console.log('Processing SSE line:', dataContent);
            
            // Check for stream termination signal
            if (dataContent === '[DONE]') {
              console.log('Received [DONE] signal, breaking');
              break;
            }
            
            try {
              const data = JSON.parse(dataContent);
              console.log('Parsed SSE data:', data);
              
              if (data.content) {
                fullContent += data.content;
                console.log('Received content chunk:', data.content, 'Total content:', fullContent.length);
                // Update streaming message
                const updateMessage = (msgs: ChatMessage[]) => 
                  msgs.map(msg => 
                    msg.id === assistantMessageId 
                      ? { ...msg, content: fullContent, isStreaming: true }
                      : msg
                  );

                if (activeChatSessions) {
                  const allMessages = activeChatSessions.currentMessages.some(m => m.id === assistantMessageId) 
                    ? activeChatSessions.currentMessages 
                    : [...activeChatSessions.currentMessages, assistantMessage];
                  const updatedMessages = updateMessage(allMessages);
                  setFallbackMessages(updatedMessages);
                } else {
                  setFallbackMessages(updateMessage);
                }
              } else if (data.citations) {
                citations = data.citations;
              } else if (data.type === 'done') {
                break;
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e);
            }
          }
        }
      }

      // Create final assistant message
      const finalAssistantMessage: ChatMessage = {
        id: assistantMessageId,
        role: 'assistant',
        content: fullContent,
        timestamp: new Date(),
        citations: citations,
        isStreaming: false
      };

      // Save the final assistant message to session if available
      if (activeChatSessions) {
        await activeChatSessions.saveMessageImmediately(finalAssistantMessage);
        // CRITICAL: Update the assistant message in session state to trigger re-renders
        activeChatSessions.updateMessage(assistantMessageId, {
          content: fullContent,
          isStreaming: false,
          citations: citations
        });
      }

      // Update messages to show final message
      const updateFinalMessage = (msgs: ChatMessage[]) => 
        msgs.map(msg => 
          msg.id === assistantMessageId
            ? finalAssistantMessage
            : msg
        );

      if (activeChatSessions) {
        const allMessages = activeChatSessions.currentMessages.some(m => m.id === assistantMessageId) 
          ? activeChatSessions.currentMessages 
          : [...activeChatSessions.currentMessages, assistantMessage];
        setFallbackMessages(updateFinalMessage(allMessages));
      } else {
        setFallbackMessages(updateFinalMessage);
      }

      // CRITICAL: Ensure the final message persists in fallback messages before clearing streaming
      const finalMessages = activeChatSessions?.currentMessages?.length 
        ? [...activeChatSessions.currentMessages, finalAssistantMessage]
        : updateFinalMessage(fallbackMessages);
      setFallbackMessages(finalMessages);
      
      setStreamingMessageId(null);
      setIsLoading(false);
      
      // Clear the stored message since it was successful
      setLastFailedMessage('');
      setError(null);

    } catch (error) {
      console.error('Chat error:', error);
      setError('Failed to send message. Please try again.');
      setIsLoading(false);
      setStreamingMessageId(null);

      // Remove the empty assistant message on error
      const removeFailedMessage = (msgs: ChatMessage[]) => 
        msgs.filter(msg => msg.id !== assistantMessageId);

      if (activeChatSessions) {
        setFallbackMessages(removeFailedMessage(activeChatSessions.currentMessages.concat([assistantMessage])));
      } else {
        setFallbackMessages(removeFailedMessage);
      }
    }
  };

  const getFilterContext = () => {
    const parts = [];
    
    if (filters.workspaces.length > 0) {
      const workspaceNames = filters.workspaces.map(id => {
        const workspace = databases.find(w => w.database_id === id);
        return workspace ? workspace.database_name : id;
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
    // Allow Shift+Enter for multiline input - don't prevent default
  };

  const handleBackToHome = () => {
    onBackToHome?.();
  };

  const handleModelSelect = (model: AIModel) => {
    setSelectedModel(model);
    setModelSelectorOpen(false);
  };

  const getWorkspaceDisplayName = () => {
    // Show session title if we have a current session
    if (activeChatSessions?.currentSession?.title) {
      return activeChatSessions.currentSession.title;
    }
    
    // Show "New Chat" for temporary chat sessions
    if (activeChatSessions?.isTemporaryChat) {
      return 'New Chat';
    }
    
    // Fall back to workspace/database filtering display
    if (filters.workspaces.length === 0) {
      return isConnected && connection ? connection.name : 'AI Chat';
    }
    
    if (filters.workspaces.length === 1) {
      const database = databases.find(w => w.database_id === filters.workspaces[0]);
      return database ? `${database.database_name}` : 'AI Chat';
    }
    
    return `${filters.workspaces.length} Databases`;
  };

  const getSubtitleText = () => {
    // Show "Chat Session" for active sessions
    if (activeChatSessions?.currentSession?.title) {
      return 'Chat Session';
    }
    
    // Show "New Chat" subtitle for temporary sessions
    if (activeChatSessions?.isTemporaryChat) {
      return 'Start a conversation to save this session';
    }
    
    // Default subtitle for workspace mode
    return 'AI-powered search with intelligent filtering';
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
                {getWorkspaceDisplayName()}
              </h2>
              <p className="text-xs md:text-sm text-muted-foreground">
                {getSubtitleText()}
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
        availableWorkspaces={databases.map(db => ({
          id: db.database_id,
          name: db.database_name,
          documentCount: db.document_count || 0
        }))}
        disabled={isLoading || activeChatSessions?.isLoading}
      />

      {/* Messages */}
      <ScrollArea className="flex-1 p-3 md:p-4" ref={scrollAreaRef}>
        <div className="space-y-4 md:space-y-6 max-w-4xl mx-auto">
          {/* Error Message */}
          {(error || activeChatSessions?.error) && (
            <div className="flex justify-center">
              <Card className="bg-destructive/10 border-destructive/20 max-w-md">
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm text-destructive font-medium mb-2">
                        {error || activeChatSessions?.error}
                      </p>
                      {(lastFailedMessage || activeChatSessions?.error) && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleRetry}
                          className="gap-2 text-destructive border-destructive/20 hover:bg-destructive/10"
                        >
                          <RefreshCw className="h-3 w-3" />
                          Retry
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                "flex gap-3 md:gap-4",
                message.role === 'user' ? "justify-end" : "justify-start"
              )}
              data-role={message.role === 'assistant' ? 'assistant' : message.role}
            >
              {message.role === 'assistant' && (
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
                    
                    {/* Show thinking indicator for empty assistant messages that are streaming */}
                    {message.isStreaming && !message.content && (
                      <div className="flex items-center space-x-2 text-muted-foreground">
                        <div className="flex space-x-1">
                          <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" style={{ animationDelay: '0ms' }}></div>
                          <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" style={{ animationDelay: '150ms' }}></div>
                          <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" style={{ animationDelay: '300ms' }}></div>
                        </div>
                        <span className="text-sm">Thinking...</span>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Citations */}
                {message.role === 'assistant' && message.citations && message.citations.length > 0 && message.content && (
                  <MessageCitations citations={message.citations} />
                )}

                {/* Message Actions */}
                {message.role === 'assistant' && !streamingMessageId && message.content && !isMobile && (
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
          <div className="flex gap-2 items-end">
            <Textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder={`Ask me anything${getFilterContext()}...`}
              disabled={isLoading || chatOperationLoading || activeChatSessions?.isLoading}
              className="flex-1 min-h-[44px] max-h-32 resize-none"
              rows={1}
              aria-label="message input"
              tabIndex={0}
              style={{
                height: 'auto',
                minHeight: '44px'
              }}
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement;
                target.style.height = 'auto';
                target.style.height = `${Math.min(target.scrollHeight, 128)}px`;
              }}
            />
            <Button 
              onClick={handleSend} 
              disabled={!input.trim() || isLoading || chatOperationLoading || activeChatSessions?.isLoading}
              size="icon"
              className="flex-shrink-0 h-11 w-11"
              aria-label="Send message"
              tabIndex={1}
            >
              {(isLoading || activeChatSessions?.isLoading) ? (
                <Loader2 className="h-4 w-4 animate-spin" data-testid="loading-indicator" />
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