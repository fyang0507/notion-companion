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
  
  // Session management
  createNewSession: (title?: string) => Promise<ChatSession>;
  loadSession: (sessionId: string) => Promise<void>;
  saveCurrentSession: () => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  
  // Message management
  addMessage: (message: ChatMessage) => void;
  updateMessage: (messageId: string, updates: Partial<ChatMessage>) => void;
  clearMessages: () => void;
  
  // Recent sessions
  recentSessions: RecentChatSummary[];
  loadRecentSessions: () => Promise<void>;
  refreshRecentSessions: () => Promise<void>;
}

export function useChatSessions(): ChatSessionHook {
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [currentMessages, setCurrentMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recentSessions, setRecentSessions] = useState<RecentChatSummary[]>([]);
  
  // Keep track of unsaved messages
  const unsavedMessages = useRef<ChatMessage[]>([]);

  const createNewSession = useCallback(async (title?: string): Promise<ChatSession> => {
    try {
      setIsLoading(true);
      setError(null);

      // First save current session if it has messages
      if (currentSession && currentMessages.length > 0) {
        await saveCurrentSession();
      }

      // Create new session
      const sessionData: ChatSessionCreate = {
        title: title || 'New Chat',
        session_context: {}
      };

      const newSession = await apiClient.createChatSession(sessionData);
      
      setCurrentSession(newSession);
      setCurrentMessages([]);
      unsavedMessages.current = [];

      // Refresh recent sessions to include the new one
      await loadRecentSessions();

      return newSession;
    } catch (err) {
      let errorMessage = 'Failed to create new session';
      
      if (err instanceof Error) {
        if (err.message.includes('503') || err.message.includes('not available')) {
          errorMessage = 'Chat sessions feature not yet set up. Using temporary chat.';
        } else {
          errorMessage = err.message;
        }
      }
      
      setError(errorMessage);
      
      // Don't throw error for missing tables - allow app to continue with temporary chat
      if (err instanceof Error && (err.message.includes('503') || err.message.includes('not available'))) {
        console.warn('Chat sessions not available, continuing with temporary chat');
        return null as any; // Will be handled by fallback logic
      }
      
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [currentSession, currentMessages]);

  const loadSession = useCallback(async (sessionId: string): Promise<void> => {
    try {
      setIsLoading(true);
      setError(null);

      // Save current session before loading new one
      if (currentSession && currentMessages.length > 0) {
        await saveCurrentSession();
      }

      // Load the requested session
      const sessionData = await apiClient.getChatSession(sessionId);
      
      setCurrentSession(sessionData.session);
      
      // Convert backend messages to frontend format
      const frontendMessages: ChatMessage[] = sessionData.messages.map(msg => ({
        id: msg.id,
        type: msg.role === 'user' ? 'user' : 'bot',
        content: msg.content,
        timestamp: new Date(msg.created_at),
        citations: msg.citations || []
      }));
      
      setCurrentMessages(frontendMessages);
      unsavedMessages.current = [];

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load session';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [currentSession, currentMessages]);

  const saveCurrentSession = useCallback(async (): Promise<void> => {
    if (!currentSession || unsavedMessages.current.length === 0) {
      return;
    }

    try {
      // Convert frontend messages to backend format
      const backendMessages: ChatMessageCreate[] = unsavedMessages.current.map(msg => ({
        role: msg.type === 'user' ? 'user' : 'assistant',
        content: msg.content,
        citations: msg.citations || [],
        context_used: {}
      }));

      await apiClient.saveChatSession(currentSession.id, backendMessages);
      unsavedMessages.current = [];

      // Refresh recent sessions to update message counts and timestamps
      await loadRecentSessions();

    } catch (err) {
      console.error('Failed to save session:', err);
      // Don't throw here as this is often called automatically
    }
  }, [currentSession]);

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

  const addMessage = useCallback((message: ChatMessage): void => {
    setCurrentMessages(prev => [...prev, message]);
    unsavedMessages.current.push(message);
  }, []);

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
  }, []);

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

  const refreshRecentSessions = useCallback(async (): Promise<void> => {
    await loadRecentSessions();
  }, [loadRecentSessions]);

  return {
    currentSession,
    currentMessages,
    isLoading,
    error,
    createNewSession,
    loadSession,
    saveCurrentSession,
    deleteSession,
    addMessage,
    updateMessage,
    clearMessages,
    recentSessions,
    loadRecentSessions,
    refreshRecentSessions
  };
}