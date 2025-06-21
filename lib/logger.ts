// Frontend logging system with localStorage persistence

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  module?: string;
  requestId?: string;
  extra?: Record<string, any>;
  error?: {
    message: string;
    stack?: string;
    name: string;
  };
}

class FrontendLogger {
  private maxLogEntries = 1000; // Keep last 1000 log entries
  private logKey = 'notion-companion-logs';
  private currentRequestId: string | null = null;
  private pendingLogs: LogEntry[] = [];
  private batchTimeout: NodeJS.Timeout | null = null;
  private maxBatchSize = 50;
  private batchDelayMs = 2000; // Send logs every 2 seconds
  
  constructor() {
    // Clear all logs if in development mode (fresh start for testing sessions)
    if (typeof window !== 'undefined' && (
      process.env.NODE_ENV === 'development' || 
      window.location.hostname === 'localhost'
    )) {
      this.clearLogs();
      console.log('🧹 Frontend logs cleared for development session');
    } else {
      // Clean up old logs on startup for production
      this.cleanupOldLogs();
    }
    
    // Start periodic log sending for important logs
    this.startLogSending();
  }

  private getCurrentTimestamp(): string {
    return new Date().toISOString();
  }

  private generateRequestId(): string {
    return Math.random().toString(36).substring(2, 10);
  }

  private getStoredLogs(): LogEntry[] {
    try {
      const logs = localStorage.getItem(this.logKey);
      return logs ? JSON.parse(logs) : [];
    } catch (error) {
      console.warn('Failed to retrieve logs from localStorage:', error);
      return [];
    }
  }

  private storeLogs(logs: LogEntry[]): void {
    try {
      // Keep only the most recent logs
      const trimmedLogs = logs.slice(-this.maxLogEntries);
      localStorage.setItem(this.logKey, JSON.stringify(trimmedLogs));
    } catch (error) {
      console.warn('Failed to store logs to localStorage:', error);
      // If storage is full, try to free space by removing older logs
      try {
        const reducedLogs = logs.slice(-Math.floor(this.maxLogEntries / 2));
        localStorage.setItem(this.logKey, JSON.stringify(reducedLogs));
      } catch (retryError) {
        console.warn('Failed to store reduced logs:', retryError);
      }
    }
  }

  private cleanupOldLogs(): void {
    const logs = this.getStoredLogs();
    const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
    
    // Remove logs older than 24 hours
    const recentLogs = logs.filter(log => log.timestamp > oneDayAgo);
    
    if (recentLogs.length !== logs.length) {
      this.storeLogs(recentLogs);
    }
  }

  private createLogEntry(
    level: LogLevel,
    message: string,
    module?: string,
    extra?: Record<string, any>,
    error?: Error
  ): LogEntry {
    const entry: LogEntry = {
      timestamp: this.getCurrentTimestamp(),
      level,
      message,
      module,
      requestId: this.currentRequestId || undefined,
      extra,
    };

    if (error) {
      entry.error = {
        message: error.message,
        stack: error.stack,
        name: error.name,
      };
    }

    return entry;
  }

  private log(level: LogLevel, message: string, module?: string, extra?: Record<string, any>, error?: Error): void {
    const entry = this.createLogEntry(level, message, module, extra, error);
    
    // Store to localStorage
    const logs = this.getStoredLogs();
    logs.push(entry);
    this.storeLogs(logs);

    // Add to pending logs for backend if it's warning or error level
    if (level === 'warn' || level === 'error') {
      this.pendingLogs.push(entry);
      this.scheduleBatchSend();
    }

    // Also log to console for development
    const consoleMessage = `[${level.toUpperCase()}] ${module ? `(${module}) ` : ''}${message}`;
    const consoleExtra = {
      ...extra,
      requestId: this.currentRequestId,
      timestamp: entry.timestamp,
    };

    switch (level) {
      case 'debug':
        console.debug(consoleMessage, consoleExtra);
        break;
      case 'info':
        console.info(consoleMessage, consoleExtra);
        break;
      case 'warn':
        console.warn(consoleMessage, consoleExtra);
        break;
      case 'error':
        if (error) {
          console.error(consoleMessage, error, consoleExtra);
        } else {
          console.error(consoleMessage, consoleExtra);
        }
        break;
    }
  }

  // Set request ID for correlating with backend logs
  setRequestId(requestId: string | null): void {
    this.currentRequestId = requestId;
  }

  // Generate and set a new request ID
  generateAndSetRequestId(): string {
    const requestId = this.generateRequestId();
    this.setRequestId(requestId);
    return requestId;
  }

  // Get current request ID
  getRequestId(): string | null {
    return this.currentRequestId;
  }

  // Log methods
  debug(message: string, module?: string, extra?: Record<string, any>): void {
    this.log('debug', message, module, extra);
  }

  info(message: string, module?: string, extra?: Record<string, any>): void {
    this.log('info', message, module, extra);
  }

  warn(message: string, module?: string, extra?: Record<string, any>): void {
    this.log('warn', message, module, extra);
  }

  error(message: string, module?: string, extra?: Record<string, any>, error?: Error): void {
    this.log('error', message, module, extra, error);
  }

  // Performance logging
  logPerformance(operation: string, durationMs: number, module?: string, extra?: Record<string, any>): void {
    this.info(`Performance: ${operation}`, module, {
      operation,
      duration_ms: durationMs,
      ...extra,
    });
  }

