'use client';

import { useState, useCallback, useRef } from 'react';
import { apiClient, ChatSession, ChatSessionCreate, RecentChatSummary, ChatMessageCreate, ChatSessionWithMessages } from '@/lib/api';
import { ChatMessage } from '@/types/chat';

export interface ChatSessionHook {
  // Current session state
  currentSession: ChatSession | null;
  currentMessages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  isTemporaryChat: boolean;
  
  // Session management
  startTemporaryChat: (sessionContext?: Record<string, any>) => void; // Main entry point for new chats
  loadSession: (sessionId: string) => Promise<void>;
  saveCurrentSession: () => Promise<void>;
  concludeCurrentSession: (reason?: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  
  // Message management
  addMessage: (message: ChatMessage, sessionContext?: Record<string, any>) => Promise<string | null>;
  saveMessageImmediately: (message: ChatMessage) => Promise<void>;
  updateMessage: (messageId: string, updates: Partial<ChatMessage>) => void;
  clearMessages: () => void;
  
  // Recent sessions
  recentSessions: RecentChatSummary[];
  loadRecentSessions: () => Promise<void>;
  refreshRecentSessions: () => Promise<void>;
  
  // Callback for session creation
  onSessionCreated?: (sessionId: string) => void;
  setOnSessionCreated: (callback: (sessionId: string) => void) => void;
}

export function useChatSessions(): ChatSessionHook {
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [currentMessages, setCurrentMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isTemporaryChat, setIsTemporaryChat] = useState(false);
  const [recentSessions, setRecentSessions] = useState<RecentChatSummary[]>([]);
  const [pendingSessionContext, setPendingSessionContext] = useState<Record<string, any> | null>(null);
  const [onSessionCreatedCallback, setOnSessionCreatedCallback] = useState<((sessionId: string) => void) | null>(null);
  
  // Keep track of unsaved messages
  const unsavedMessages = useRef<ChatMessage[]>([]);

  const loadRecentSessions = useCallback(async (): Promise<void> => {
    try {
      const timeoutPromise = new Promise<never>((_, reject) => {
        setTimeout(() => reject(new Error('Request timeout')), 5000);
      });
      
      const sessions = await Promise.race([
        apiClient.getRecentChats(20),
        timeoutPromise
      ]);
      
      setRecentSessions(sessions);
      setError(null); // Clear any previous errors
    } catch (err) {
      console.error('Failed to load recent sessions:', err);
      
      // For any error, just set empty array and continue
      setRecentSessions([]);
      setError(null); // Don't show error, just handle gracefully
    }
  }, []);

  const saveCurrentSession = useCallback(async (): Promise<void> => {
    // Messages are saved individually during chat flow, so this just refreshes recent sessions
    if (!currentSession) {
      return;
    }

    try {
      // Clear any remaining unsaved messages (they should have been saved individually)
      unsavedMessages.current = [];

      // Refresh recent sessions to update message counts and timestamps
      await loadRecentSessions();

    } catch (err) {
      console.error('Failed to refresh session:', err);
      // Don't throw here as this is often called automatically
    }
  }, [currentSession, loadRecentSessions]);



  const loadSession = useCallback(async (sessionId: string): Promise<void> => {
    try {
      setIsLoading(true);
      setError(null);

      // Conclude current session before loading new one if user has sent at least one message
      const userMessageCount = currentMessages.filter(msg => msg.role === 'user').length;
      if (currentSession && userMessageCount > 0) {
        await saveCurrentSession();
        try {
          await apiClient.concludeForResume(currentSession.id, sessionId);
        } catch (err) {
          console.error('Failed to conclude previous session:', err);
        }
      }

      // Load the requested session
      const sessionData = await apiClient.getChatSession(sessionId);
      
      setCurrentSession(sessionData.session);
      
      // Convert backend messages to frontend format
      const frontendMessages: ChatMessage[] = sessionData.messages.map(msg => ({
        id: msg.id,
        role: msg.role === 'user' ? 'user' : 'assistant',
        content: msg.content,
        timestamp: msg.created_at,
        citations: msg.citations || []
      }));
      
      setCurrentMessages(frontendMessages);
      unsavedMessages.current = [];
      setIsTemporaryChat(false);

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load session';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [currentSession, currentMessages, saveCurrentSession]);

  const deleteSession = useCallback(async (sessionId: string): Promise<void> => {
    try {
      await apiClient.deleteChatSession(sessionId, true); // Soft delete
      
      // If this was the current session, clear it
      if (currentSession?.id === sessionId) {
        setCurrentSession(null);
        setCurrentMessages([]);
        unsavedMessages.current = [];
      }

      // Remove from recent sessions
      setRecentSessions(prev => prev.filter(session => session.id !== sessionId));

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete session';
      setError(errorMessage);
      throw err;
    }
  }, [currentSession]);

  const setOnSessionCreated = useCallback((callback: (sessionId: string) => void) => {
    setOnSessionCreatedCallback(() => callback);
  }, []);

  const addMessage = useCallback(async (message: ChatMessage, sessionContext?: Record<string, any>): Promise<string | null> => {
    // If we're in temporary chat mode and this is a user message, create the session
    if (isTemporaryChat && message.role === 'user') {
      try {
        console.log('Creating session for first user message in temporary chat');
        const contextToUse = sessionContext || pendingSessionContext || {};
        
        // Create new session directly
        const sessionData: ChatSessionCreate = {
          title: 'New Chat',
          session_context: contextToUse
        };

        const newSession = await apiClient.createChatSession(sessionData);
        
        // Set up the new session state
        setCurrentSession(newSession);
        setIsTemporaryChat(false);
        setPendingSessionContext(null);
        
        // Add the message to the new session
        setCurrentMessages(prev => [...prev, message]);
        
        // User message will be saved by backend when chat request is processed
        console.log('First user message added to UI, will be saved by backend:', newSession.id);
        
        // Refresh recent sessions to include the new one
        await loadRecentSessions();
        
        // Notify parent component that a session was created
        if (onSessionCreatedCallback) {
          onSessionCreatedCallback(newSession.id);
        }
        
        return newSession.id;  // Return the new session ID
      } catch (err) {
        console.error('Failed to create session from temporary chat:', err);
        // Continue with temporary chat if session creation fails
      }
    }
    
    setCurrentMessages(prev => [...prev, message]);
    
    // Messages will be saved by backend when chat request is processed
    // Frontend only manages UI state, not persistence
    console.log('Message added to UI:', message.role, 'for session:', currentSession?.id || 'temporary');
    
    // Return current session ID if available, null otherwise
    return currentSession?.id || null;
  }, [isTemporaryChat, pendingSessionContext, loadRecentSessions, onSessionCreatedCallback, currentSession]);

  const saveMessageImmediately = useCallback(async (message: ChatMessage): Promise<void> => {
    // No-op: Backend handles all message persistence
    // This method is kept for compatibility but does nothing
    console.log('saveMessageImmediately called (no-op):', message.role, 'message for session:', currentSession?.id);
  }, [currentSession]);

  const updateMessage = useCallback((messageId: string, updates: Partial<ChatMessage>): void => {
    setCurrentMessages(prev => 
      prev.map(msg => 
        msg.id === messageId ? { ...msg, ...updates } : msg
      )
    );
    
    // Also update unsaved messages if the message exists there
    const unsavedIndex = unsavedMessages.current.findIndex(msg => msg.id === messageId);
    if (unsavedIndex !== -1) {
      unsavedMessages.current[unsavedIndex] = {
        ...unsavedMessages.current[unsavedIndex],
        ...updates
      };
    }
  }, []);

  const clearMessages = useCallback((): void => {
    setCurrentMessages([]);
    unsavedMessages.current = [];
    setIsTemporaryChat(false);
    setPendingSessionContext(null);
  }, []);

  const startTemporaryChat = useCallback((sessionContext?: Record<string, any>): void => {
    // This is the main entry point for starting new chats
    // Session will be created automatically when user sends first message
    
    // Clear any existing session and messages
    setCurrentSession(null);
    setCurrentMessages([]);
    unsavedMessages.current = [];
    setIsTemporaryChat(true);
    setPendingSessionContext(sessionContext || null);
    setError(null);
  }, []);


  const refreshRecentSessions = useCallback(async (): Promise<void> => {
    await loadRecentSessions();
  }, [loadRecentSessions]);

  const concludeCurrentSession = useCallback(async (reason?: string): Promise<void> => {
    if (!currentSession) {
      return;
    }

    try {
      // First save any unsaved messages
      await saveCurrentSession();
      
      // Then conclude the session (generate title and summary)
      await apiClient.concludeChatSession(currentSession.id, reason);
      
      // Refresh recent sessions to show updated title/summary
      await loadRecentSessions();

    } catch (err) {
      console.error('Failed to conclude session:', err);
      // Don't throw here as this is often called automatically
    }
  }, [currentSession, saveCurrentSession, loadRecentSessions]);

  return {
    currentSession,
    currentMessages,
    isLoading,
    error,
    isTemporaryChat,
    startTemporaryChat,
    loadSession,
    saveCurrentSession,
    concludeCurrentSession,
    deleteSession,
    addMessage,
    saveMessageImmediately,
    updateMessage,
    clearMessages,
    recentSessions,
    loadRecentSessions,
    refreshRecentSessions,
    setOnSessionCreated
  };
}