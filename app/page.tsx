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
import { AuthDialog } from '@/components/auth-dialog';

export default function Home() {
  const { user, loading, initialized } = useAuth();
  const { connection, isConnected, loading: connectionLoading } = useNotionConnection();
  const [selectedWorkspace, setSelectedWorkspace] = useState<string | 'global' | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [chatKey, setChatKey] = useState(0);
  const [isMobile, setIsMobile] = useState(false);
  
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

  // Auto-start global chat when backend is configured and user is ready
  useEffect(() => {
    if (isBackendConfigured && user && initialized && !connectionLoading && !selectedWorkspace) {
      setSelectedWorkspace('global');
    }
  }, [isBackendConfigured, user, initialized, connectionLoading, selectedWorkspace]);


  const handleNewChat = () => {
    setChatKey(prev => prev + 1);
  };

  const handleSelectWorkspace = (workspaceId: string | 'global') => {
    setSelectedWorkspace(workspaceId);
    // Auto-collapse sidebar on mobile when selecting workspace
    if (isMobile) {
      setSidebarCollapsed(true);
    }
  };

  const handleStartGlobalChat = () => {
    setSelectedWorkspace('global');
    // Auto-collapse sidebar on mobile when starting chat
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

  // Show loading screen while checking authentication
  if (loading || !initialized) {
    return <LoadingScreen />;
  }

  // Show auth dialog if no user
  if (!user) {
    return <AuthDialog />;
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