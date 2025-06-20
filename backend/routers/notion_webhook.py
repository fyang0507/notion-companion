from fastapi import APIRouter, HTTPException
from database_v3 import get_db
from services.openai_service import get_openai_service
from services.document_processor import get_document_processor
from services.notion_service import get_notion_service
from models import NotionWebhookPayload, WebhookResponse
from typing import Dict, Any

router = APIRouter()

@router.post("/webhook", response_model=WebhookResponse)
async def notion_webhook(payload: NotionWebhookPayload):
    try:
        if payload.object == "page" and payload.event_type == "updated":
            await handle_page_update(payload.data)
        elif payload.object == "page" and payload.event_type == "created":
            await handle_page_created(payload.data)
        elif payload.object == "page" and payload.event_type == "deleted":
            await handle_page_deleted(payload.data)
        
        return WebhookResponse(success=True)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")

async def handle_page_update(page_data: Dict[str, Any]):
    db = get_db()
    notion_page_id = page_data.get('id')
    archived = page_data.get('archived', False)
    
    if archived:
        # Remove from database if archived
        db.delete_document(notion_page_id)
        return
    
    # Find the workspace for this page
    workspace = await find_workspace_for_page(notion_page_id)
    if not workspace:
        raise Exception(f"No workspace found for page {notion_page_id}")
    
    # Get Notion service for this workspace
    notion_service = get_notion_service(workspace['access_token'])
    
    # Get updated page content
    title = notion_service.extract_title_from_page(page_data)
    content = await notion_service.get_page_content(notion_page_id)
    
    # Process the updated document
    openai_service = get_openai_service()
    document_processor = get_document_processor(openai_service, db)
    
    await document_processor.update_document(
        workspace_id=workspace['id'],
        page_data=page_data,
        content=content,
        title=title
    )

async def handle_page_created(page_data: Dict[str, Any]):
    # Similar to handlePageUpdate but for new pages
    await handle_page_update(page_data)

async def handle_page_deleted(page_data: Dict[str, Any]):
    db = get_db()
    notion_page_id = page_data.get('id')
    db.delete_document(notion_page_id)

async def find_workspace_for_page(notion_page_id: str) -> Dict[str, Any]:
    """
    Find the workspace that contains this Notion page.
    This is needed because webhooks don't include workspace information.
    """
    db = get_db()
    
    # First, check if we already have this page in our database
    doc_response = db.client.table('documents').select(
        'workspace_id'
    ).eq('notion_page_id', notion_page_id).execute()
    
    if doc_response.data:
        workspace_id = doc_response.data[0]['workspace_id']
        workspace_response = db.client.table('workspaces').select(
            'id, access_token, name'
        ).eq('id', workspace_id).execute()
        
        if workspace_response.data:
            return workspace_response.data[0]
    
    # If page not found in our database, try all active workspaces
    # This can happen for newly created pages
    workspaces_response = db.client.table('workspaces').select(
        'id, access_token, name'
    ).eq('is_active', True).execute()
    
    for workspace in workspaces_response.data:
        try:
            notion_service = get_notion_service(workspace['access_token'])
            # Try to fetch the page to see if it exists in this workspace
            page = await notion_service.get_page(notion_page_id)
            if page:
                return workspace
        except:
            # Page not found in this workspace, continue
            continue
    
    return None