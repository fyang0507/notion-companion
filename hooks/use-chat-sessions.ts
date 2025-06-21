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
  createNewSession: (title?: string, sessionContext?: Record<string, any>) => Promise<ChatSession>;
  loadSession: (sessionId: string) => Promise<void>;
  saveCurrentSession: () => Promise<void>;
  finalizeCurrentSession: () => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  
  // Message management
  addMessage: (message: ChatMessage) => void;
  saveMessageImmediately: (message: ChatMessage) => Promise<void>;
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
    // Messages are now saved immediately, so this mainly refreshes recent sessions
    if (!currentSession) {
      return;
    }

    try {
      // If there are any remaining unsaved messages, save them
      if (unsavedMessages.current.length > 0) {
        const backendMessages: ChatMessageCreate[] = unsavedMessages.current.map(msg => ({
          role: msg.type === 'user' ? 'user' : 'assistant',
          content: msg.content,
          citations: msg.citations || [],
          context_used: {}
        }));

        await apiClient.saveChatSession(currentSession.id, backendMessages);
        unsavedMessages.current = [];
      }

      // Refresh recent sessions to update message counts and timestamps
      await loadRecentSessions();

    } catch (err) {
      console.error('Failed to save session:', err);
      // Don't throw here as this is often called automatically
    }
  }, [currentSession, loadRecentSessions]);

  const finalizeCurrentSession = useCallback(async (): Promise<void> => {
    if (!currentSession) {
      return;
    }

    try {
      // First save any unsaved messages
      await saveCurrentSession();
      
      // Then finalize the session (generate title and summary)
      await apiClient.finalizeChatSession(currentSession.id);
      
      // Refresh recent sessions to show updated title/summary
      await loadRecentSessions();

    } catch (err) {
      console.error('Failed to finalize session:', err);
      // Don't throw here as this is often called automatically
    }
  }, [currentSession, saveCurrentSession, loadRecentSessions]);

  const createNewSession = useCallback(async (title?: string, sessionContext?: Record<string, any>): Promise<ChatSession> => {
    try {
      setIsLoading(true);
      setError(null);

      // First save and finalize current session if user has sent at least one message
      const userMessageCount = currentMessages.filter(msg => msg.type === 'user').length;
      if (currentSession && userMessageCount > 0) {
        await saveCurrentSession();
        try {
          await apiClient.finalizeChatSession(currentSession.id);
        } catch (err) {
          console.error('Failed to finalize previous session:', err);
        }
      }

      // Create new session
      const sessionData: ChatSessionCreate = {
        title: title || 'New Chat',
        session_context: sessionContext || {}
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

      // Save and finalize current session before loading new one if user has sent at least one message
      const userMessageCount = currentMessages.filter(msg => msg.type === 'user').length;
      if (currentSession && userMessageCount > 0) {
        await saveCurrentSession();
        try {
          await apiClient.finalizeChatSession(currentSession.id);
        } catch (err) {
          console.error('Failed to finalize previous session:', err);
        }
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
  }, [currentSession, currentMessages, finalizeCurrentSession]);

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

  const saveMessageImmediately = useCallback(async (message: ChatMessage): Promise<void> => {
    if (!currentSession) {
      return;
    }

    try {
      // Convert frontend message to backend format
      const backendMessage: ChatMessageCreate = {
        role: message.type === 'user' ? 'user' : 'assistant',
        content: message.content,
        citations: message.citations || [],
        context_used: {}
      };

      await apiClient.addMessageToSession(currentSession.id, backendMessage);
      
      // Remove from unsaved messages if it exists there
      const messageIndex = unsavedMessages.current.findIndex(msg => msg.id === message.id);
      if (messageIndex !== -1) {
        unsavedMessages.current.splice(messageIndex, 1);
      }

    } catch (err) {
      console.error('Failed to save message immediately:', err);
      // Don't throw here as this is often called automatically
    }
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
    finalizeCurrentSession,
    deleteSession,
    addMessage,
    saveMessageImmediately,
    updateMessage,
    clearMessages,
    recentSessions,
    loadRecentSessions,
    refreshRecentSessions
  };
}