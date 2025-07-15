#!/usr/bin/env python3
"""
FastAPI Backend Startup Script
"""
import uvicorn
import os
import sys
from pathlib import Path

if __name__ == "__main__":
    # Change to project root directory
    os.chdir(Path(__file__).parent)
    
    # Add project root to Python path
    sys.path.insert(0, str(Path(__file__).parent))
    
    # Run with hot reload in development
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["./api", "./rag", "./storage", "./shared", "./ingestion"]
    ) 