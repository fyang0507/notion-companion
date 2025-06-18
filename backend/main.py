from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import time
from dotenv import load_dotenv

from routers import chat, search, notion_webhook, bootstrap
from database import init_db
from logging_config import setup_logging, set_request_id, log_api_request, get_logger

load_dotenv(dotenv_path="../.env")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger = get_logger(__name__)
    logger.info("Starting Notion Companion API")
    await init_db()
    logger.info("Database initialized successfully")
    yield
    # Shutdown
    logger.info("Shutting down Notion Companion API")

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
    
    # Log incoming request
    logger = get_logger("api")
    logger.info(f"Request started: {request.method} {request.url.path}", extra={
        'method': request.method,
        'path': request.url.path,
        'query_params': str(request.query_params),
        'client_ip': request.client.host if request.client else None,
        'user_agent': request.headers.get('user-agent'),
        'request_id': request_id
    })
    
    # Process request
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        
        # Log successful response
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

@app.get("/")
async def root():
    return {"message": "Notion Companion API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)