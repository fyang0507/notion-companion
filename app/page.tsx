'use client';

import { useEffect, useState } from 'react';
import { Sidebar } from '@/components/sidebar';
import { ChatInterface } from '@/components/chat-interface';
import { WelcomeScreen } from '@/components/welcome-screen';
import { DashboardHome } from '@/components/dashboard-home';
import { Header } from '@/components/header';
import { LoadingScreen } from '@/components/loading-screen';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import { useAuth } from '@/hooks/use-auth';
import { useNotionConnection } from '@/hooks/use-notion-connection';
import { useChatSessions } from '@/hooks/use-chat-sessions';
import { useSessionLifecycle } from '@/hooks/use-session-lifecycle';
import { apiClient } from '@/lib/api';
import { toast } from 'sonner';

export default function Home() {
  const { user, loading, initialized } = useAuth();
  const { connection, isConnected, loading: connectionLoading } = useNotionConnection();
  const chatSessions = useChatSessions();
  
  // Set up session lifecycle management (window close, idle detection, etc.)
  useSessionLifecycle({ chatSessions });
  const [selectedWorkspace, setSelectedWorkspace] = useState<string | 'global' | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [chatKey, setChatKey] = useState(0);
  const [isMobile, setIsMobile] = useState(false);
  const [chatRefreshTrigger, setChatRefreshTrigger] = useState(0);
  const [chatOperationLoading, setChatOperationLoading] = useState(false);
  const [chatOperationStatus, setChatOperationStatus] = useState<string>('');
  
  // Check if we have a backend configured (API base URL is set)
  const isBackendConfigured = process.env.NEXT_PUBLIC_API_BASE_URL;
  
  // For now, since we have backend configured, always show chat interface
  // Later we can add checks for actual Notion connection status

  // Set up callback to refresh sidebar when new session is created
  useEffect(() => {
    chatSessions.setOnSessionCreated((sessionId: string) => {
      console.log('New session created, refreshing sidebar:', sessionId);
      setChatRefreshTrigger(prev => prev + 1);
    });
  }, []); // Only run once on mount

  // Check if mobile on mount and resize
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
      // Auto-collapse sidebar on mobile
      if (window.innerWidth < 768) {
        setSidebarCollapsed(true);
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Note: Recent chats are loaded by the RecentChats component itself
  // No need to load them here to avoid redundant API calls

  // Auto-start global chat when backend is configured and user is ready
  useEffect(() => {
    if (isBackendConfigured && user && initialized && !connectionLoading && !selectedWorkspace) {
      setSelectedWorkspace('global');
    }
  }, [isBackendConfigured, user, initialized, connectionLoading, selectedWorkspace]);

  const handleNewChat = async () => {
    console.log('handleNewChat called - starting temporary chat');
    
    // Check if user is already in an empty chat
    const hasUserMessages = chatSessions.currentMessages.some(m => m.role === 'user');
    const isAlreadyEmpty = chatSessions.isTemporaryChat || (!chatSessions.currentSession && !hasUserMessages);
    
    if (isAlreadyEmpty) {
      toast.info("You're already in a new chat! Start typing to begin a conversation.");
      return;
    }
    
    // Show loading state for concluding and starting new chat
    setChatOperationLoading(true);
    
    try {
      // First conclude current session if it exists and has user messages
      if (chatSessions.currentSession && hasUserMessages) {
        setChatOperationStatus('Concluding current chat...');
        console.log('Concluding current session before starting new chat, session ID:', chatSessions.currentSession.id);
        console.log('Current messages:', chatSessions.currentMessages.length, 'messages');
        const result = await apiClient.concludeCurrentAndStartNew(chatSessions.currentSession.id);
        console.log('Conclusion result:', result);
      } else {
        console.log('No session to conclude or no user messages found');
        console.log('Current session:', chatSessions.currentSession?.id);
        console.log('User messages:', chatSessions.currentMessages.filter(m => m.role === 'user').length);
      }
      
      setChatOperationStatus('Starting new chat...');
      
      // Always start with temporary chat - session will be created when user sends first message
      chatSessions.startTemporaryChat();
      setSelectedWorkspace('global');
      setChatKey(prev => prev + 1);
      setChatRefreshTrigger(prev => prev + 1); // Trigger recent chats refresh
      
      // Auto-collapse sidebar on mobile when starting chat
      if (isMobile) {
        setSidebarCollapsed(true);
      }
    } catch (err) {
      console.error('Failed to start new chat:', err);
      toast.error('Failed to start new chat. Please try again.');
    } finally {
      setChatOperationLoading(false);
      setChatOperationStatus('');
    }
  };

  const handleSelectWorkspace = (workspaceId: string | 'global') => {
    setSelectedWorkspace(workspaceId);
    // Auto-collapse sidebar on mobile when selecting workspace
    if (isMobile) {
      setSidebarCollapsed(true);
    }
  };



  const handleChatSelect = async (chatId: string) => {
    // Show loading state for resuming chat
    setChatOperationLoading(true);
    setChatOperationStatus('Resuming your recent chat...');
    
    try {
      await chatSessions.loadSession(chatId);
      setSelectedWorkspace('global');
      setChatKey(prev => prev + 1);
    } catch (err) {
      console.error('Failed to load chat session:', err);
      toast.error('Failed to load chat session. Please try again.');
    } finally {
      setChatOperationLoading(false);
      setChatOperationStatus('');
    }
    
    // Auto-collapse sidebar on mobile when selecting chat
    if (isMobile) {
      setSidebarCollapsed(true);
    }
  };

  const handleBackToHome = () => {
    setSelectedWorkspace(null);
  };

  const handleToggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  // Show loading screen while initializing
  if (loading || !initialized) {
    return <LoadingScreen />;
  }

  // Show loading screen while checking Notion connection
  if (connectionLoading) {
    return <LoadingScreen message="Checking your Notion connection..." />;
  }

  // Show welcome screen only if backend is not configured
  // When backend is configured, we auto-start the chat interface
  if (!isBackendConfigured) {
    return (
      <div className="h-screen flex flex-col">
        <Header 
          user={user}
          onToggleSidebar={handleToggleSidebar}
          sidebarCollapsed={sidebarCollapsed}
        />
        <WelcomeScreen onSelectWorkspace={handleSelectWorkspace} />
      </div>
    );
  }

  // Render main app UI - single layout that adapts to mobile/desktop
  return (
    <div className="h-screen flex flex-col">
      <Header 
        user={user}
        onToggleSidebar={handleToggleSidebar}
        sidebarCollapsed={sidebarCollapsed}
      />
      
      {isMobile ? (
        // Mobile layout - use overlay sidebar
        <div className="flex-1 relative overflow-hidden">
          {/* Mobile Sidebar Overlay */}
          {!sidebarCollapsed && (
            <>
              {/* Backdrop */}
              <div 
                className="absolute inset-0 bg-black/50 z-40"
                onClick={() => setSidebarCollapsed(true)}
              />
              
              {/* Sidebar */}
              <div className="absolute left-0 top-0 bottom-0 w-80 bg-background border-r z-50 transform transition-transform">
                <Sidebar 
                  selectedWorkspace={selectedWorkspace}
                  onSelectWorkspace={setSelectedWorkspace}
                  onNewChat={handleNewChat}
                  onChatSelect={handleChatSelect}
                  chatRefreshTrigger={chatRefreshTrigger}
                />
              </div>
            </>
          )}
          
          {/* Main Content */}
          <div className="h-full">
            {selectedWorkspace ? (
              <ChatInterface 
                key={chatKey} 
                onBackToHome={handleBackToHome}
                chatSessions={chatSessions}
                chatOperationLoading={chatOperationLoading}
                chatOperationStatus={chatOperationStatus}
              />
            ) : (
              <DashboardHome 
                onSelectWorkspace={setSelectedWorkspace}
                onNewChat={handleNewChat}
              />
            )}
          </div>
        </div>
      ) : (
        // Desktop layout - use resizable panels
        <div className="flex-1 overflow-hidden">
          <ResizablePanelGroup direction="horizontal" className="h-full">
            {!sidebarCollapsed && (
              <>
                <ResizablePanel defaultSize={25} minSize={20} maxSize={40}>
                  <Sidebar 
                    selectedWorkspace={selectedWorkspace}
                    onSelectWorkspace={setSelectedWorkspace}
                    onNewChat={handleNewChat}
                    onChatSelect={handleChatSelect}
                    chatRefreshTrigger={chatRefreshTrigger}
                  />
                </ResizablePanel>
                <ResizableHandle />
              </>
            )}
            
            <ResizablePanel defaultSize={sidebarCollapsed ? 100 : 75}>
              <div className="h-full flex flex-col">
                {selectedWorkspace ? (
                  <ChatInterface 
                    key={chatKey} 
                    onBackToHome={handleBackToHome}
                    chatSessions={chatSessions}
                    chatOperationLoading={chatOperationLoading}
                    chatOperationStatus={chatOperationStatus}
                  />
                ) : (
                  <DashboardHome 
                    onSelectWorkspace={setSelectedWorkspace}
                    onNewChat={handleNewChat}
                  />
                )}
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
        </div>
      )}
    </div>
  );
}