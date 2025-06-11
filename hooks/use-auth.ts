'use client';

import { useState, useEffect } from 'react';

interface User {
  id: string;
  email: string;
  avatar_url?: string;
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    // Simulate authentication check with more realistic timing
    const checkAuth = async () => {
      try {
        // Simulate checking for existing session/token
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // For demo purposes, set a mock user
        // In production, this would check localStorage, cookies, or make an API call
        const mockUser = {
          id: '1',
          email: 'demo@example.com',
          avatar_url: 'https://images.pexels.com/photos/220453/pexels-photo-220453.jpeg?w=64&h=64&fit=crop&crop=face'
        };
        
        setUser(mockUser);
      } catch (error) {
        console.error('Auth check failed:', error);
        setUser(null);
      } finally {
        setLoading(false);
        setInitialized(true);
      }
    };

    checkAuth();
  }, []);

  return { user, loading, initialized };
}