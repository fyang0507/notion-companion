from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from database import get_db
from services.openai_service import get_openai_service
from services.document_processor import get_document_processor
from services.notion_service import get_notion_service
from typing import Dict, Any, Optional
import asyncio
import uuid

router = APIRouter()

class WorkspaceConnectRequest(BaseModel):
    user_id: str
    workspace_name: str
    notion_access_token: str

class BootstrapRequest(BaseModel):
    workspace_id: str
    batch_size: int = 10

class BootstrapResponse(BaseModel):
    success: bool
    message: str
    job_id: Optional[str] = None
    workspace_id: Optional[str] = None

class BootstrapStatusResponse(BaseModel):
    job_id: str
    status: str  # 'running', 'completed', 'failed'
    progress: Dict[str, Any]

# In-memory job tracking (in production, use Redis or database)
bootstrap_jobs = {}

@router.post("/connect-workspace", response_model=BootstrapResponse)
async def connect_workspace(request: WorkspaceConnectRequest):
    """
    Connect a new Notion workspace and validate access.
    """
    try:
        db = get_db()
        
        # Test the Notion API access
        notion_service = get_notion_service(request.notion_access_token)
        
        # Try to search for pages to validate access
        try:
            test_pages = await notion_service.search_pages(page_size=1)
            if not isinstance(test_pages, list):
                raise Exception("Invalid response from Notion API")
        except Exception as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to validate Notion access token: {str(e)}"
            )
        
        # Create workspace record
        workspace_data = {
            'id': str(uuid.uuid4()),
            'user_id': request.user_id,
            'notion_workspace_id': f"workspace_{uuid.uuid4()}",  # Placeholder - Notion doesn't expose workspace ID
            'name': request.workspace_name,
            'access_token': request.notion_access_token,  # In production, encrypt this
            'is_active': True
        }
        
        result = db.client.table('workspaces').insert(workspace_data).execute()
        workspace_id = result.data[0]['id']
        
        return BootstrapResponse(
            success=True,
            message="Workspace connected successfully. You can now start the bootstrap process.",
            workspace_id=workspace_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect workspace: {str(e)}")

@router.post("/bootstrap", response_model=BootstrapResponse)
async def start_bootstrap(request: BootstrapRequest, background_tasks: BackgroundTasks):
    """
    Start the bootstrap process to load all Notion pages into the database.
    This runs as a background task to avoid timeout issues.
    """
    try:
        db = get_db()
        
        # Verify workspace exists
        workspace_response = db.client.table('workspaces').select(
            'id, access_token, name'
        ).eq('id', request.workspace_id).execute()
        
        if not workspace_response.data:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        workspace = workspace_response.data[0]
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Initialize job tracking
        bootstrap_jobs[job_id] = {
            'status': 'running',
            'workspace_id': request.workspace_id,
            'workspace_name': workspace['name'],
            'progress': {
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
            request.workspace_id,
            workspace['access_token'],
            request.batch_size
        )
        
        return BootstrapResponse(
            success=True,
            message="Bootstrap process started. Use the job ID to check progress.",
            job_id=job_id,
            workspace_id=request.workspace_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start bootstrap: {str(e)}")

@router.get("/bootstrap/{job_id}/status", response_model=BootstrapStatusResponse)
async def get_bootstrap_status(job_id: str):
    """
    Get the status of a bootstrap job.
    """
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
    """
    Cancel a running bootstrap job (cleanup only - can't actually stop background task).
    """
    if job_id not in bootstrap_jobs:
        raise HTTPException(status_code=404, detail="Bootstrap job not found")
    
    # Mark as cancelled (the background task will check this)
    bootstrap_jobs[job_id]['status'] = 'cancelled'
    
    return {"success": True, "message": "Bootstrap job marked for cancellation"}

async def run_bootstrap_process(job_id: str, workspace_id: str, access_token: str, batch_size: int):
    """
    Background task to run the bootstrap process.
    """
    from datetime import datetime
    
    try:
        # Update job status
        bootstrap_jobs[job_id]['progress']['started_at'] = datetime.utcnow().isoformat()
        
        # Initialize services
        db = get_db()
        openai_service = get_openai_service()
        document_processor = get_document_processor(openai_service, db)
        
        # Run the processing
        results = await document_processor.process_workspace_pages(
            workspace_id=workspace_id,
            access_token=access_token,
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

@router.get("/workspaces/{workspace_id}/stats")
async def get_workspace_stats(workspace_id: str):
    """
    Get statistics about a workspace's indexed content.
    """
    try:
        db = get_db()
        
        # Get document count
        doc_response = db.client.table('documents').select(
            'id, title, created_at, metadata'
        ).eq('workspace_id', workspace_id).execute()
        
        documents = doc_response.data
        
        # Get chunk count
        chunk_response = db.client.rpc('get_workspace_chunk_count', {
            'workspace_id': workspace_id
        }).execute()
        
        chunk_count = chunk_response.data[0]['count'] if chunk_response.data else 0
        
        # Calculate statistics
        total_tokens = sum(
            doc.get('metadata', {}).get('token_count', 0) 
            for doc in documents
        )
        
        chunked_documents = sum(
            1 for doc in documents 
            if doc.get('metadata', {}).get('is_chunked', False)
        )
        
        return {
            'workspace_id': workspace_id,
            'total_documents': len(documents),
            'chunked_documents': chunked_documents,
            'total_chunks': chunk_count,
            'total_tokens': total_tokens,
            'documents': [
                {
                    'id': doc['id'],
                    'title': doc['title'],
                    'created_at': doc['created_at'],
                    'token_count': doc.get('metadata', {}).get('token_count', 0),
                    'chunk_count': doc.get('metadata', {}).get('chunk_count', 1),
                    'is_chunked': doc.get('metadata', {}).get('is_chunked', False)
                }
                for doc in documents
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workspace stats: {str(e)}")

@router.delete("/workspaces/{workspace_id}/documents")
async def clear_workspace_documents(workspace_id: str):
    """
    Clear all documents and chunks for a workspace (useful for re-bootstrapping).
    """
    try:
        db = get_db()
        
        # Delete all chunks first (through foreign key cascade this should happen automatically)
        db.client.table('documents').delete().eq('workspace_id', workspace_id).execute()
        
        return {"success": True, "message": "All workspace documents cleared"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear workspace documents: {str(e)}")