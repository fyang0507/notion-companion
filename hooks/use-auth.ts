'use client';

import { useState, useEffect } from 'react';

interface User {
  id: string;
  email: string;
  avatar_url?: string;
}

export function useAuth() {
  const [user] = useState<User>({
    id: 'single-user',
    email: 'user@notion-companion.com',
    avatar_url: 'https://images.pexels.com/photos/220453/pexels-photo-220453.jpeg?w=64&h=64&fit=crop&crop=face'
  });
  const [loading, setLoading] = useState(true);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    // Simulate brief loading for consistent UI behavior
    const timer = setTimeout(() => {
      setLoading(false);
      setInitialized(true);
    }, 100);

    return () => clearTimeout(timer);
  }, []);

  return { 
    user, 
    loading, 
    initialized
  };
}