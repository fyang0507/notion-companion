'use client';

import { useState, useEffect } from 'react';
import { logger } from '@/lib/logger';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';

interface LogStats {
  total: number;
  byLevel: Record<string, number>;
  oldestTimestamp?: string;
  newestTimestamp?: string;
}

export function DebugLogs() {
  const [stats, setStats] = useState<LogStats | null>(null);
  const [exportedLogs, setExportedLogs] = useState<string>('');
  const [isExportOpen, setIsExportOpen] = useState(false);

  useEffect(() => {
    const updateStats = () => {
      setStats(logger.getLogStats());
    };

    updateStats();
    const interval = setInterval(updateStats, 5000); // Update every 5 seconds

    return () => clearInterval(interval);
  }, []);

  const handleExportLogs = () => {
    const logs = logger.exportLogs();
    setExportedLogs(logs);
    setIsExportOpen(true);
  };

  const handleClearLogs = () => {
    logger.clearLogs();
    setStats(logger.getLogStats());
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(exportedLogs);
      // Could add a toast notification here
    } catch (err) {
      console.error('Failed to copy logs to clipboard:', err);
    }
  };

  if (!stats) {
    return null;
  }

  const levelColors = {
    debug: 'bg-gray-100 text-gray-800',
    info: 'bg-blue-100 text-blue-800',
    warn: 'bg-yellow-100 text-yellow-800',
    error: 'bg-red-100 text-red-800',
  };

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="text-sm font-medium">Debug Logs</CardTitle>
        <CardDescription className="text-xs">
          Frontend logging statistics
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <span className="font-medium">Total:</span> {stats.total}
          </div>
          <div>
            <span className="font-medium">Since:</span>{' '}
            {stats.oldestTimestamp ? 
              new Date(stats.oldestTimestamp).toLocaleTimeString() : 
              'N/A'
            }
          </div>
        </div>

        <div className="flex flex-wrap gap-1">
          {Object.entries(stats.byLevel).map(([level, count]) => (
            <Badge
              key={level}
              variant="secondary"
              className={`text-xs ${levelColors[level as keyof typeof levelColors] || 'bg-gray-100'}`}
            >
              {level}: {count}
            </Badge>
          ))}
        </div>

        <div className="flex gap-2">
          <Dialog open={isExportOpen} onOpenChange={setIsExportOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm" onClick={handleExportLogs}>
                Export
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-4xl max-h-[80vh]">
              <DialogHeader>
                <DialogTitle>Exported Logs</DialogTitle>
                <DialogDescription>
                  Copy these logs for debugging purposes
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div className="flex gap-2">
                  <Button size="sm" onClick={copyToClipboard}>
                    Copy to Clipboard
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setIsExportOpen(false)}
                  >
                    Close
                  </Button>
                </div>
                <ScrollArea className="h-96">
                  <Textarea
                    value={exportedLogs}
                    readOnly
                    className="min-h-96 font-mono text-xs"
                    placeholder="Logs will appear here..."
                  />
                </ScrollArea>
              </div>
            </DialogContent>
          </Dialog>

          <Button variant="destructive" size="sm" onClick={handleClearLogs}>
            Clear
          </Button>
        </div>

        <div className="text-xs text-gray-500">
          Logs persist in localStorage for debugging
        </div>
      </CardContent>
    </Card>
  );
}