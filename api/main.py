from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import time
from dotenv import load_dotenv

import sys
import os
# Add the parent directory to the Python path to access the modular structure
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .routers import chat, search, notion_webhook, bootstrap, chat_sessions, logs, metadata
from storage.database import init_db
from shared.logging.logging_config import setup_logging, set_request_id, log_api_request, get_logger
from rag.services.chat_session_service import get_chat_session_service

load_dotenv(dotenv_path=".env")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Check if this is a development session and clear logs
    is_dev = os.getenv("NODE_ENV") == "development" or os.getenv("CLEAR_LOGS", "").lower() == "true"
    setup_logging(clear_logs=is_dev)
    logger = get_logger(__name__)
    logger.warning("Starting Notion Companion API")
    
    # Initialize database with robust error handling
    logger.warning("Initializing database connection...")
    try:
        await init_db()
        
        # Verify database connection is working
        from storage.database import get_db
        db = get_db()
        if db.client is None:
            raise RuntimeError("Database client is None after initialization")
        
        # Test database connectivity
        try:
            databases = db.get_notion_databases()
            logger.warning(f"✅ Database initialized successfully - {len(databases)} Notion databases found")
        except Exception as db_test_error:
            logger.error(f"Database connection test failed: {db_test_error}")
            raise RuntimeError(f"Database connectivity test failed: {db_test_error}")
            
    except Exception as e:
        logger.error(f"❌ CRITICAL: Database initialization failed: {e}")
        logger.error("Application cannot start without database connection")
        raise RuntimeError(f"Database initialization failed: {e}") from e
    
    # Start chat session idle monitoring
    chat_service = get_chat_session_service()
    await chat_service.start_idle_monitoring()
    logger.warning("Chat session idle monitoring started")
    logger.warning("🚀 Notion Companion API started successfully - all systems ready")
    
    yield
    
    # Shutdown
    await chat_service.stop_idle_monitoring()
    logger.warning("Chat session idle monitoring stopped")
    logger.warning("Shutting down Notion Companion API")

app = FastAPI(
    title="Notion Companion API",
    description="FastAPI backend for Notion RAG application",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Set request ID for this request context
    request_id = set_request_id()
    
    # Track request start time
    start_time = time.time()
    
    # Only log request start for debugging purposes (now filtered at WARNING level)
    logger = get_logger("api")
    
    # Process request
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        
        # Only log errors and slow requests (>1s) to reduce noise
        if response.status_code >= 400 or duration_ms > 1000:
            log_api_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                request_id=request_id
            )
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        return response
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        
        # Log error
        logger.error(f"Request failed: {request.method} {request.url.path}", extra={
            'method': request.method,
            'path': request.url.path,
            'duration_ms': duration_ms,
            'error': str(e),
            'request_id': request_id
        }, exc_info=True)
        
        raise

# Include routers
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(notion_webhook.router, prefix="/api/notion", tags=["notion"])
app.include_router(bootstrap.router, prefix="/api/bootstrap", tags=["bootstrap"])
app.include_router(chat_sessions.router)
app.include_router(logs.router, prefix="/api", tags=["logs"])
app.include_router(metadata.router, tags=["metadata"])

@app.get("/")
async def root():
    return {
        "name": "Notion Companion API",
        "version": "1.0.0",
        "status": "healthy",
        "message": "FastAPI backend for Notion RAG application"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)