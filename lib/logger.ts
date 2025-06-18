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
  
  constructor() {
    // Clean up old logs on startup
    this.cleanupOldLogs();
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
    const level = statusCode >= 400 ? 'error' : 'info';
    this.log(level, `API ${method} ${url} -> ${statusCode}`, 'api', {
      method,
      url,
      status_code: statusCode,
      duration_ms: durationMs,
      ...extra,
    });
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