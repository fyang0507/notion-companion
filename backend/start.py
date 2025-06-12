#!/usr/bin/env python3
"""
FastAPI Backend Startup Script
"""
import uvicorn
import os
from pathlib import Path

if __name__ == "__main__":
    # Change to backend directory
    os.chdir(Path(__file__).parent)
    
    # Run with hot reload in development
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["./"]
    )