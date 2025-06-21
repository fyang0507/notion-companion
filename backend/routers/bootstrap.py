"""
Bootstrap Router - Single Database Model

This webapp is designed to support ONLY ONE Notion workspace with multiple databases.
No workspace concept exists - all operations are per-database.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from database import get_db
from services.openai_service import get_openai_service
from services.document_processor import get_document_processor
from services.notion_service import get_notion_service
from typing import Dict, Any, Optional, List
import asyncio
import uuid
import os

router = APIRouter()

class DatabaseConfig(BaseModel):
    database_id: str
    name: str
    batch_size: int = 10

class BootstrapRequest(BaseModel):
    database_configs: List[DatabaseConfig]
    batch_size: int = 10

class BootstrapResponse(BaseModel):
    success: bool
    message: str
    job_id: Optional[str] = None

class BootstrapStatusResponse(BaseModel):
    job_id: str
    status: str  # 'running', 'completed', 'failed'
    progress: Dict[str, Any]

# In-memory job tracking (in production, use Redis or database)
bootstrap_jobs = {}

@router.post("/bootstrap", response_model=BootstrapResponse)
async def start_bootstrap(request: BootstrapRequest, background_tasks: BackgroundTasks):
    """
    Start the bootstrap process to load Notion databases.
    Single database model - no workspace concept.
    """
    try:
        # Get Notion access token from environment (single workspace model)
        notion_access_token = os.getenv('NOTION_ACCESS_TOKEN')
        if not notion_access_token:
            raise HTTPException(status_code=400, detail="NOTION_ACCESS_TOKEN not configured")
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Initialize job tracking
        bootstrap_jobs[job_id] = {
            'status': 'running',
            'progress': {
                'total_databases': len(request.database_configs),
                'processed_databases': 0,
                'total_pages': 0,
                'processed_pages': 0,
                'failed_pages': 0,
                'errors': [],
                'started_at': None,
                'completed_at': None
            }
        }
        
        # Start background task
        background_tasks.add_task(
            run_bootstrap_process,
            job_id,
            request.database_configs,
            notion_access_token,
            request.batch_size
        )
        
        return BootstrapResponse(
            success=True,
            message="Bootstrap process started. Use the job ID to check progress.",
            job_id=job_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start bootstrap: {str(e)}")

@router.get("/bootstrap/{job_id}/status", response_model=BootstrapStatusResponse)
async def get_bootstrap_status(job_id: str):
    """Get the status of a bootstrap job."""
    if job_id not in bootstrap_jobs:
        raise HTTPException(status_code=404, detail="Bootstrap job not found")
    
    job = bootstrap_jobs[job_id]
    
    return BootstrapStatusResponse(
        job_id=job_id,
        status=job['status'],
        progress=job['progress']
    )

@router.delete("/bootstrap/{job_id}")
async def cancel_bootstrap(job_id: str):
    """Cancel a running bootstrap job."""
    if job_id not in bootstrap_jobs:
        raise HTTPException(status_code=404, detail="Bootstrap job not found")
    
    # Mark as cancelled
    bootstrap_jobs[job_id]['status'] = 'cancelled'
    
    return {"success": True, "message": "Bootstrap job marked for cancellation"}

async def run_bootstrap_process(job_id: str, database_configs: List[DatabaseConfig], 
                               access_token: str, batch_size: int):
    """
    Background task to run the bootstrap process.
    Single database model - no workspace concept.
    """
    from datetime import datetime
    
    try:
        # Update job status
        bootstrap_jobs[job_id]['progress']['started_at'] = datetime.utcnow().isoformat()
        
        # Initialize services
        db = get_db()
        openai_service = get_openai_service()
        document_processor = get_document_processor(openai_service, db)
        notion_service = get_notion_service(access_token)
        
        # Run the processing
        results = await document_processor.process_databases(
            database_configs=[{
                'database_id': config.database_id,
                'name': config.name,
                'sync_settings': {'batch_size': config.batch_size}
            } for config in database_configs],
            notion_service=notion_service,
            batch_size=batch_size
        )
        
        # Update job with results
        bootstrap_jobs[job_id]['progress'].update(results)
        bootstrap_jobs[job_id]['progress']['completed_at'] = datetime.utcnow().isoformat()
        bootstrap_jobs[job_id]['status'] = 'completed'
        
    except Exception as e:
        # Mark job as failed
        bootstrap_jobs[job_id]['status'] = 'failed'
        bootstrap_jobs[job_id]['progress']['error'] = str(e)
        bootstrap_jobs[job_id]['progress']['completed_at'] = datetime.utcnow().isoformat()

@router.get("/databases/stats")
async def get_database_stats():
    """
    Get statistics about indexed databases.
    Single database model - no workspace concept.
    """
    try:
        db = get_db()
        
        # Get all documents
        doc_response = db.client.table('documents').select(
            'id, title, database_id, created_at, extracted_metadata'
        ).execute()
        
        documents = doc_response.data
        
        # Get chunk count by counting chunks for all documents
        if documents:
            chunk_response = db.client.table('document_chunks').select(
                'id', count='exact'
            ).in_('document_id', [doc['id'] for doc in documents]).execute()
            chunk_count = chunk_response.count or 0
        else:
            chunk_count = 0
        
        # Calculate statistics by database
        database_stats = {}
        total_tokens = 0
        chunked_documents = 0
        
        for doc in documents:
            db_id = doc['database_id']
            if db_id not in database_stats:
                database_stats[db_id] = {
                    'document_count': 0,
                    'token_count': 0,
                    'chunked_documents': 0
                }
            
            database_stats[db_id]['document_count'] += 1
            
            doc_tokens = doc.get('extracted_metadata', {}).get('token_count', 0)
            database_stats[db_id]['token_count'] += doc_tokens
            total_tokens += doc_tokens
            
            if doc.get('extracted_metadata', {}).get('is_chunked', False):
                database_stats[db_id]['chunked_documents'] += 1
                chunked_documents += 1
        
        return {
            'total_documents': len(documents),
            'chunked_documents': chunked_documents,
            'total_chunks': chunk_count,
            'total_tokens': total_tokens,
            'database_stats': database_stats,
            'documents': [
                {
                    'id': doc['id'],
                    'title': doc['title'],
                    'database_id': doc['database_id'],
                    'created_at': doc['created_at'],
                    'token_count': doc.get('extracted_metadata', {}).get('token_count', 0),
                    'chunk_count': doc.get('extracted_metadata', {}).get('chunk_count', 1),
                    'is_chunked': doc.get('extracted_metadata', {}).get('is_chunked', False)
                }
                for doc in documents
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get database stats: {str(e)}")

@router.delete("/databases/{database_id}/documents")
async def clear_database_documents(database_id: str):
    """
    Clear all documents and chunks for a specific database.
    Single database model - no workspace concept.
    """
    try:
        db = get_db()
        
        # Delete all documents for this database (chunks cascade automatically)
        db.client.table('documents').delete().eq('database_id', database_id).execute()
        
        return {"success": True, "message": f"All documents cleared for database {database_id}"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear database documents: {str(e)}")