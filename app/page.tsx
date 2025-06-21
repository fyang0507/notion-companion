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
import { toast } from 'sonner';

export default function Home() {
  const { user, loading, initialized } = useAuth();
  const { connection, isConnected, loading: connectionLoading } = useNotionConnection();
  const chatSessions = useChatSessions();
  const [selectedWorkspace, setSelectedWorkspace] = useState<string | 'global' | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [chatKey, setChatKey] = useState(0);
  const [isMobile, setIsMobile] = useState(false);
  const [chatRefreshTrigger, setChatRefreshTrigger] = useState(0);
  
  // Check if we have a backend configured (API base URL is set)
  const isBackendConfigured = process.env.NEXT_PUBLIC_API_BASE_URL;
  
  // For now, since we have backend configured, always show chat interface
  // Later we can add checks for actual Notion connection status

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
    try {
      await chatSessions.createNewSession();
      setChatKey(prev => prev + 1);
      setChatRefreshTrigger(prev => prev + 1); // Trigger recent chats refresh
    } catch (err) {
      console.error('Failed to create new chat session:', err);
      // Fallback to regular chat reset - this ensures the app always works
      setChatKey(prev => prev + 1);
    }
  };

  const handleSelectWorkspace = (workspaceId: string | 'global') => {
    setSelectedWorkspace(workspaceId);
    // Auto-collapse sidebar on mobile when selecting workspace
    if (isMobile) {
      setSidebarCollapsed(true);
    }
  };

  const handleStartGlobalChat = async () => {
    // Always start temporary chat mode - session will be created when user sends first message
    chatSessions.startTemporaryChat();
    setSelectedWorkspace('global');
    setChatKey(prev => prev + 1);
    
    // Auto-collapse sidebar on mobile when starting chat
    if (isMobile) {
      setSidebarCollapsed(true);
    }
  };

  const handleChatSelect = async (chatId: string) => {
    try {
      await chatSessions.loadSession(chatId);
      setSelectedWorkspace('global');
      setChatKey(prev => prev + 1);
    } catch (err) {
      console.error('Failed to load chat session:', err);
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

  // Mobile layout - use overlay sidebar
  if (isMobile) {
    return (
      <div className="h-screen flex flex-col">
        <Header 
          user={user}
          onToggleSidebar={handleToggleSidebar}
          sidebarCollapsed={sidebarCollapsed}
        />
        
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
                  onStartGlobalChat={handleStartGlobalChat}
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
              />
            ) : (
              <DashboardHome 
                onSelectWorkspace={setSelectedWorkspace}
                onNewChat={handleNewChat}
                onStartGlobalChat={handleStartGlobalChat}
              />
            )}
          </div>
        </div>
      </div>
    );
  }

  // Desktop layout - use resizable panels
  return (
    <div className="h-screen flex flex-col">
      <Header 
        user={user}
        onToggleSidebar={handleToggleSidebar}
        sidebarCollapsed={sidebarCollapsed}
      />
      
      <div className="flex-1 overflow-hidden">
        <ResizablePanelGroup direction="horizontal" className="h-full">
          {!sidebarCollapsed && (
            <>
              <ResizablePanel defaultSize={25} minSize={20} maxSize={40}>
                <Sidebar 
                  selectedWorkspace={selectedWorkspace}
                  onSelectWorkspace={setSelectedWorkspace}
                  onNewChat={handleNewChat}
                  onStartGlobalChat={handleStartGlobalChat}
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
                />
              ) : (
                <DashboardHome 
                  onSelectWorkspace={setSelectedWorkspace}
                  onNewChat={handleNewChat}
                  onStartGlobalChat={handleStartGlobalChat}
                />
              )}
            </div>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </div>
  );
}