// Separate frontend error logging system for better error tracking
// This complements the main logger but focuses specifically on frontend errors

interface FrontendError {
  timestamp: string;
  type: 'hook_error' | 'api_error' | 'component_error' | 'global_error';
  module: string;
  message: string;
  stack?: string;
  context?: Record<string, any>;
  user_agent?: string;
  url?: string;
}

class FrontendErrorLogger {
  private readonly maxErrors = 100;
  private readonly storageKey = 'frontend-errors';

  private getStoredErrors(): FrontendError[] {
    try {
      const errors = localStorage.getItem(this.storageKey);
      return errors ? JSON.parse(errors) : [];
    } catch {
      return [];
    }
  }

  private storeErrors(errors: FrontendError[]): void {
    try {
      const trimmed = errors.slice(-this.maxErrors);
      localStorage.setItem(this.storageKey, JSON.stringify(trimmed));
    } catch (error) {
      console.warn('Failed to store frontend errors:', error);
    }
  }

  logError(
    type: FrontendError['type'],
    module: string,
    message: string,
    error?: Error,
    context?: Record<string, any>
  ): void {
    const frontendError: FrontendError = {
      timestamp: new Date().toISOString(),
      type,
      module,
      message,
      stack: error?.stack,
      context,
      user_agent: navigator.userAgent,
      url: window.location.href,
    };

    // Store the error
    const errors = this.getStoredErrors();
    errors.push(frontendError);
    this.storeErrors(errors);

    // Also log to console for development
    console.error(`[FE ERROR] ${type} in ${module}: ${message}`, {
      error,
      context,
      timestamp: frontendError.timestamp,
    });
  }

  getErrors(): FrontendError[] {
    return this.getStoredErrors();
  }

  getErrorsByType(type: FrontendError['type']): FrontendError[] {
    return this.getStoredErrors().filter(err => err.type === type);
  }

  clearErrors(): void {
    localStorage.removeItem(this.storageKey);
  }

  exportErrors(): string {
    return JSON.stringify(this.getStoredErrors(), null, 2);
  }

  getErrorStats(): {
    total: number;
    byType: Record<FrontendError['type'], number>;
    byModule: Record<string, number>;
  } {
    const errors = this.getStoredErrors();
    const stats = {
      total: errors.length,
      byType: {
        hook_error: 0,
        api_error: 0,
        component_error: 0,
        global_error: 0,
      } as Record<FrontendError['type'], number>,
      byModule: {} as Record<string, number>,
    };

    errors.forEach(error => {
      stats.byType[error.type]++;
      stats.byModule[error.module] = (stats.byModule[error.module] || 0) + 1;
    });

    return stats;
  }
}

export const frontendErrorLogger = new FrontendErrorLogger();

// Hook for React components
export function useFrontendErrorLogger(module: string) {
  return {
    logHookError: (message: string, error?: Error, context?: Record<string, any>) =>
      frontendErrorLogger.logError('hook_error', module, message, error, context),
    
    logApiError: (message: string, error?: Error, context?: Record<string, any>) =>
      frontendErrorLogger.logError('api_error', module, message, error, context),
    
    logComponentError: (message: string, error?: Error, context?: Record<string, any>) =>
      frontendErrorLogger.logError('component_error', module, message, error, context),
  };
}

// Global error capture for unhandled frontend errors
if (typeof window !== 'undefined') {
  window.addEventListener('error', (event) => {
    frontendErrorLogger.logError(
      'global_error',
      'window',
      event.message || 'Unhandled error',
      event.error,
      {
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
      }
    );
  });

  window.addEventListener('unhandledrejection', (event) => {
    frontendErrorLogger.logError(
      'global_error',
      'promise',
      'Unhandled promise rejection',
      event.reason instanceof Error ? event.reason : undefined,
      {
        reason: event.reason,
      }
    );
  });
}