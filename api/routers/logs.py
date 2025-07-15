"""
API router for receiving and processing frontend logs
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from shared.logging.logging_config import get_logger, set_request_id

router = APIRouter()
logger = get_logger(__name__)

class FrontendLogEntry(BaseModel):
    timestamp: str
    level: str  # 'debug' | 'info' | 'warn' | 'error'
    message: str
    module: Optional[str] = None
    requestId: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

class FrontendLogBatch(BaseModel):
    logs: List[FrontendLogEntry]
    source: str = "frontend"

@router.post("/logs/frontend")
async def receive_frontend_logs(log_batch: FrontendLogBatch):
    """
    Receive and process frontend logs, writing them to backend log files
    """
    try:
        processed_count = 0
        error_count = 0
        
        for log_entry in log_batch.logs:
            try:
                # Set request ID for correlation if available
                if log_entry.requestId:
                    set_request_id(log_entry.requestId)
                
                # Map frontend log levels to Python logging levels
                level_mapping = {
                    'debug': logging.DEBUG,
                    'info': logging.INFO,
                    'warn': logging.WARNING,
                    'error': logging.ERROR
                }
                
                python_level = level_mapping.get(log_entry.level, logging.INFO)
                
                # Only process WARNING and ERROR levels (matching our new backend policy)
                if python_level < logging.WARNING:
                    continue
                    
                # Create a frontend-specific logger
                frontend_logger = get_logger(f'frontend.{log_entry.module or "unknown"}')
                
                # Prepare log message with frontend context
                message = f"[FRONTEND] {log_entry.message}"
                
                # Prepare extra data
                extra_data = {
                    'source': 'frontend',
                    'frontend_timestamp': log_entry.timestamp,
                    'frontend_level': log_entry.level,
                    **(log_entry.extra or {})
                }
                
                # Handle error information
                if log_entry.error:
                    extra_data['frontend_error'] = log_entry.error
                    
                # Log with appropriate level
                if python_level == logging.DEBUG:
                    frontend_logger.debug(message, extra=extra_data)
                elif python_level == logging.INFO:
                    frontend_logger.info(message, extra=extra_data)
                elif python_level == logging.WARNING:
                    frontend_logger.warning(message, extra=extra_data)
                elif python_level == logging.ERROR:
                    frontend_logger.error(message, extra=extra_data)
                    
                processed_count += 1
                
            except Exception as e:
                error_count += 1
                logger.error(f"Failed to process frontend log entry: {e}", extra={
                    'log_entry': log_entry.model_dump(),
                    'error': str(e)
                })
        
        # Log summary of batch processing
        if processed_count > 0 or error_count > 0:
            logger.warning(f"Processed frontend log batch", extra={
                'total_logs': len(log_batch.logs),
                'processed': processed_count,
                'errors': error_count,
                'source': log_batch.source
            })
        
        return {
            "status": "success",
            "processed": processed_count,
            "errors": error_count,
            "total": len(log_batch.logs)
        }
        
    except Exception as e:
        logger.error(f"Failed to process frontend log batch: {e}")
        raise HTTPException(status_code=500, detail="Failed to process logs")