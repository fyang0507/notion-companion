'use client';

import { useEffect, useRef, useCallback } from 'react';
import { ChatSessionHook } from './use-chat-sessions';
import { apiClient } from '@/lib/api';

interface UseSessionLifecycleProps {
  chatSessions: ChatSessionHook | null;
}

export function useSessionLifecycle({ chatSessions }: UseSessionLifecycleProps) {
  const lastActivityRef = useRef<Date>(new Date());
  const idleTimeoutRef = useRef<NodeJS.Timeout>();

  // Update last activity timestamp
  const updateActivity = useCallback(() => {
    lastActivityRef.current = new Date();
  }, []);

  // Handle session conclusion before page unload
  const handleBeforeUnload = useCallback((e: BeforeUnloadEvent) => {
    if (chatSessions?.currentSession && chatSessions.currentMessages.some(m => m.type === 'user')) {
      console.log('Window closing - concluding session via sendBeacon');
      
      // Use sendBeacon for reliable delivery during page unload
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
      const url = `${apiBaseUrl}/api/chat-sessions/${chatSessions.currentSession.id}/conclude`;
      const payload = new Blob([JSON.stringify({ reason: 'window_close' })], { 
        type: 'application/json' 
      });
      
      // sendBeacon is non-blocking and more reliable during page unload
      if (navigator.sendBeacon) {
        navigator.sendBeacon(url, payload);
      }
    }
  }, [chatSessions?.currentSession, chatSessions?.currentMessages]);

  // Handle visibility change (tab switch, window minimize)
  const handleVisibilityChange = useCallback(() => {
    if (document.visibilityState === 'hidden') {
      // User switched away from the tab
      if (chatSessions?.currentSession && chatSessions.currentMessages.some(m => m.type === 'user')) {
        console.log('Tab/window hidden - concluding session');
        
        // Use conclude for proper archiving and summary generation
        chatSessions.concludeCurrentSession('window_hidden').catch(err => {
          console.error('Failed to conclude session on visibility change:', err);
        });
      }
    } else if (document.visibilityState === 'visible') {
      // User returned to the tab - update activity
      updateActivity();
    }
  }, [chatSessions?.currentSession, chatSessions?.currentMessages, chatSessions?.concludeCurrentSession, updateActivity]);

  // Check for idle sessions periodically
  const checkIdleSession = useCallback(() => {
    if (!chatSessions?.currentSession || !chatSessions.currentMessages.some(m => m.type === 'user')) {
      return;
    }

    const now = new Date();
    const timeSinceActivity = now.getTime() - lastActivityRef.current.getTime();
    const tenMinutes = 10 * 60 * 1000; // 10 minutes in milliseconds

    if (timeSinceActivity >= tenMinutes) {
      console.log('Session idle for 10+ minutes - concluding session');
      
      chatSessions.concludeCurrentSession('idle').catch(err => {
        console.error('Failed to conclude idle session:', err);
      });
      
      // Clear the timeout since we've handled the idle session
      if (idleTimeoutRef.current) {
        clearTimeout(idleTimeoutRef.current);
        idleTimeoutRef.current = undefined;
      }
    }
  }, [chatSessions?.currentSession, chatSessions?.currentMessages, chatSessions?.concludeCurrentSession]);

  // Set up activity tracking and idle detection
  useEffect(() => {
    if (!chatSessions?.currentSession) {
      return;
    }

    // Activity event types to track
    const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];

    // Add activity listeners
    activityEvents.forEach(event => {
      document.addEventListener(event, updateActivity, { passive: true });
    });

    // Set up idle checking interval (check every 2 minutes)
    const idleCheckInterval = setInterval(checkIdleSession, 2 * 60 * 1000);

    return () => {
      // Cleanup activity listeners
      activityEvents.forEach(event => {
        document.removeEventListener(event, updateActivity);
      });
      
      // Clear idle check interval
      clearInterval(idleCheckInterval);
    };
  }, [chatSessions?.currentSession, updateActivity, checkIdleSession]);

  // Set up window event listeners
  useEffect(() => {
    window.addEventListener('beforeunload', handleBeforeUnload);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [handleBeforeUnload, handleVisibilityChange]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (idleTimeoutRef.current) {
        clearTimeout(idleTimeoutRef.current);
      }
    };
  }, []);

  return {
    updateActivity
  };
} 