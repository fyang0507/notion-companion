'use client';

import { Menu, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ThemeToggle } from '@/components/theme-toggle';
import { TokenUsageIndicator } from '@/components/token-usage-indicator';
import { Badge } from '@/components/ui/badge';

interface HeaderProps {
  user: any;
  onToggleSidebar: () => void;
  sidebarCollapsed: boolean;
}

export function Header({ user, onToggleSidebar, sidebarCollapsed }: HeaderProps) {
  return (
    <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-16 items-center px-4 md:px-6">
        <div className="flex items-center gap-3 md:gap-4 min-w-0 flex-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleSidebar}
            className="md:hidden flex-shrink-0"
          >
            <Menu className="h-5 w-5" />
          </Button>
          
          <div className="flex items-center gap-2 md:gap-3 min-w-0 flex-1">
            <div className="w-8 h-8 md:w-9 md:h-9 rounded-lg gradient-bg flex items-center justify-center flex-shrink-0">
              <span className="text-white font-bold text-sm md:text-base">N</span>
            </div>
            
            <div className="flex items-center gap-2 min-w-0 flex-1">
              <h1 className="font-semibold text-lg md:text-xl truncate">
                <span className="hidden sm:inline">Notion Companion</span>
                <span className="sm:hidden">Notion</span>
              </h1>
              <Badge variant="secondary" className="text-xs flex-shrink-0 hidden xs:inline-flex">
                Beta
              </Badge>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 md:gap-4 flex-shrink-0">
          <TokenUsageIndicator />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}