  // API request logging
  logApiRequest(
    method: string,
    url: string,
    statusCode: number,
    durationMs: number,
    extra?: Record<string, any>
  ): void {
    // Only log errors and warnings (400+ status codes) to reduce noise
    if (statusCode >= 400) {
      const level = statusCode >= 500 ? 'error' : 'warn';
      this.log(level, `API ${method} ${url} -> ${statusCode}`, 'api', {
        method,
        url,
        status_code: statusCode,
        duration_ms: durationMs,
        ...extra,
      });
    }
  }

  // Get all logs (for debugging/export)
  getAllLogs(): LogEntry[] {
    return this.getStoredLogs();
  }

  // Get logs filtered by level
  getLogsByLevel(level: LogLevel): LogEntry[] {
    return this.getStoredLogs().filter(log => log.level === level);
  }

  // Get logs for a specific request ID
  getLogsByRequestId(requestId: string): LogEntry[] {
    return this.getStoredLogs().filter(log => log.requestId === requestId);
  }

  // Export logs as JSON string
  exportLogs(): string {
    return JSON.stringify(this.getStoredLogs(), null, 2);
  }

  // Clear all logs
  clearLogs(): void {
    localStorage.removeItem(this.logKey);
  }

  // Start periodic log sending
  private startLogSending(): void {
    // Only start if we're in the browser
    if (typeof window === 'undefined') return;
    
    // Send logs on page unload
    window.addEventListener('beforeunload', () => {
      this.sendLogsToBackend(true); // Synchronous send on unload
    });
    
    // Send logs on visibility change (user switches tabs)
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden' && this.pendingLogs.length > 0) {
        this.sendLogsToBackend();
      }
    });
  }

  // Schedule batch send of logs
  private scheduleBatchSend(): void {
    // If we have enough logs or there's no existing timeout, send immediately
    if (this.pendingLogs.length >= this.maxBatchSize) {
      this.sendLogsToBackend();
      return;
    }

    // Otherwise, schedule a send if not already scheduled
    if (!this.batchTimeout) {
      this.batchTimeout = setTimeout(() => {
        this.sendLogsToBackend();
      }, this.batchDelayMs);
    }
  }

  // Send logs to backend API
  private async sendLogsToBackend(sync: boolean = false): Promise<void> {
    if (this.pendingLogs.length === 0) return;
    
    const logsToSend = [...this.pendingLogs];
    this.pendingLogs = [];
    
    // Clear timeout
    if (this.batchTimeout) {
      clearTimeout(this.batchTimeout);
      this.batchTimeout = null;
    }

    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    const url = `${apiBaseUrl}/api/logs/frontend`;
    
    const payload = {
      logs: logsToSend.map(log => ({
        timestamp: log.timestamp,
        level: log.level,
        message: log.message,
        module: log.module,
        requestId: log.requestId,
        extra: log.extra,
        error: log.error,
      })),
      source: 'frontend'
    };

    try {
      if (sync) {
        // Use sendBeacon for synchronous sending during page unload
        const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });
        navigator.sendBeacon(url, blob);
      } else {
        // Use fetch for normal async sending
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          console.warn('Failed to send logs to backend:', response.statusText);
          // Re-add logs to pending if send failed (but don't infinitely retry)
        }
      }
    } catch (error) {
      console.warn('Error sending logs to backend:', error);
      // Could implement retry logic here if needed
    }
  }

  // Force send all pending logs immediately
  flushLogs(): Promise<void> {
    return this.sendLogsToBackend();
  }

  // Get log statistics
  getLogStats(): {
    total: number;
    byLevel: Record<LogLevel, number>;
    oldestTimestamp?: string;
    newestTimestamp?: string;
  } {
    const logs = this.getStoredLogs();
    const stats = {
      total: logs.length,
      byLevel: {
        debug: 0,
        info: 0,
        warn: 0,
        error: 0,
      } as Record<LogLevel, number>,
      oldestTimestamp: logs[0]?.timestamp,
      newestTimestamp: logs[logs.length - 1]?.timestamp,
    };

    logs.forEach(log => {
      stats.byLevel[log.level]++;
    });

    return stats;
  }
}

// Create singleton logger instance
export const logger = new FrontendLogger();

// Hook for React components to use the logger with module context
export function useLogger(module: string) {
  return {
    debug: (message: string, extra?: Record<string, any>) => logger.debug(message, module, extra),
    info: (message: string, extra?: Record<string, any>) => logger.info(message, module, extra),
    warn: (message: string, extra?: Record<string, any>) => logger.warn(message, module, extra),
    error: (message: string, extra?: Record<string, any>, error?: Error) => logger.error(message, module, extra, error),
    logPerformance: (operation: string, durationMs: number, extra?: Record<string, any>) => 
      logger.logPerformance(operation, durationMs, module, extra),
  };
}

// Global error handler for unhandled errors and promise rejections
if (typeof window !== 'undefined') {
  window.addEventListener('error', (event) => {
    logger.error('Unhandled error', 'global', {
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
    }, event.error);
  });

  window.addEventListener('unhandledrejection', (event) => {
    logger.error('Unhandled promise rejection', 'global', {
      reason: event.reason,
    });
  });
}