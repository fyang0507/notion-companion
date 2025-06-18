import logging
import logging.handlers
import os
import json
import uuid
from datetime import datetime
from contextvars import ContextVar
from typing import Dict, Any, Optional

# Context variable for request correlation ID
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)

class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Base log structure
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add request ID if available
        request_id = request_id_var.get()
        if request_id:
            log_entry['request_id'] = request_id
            
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            
        # Add extra fields from the log record
        extra_fields = {k: v for k, v in record.__dict__.items() 
                       if k not in {'name', 'msg', 'args', 'levelname', 'levelno', 
                                   'pathname', 'filename', 'module', 'lineno', 
                                   'funcName', 'created', 'msecs', 'relativeCreated', 
                                   'thread', 'threadName', 'processName', 'process',
                                   'message', 'exc_info', 'exc_text', 'stack_info'}}
        
        if extra_fields:
            log_entry['extra'] = extra_fields
            
        return json.dumps(log_entry, ensure_ascii=False)

def setup_logging():
    """Configure logging for the application"""
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(__file__), '../logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation for all logs
    file_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, 'app.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(file_handler)
    
    # Separate error log file
    error_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, 'errors.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(error_handler)
    
    # API request logs
    api_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, 'api.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    api_handler.setLevel(logging.INFO)
    api_handler.setFormatter(StructuredFormatter())
    
    # Create API logger
    api_logger = logging.getLogger('api')
    api_logger.addHandler(api_handler)
    api_logger.setLevel(logging.INFO)
    
    # Performance logs for slow operations
    perf_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, 'performance.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=3,
        encoding='utf-8'
    )
    perf_handler.setLevel(logging.INFO)
    perf_handler.setFormatter(StructuredFormatter())
    
    perf_logger = logging.getLogger('performance')
    perf_logger.addHandler(perf_handler)
    perf_logger.setLevel(logging.INFO)
    
    # Reduce noise from third-party libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.INFO)
    logging.getLogger('supabase').setLevel(logging.INFO)
    
    logging.info("Logging system initialized", extra={
        'log_dir': log_dir,
        'handlers': [h.__class__.__name__ for h in root_logger.handlers]
    })

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(name)

def set_request_id(request_id: Optional[str] = None) -> str:
    """Set request ID for the current context"""
    if request_id is None:
        request_id = str(uuid.uuid4())[:8]
    request_id_var.set(request_id)
    return request_id

def get_request_id() -> Optional[str]:
    """Get the current request ID"""
    return request_id_var.get()

def log_performance(operation: str, duration_ms: float, **kwargs):
    """Log performance metrics"""
    perf_logger = logging.getLogger('performance')
    perf_logger.info(f"Performance: {operation}", extra={
        'operation': operation,
        'duration_ms': duration_ms,
        **kwargs
    })

def log_api_request(method: str, path: str, status_code: int, duration_ms: float, **kwargs):
    """Log API request details"""
    api_logger = logging.getLogger('api')
    api_logger.info(f"API {method} {path} -> {status_code}", extra={
        'method': method,
        'path': path,
        'status_code': status_code,
        'duration_ms': duration_ms,
        **kwargs
    })