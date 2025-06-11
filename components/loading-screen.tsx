'use client';

import { Bot, Loader2 } from 'lucide-react';

interface LoadingScreenProps {
  message?: string;
}

export function LoadingScreen({ message = "Loading your workspace..." }: LoadingScreenProps) {
  return (
    <div className="h-screen flex flex-col items-center justify-center bg-background">
      <div className="flex flex-col items-center space-y-6">
        {/* Logo */}
        <div className="w-16 h-16 rounded-2xl gradient-bg flex items-center justify-center">
          <Bot className="h-8 w-8 text-white" />
        </div>
        
        {/* Loading indicator */}
        <div className="flex items-center space-x-3">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <span className="text-lg font-medium text-foreground">{message}</span>
        </div>
        
        {/* Progress dots */}
        <div className="flex space-x-2">
          <div className="w-2 h-2 bg-primary rounded-full animate-pulse"></div>
          <div className="w-2 h-2 bg-primary/60 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
          <div className="w-2 h-2 bg-primary/30 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
        </div>
        
        {/* Subtitle */}
        <p className="text-sm text-muted-foreground text-center max-w-md">
          Setting up your AI-powered knowledge assistant
        </p>
      </div>
    </div>
  );
}