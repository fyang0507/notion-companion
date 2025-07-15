"""
Notion Webhook Router - Single Database Model

This webapp is designed to support ONLY ONE Notion workspace and multiple databases.
No workspace concept exists - all operations are per-database.
"""

from fastapi import APIRouter, HTTPException
from storage.database import get_db
from ingestion.services.openai_service import get_openai_service
from ingestion.services.document_processor import get_document_processor
from ingestion.services.notion_service import get_notion_service
from api.models.models import NotionWebhookPayload, WebhookResponse
from typing import Dict, Any
import os

router = APIRouter()

@router.post("/webhook", response_model=WebhookResponse)
async def notion_webhook(payload: NotionWebhookPayload):
    """
    Handle Notion webhook events for page updates/creation/deletion.
    Single database model - no workspace concept.
    """
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
    """Handle page update events"""
    db = get_db()
    notion_page_id = page_data.get('id')
    archived = page_data.get('archived', False)
    
    if archived:
        # Remove from database if archived
        db.delete_document(notion_page_id)
        return
    
    # Get Notion access token from environment (single workspace model)
    notion_access_token = os.getenv('NOTION_ACCESS_TOKEN')
    if not notion_access_token:
        raise Exception("NOTION_ACCESS_TOKEN not configured")
    
    # Get Notion service
    notion_service = get_notion_service(notion_access_token)
    
    # Get updated page content
    title = notion_service.extract_title_from_page(page_data)
    content = await notion_service.get_page_content(notion_page_id)
    
    # Find the database this page belongs to
    database_id = await find_database_for_page(notion_page_id, notion_service)
    if not database_id:
        raise Exception(f"No database found for page {notion_page_id}")
    
    # Process the updated document
    openai_service = get_openai_service()
    document_processor = get_document_processor(openai_service, db)
    
    await document_processor.update_document(
        database_id=database_id,
        page_data=page_data,
        content=content,
        title=title
    )

async def handle_page_created(page_data: Dict[str, Any]):
    """Handle page creation events"""
    await handle_page_update(page_data)

async def handle_page_deleted(page_data: Dict[str, Any]):
    """Handle page deletion events"""
    db = get_db()
    notion_page_id = page_data.get('id')
    db.delete_document(notion_page_id)

async def find_database_for_page(notion_page_id: str, notion_service) -> str:
    """
    Find the database ID that contains this Notion page.
    Single database model - no workspace concept.
    """
    db = get_db()
    
    # First, check if we already have this page in our database
    doc_response = db.client.table('documents').select(
        'database_id'
    ).eq('notion_page_id', notion_page_id).execute()
    
    if doc_response.data:
        return doc_response.data[0]['database_id']
    
    # If page not found, get database from Notion API
    try:
        page = await notion_service.get_page(notion_page_id)
        if page and page.get('parent', {}).get('database_id'):
            return page['parent']['database_id']
    except:
        pass
    
    return None