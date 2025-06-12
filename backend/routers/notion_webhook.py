from fastapi import APIRouter, HTTPException
from database import get_db
from services.openai_service import get_openai_service
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
    openai_service = get_openai_service()
    
    notion_page_id = page_data.get('id')
    properties = page_data.get('properties', {})
    archived = page_data.get('archived', False)
    
    if archived:
        # Remove from database if archived
        await db.delete_document(notion_page_id)
        return
    
    # Extract content and generate embedding
    title = extract_title(properties)
    content = await extract_page_content(notion_page_id)
    embedding_response = await openai_service.generate_embedding(f"{title}\n{content}")
    
    # Update or insert document
    document_data = {
        'notion_page_id': notion_page_id,
        'title': title,
        'content': content,
        'embedding': embedding_response.embedding,
        'metadata': {
            'last_edited_time': page_data.get('last_edited_time'),
            'properties': properties,
        },
    }
    
    await db.upsert_document(document_data)

async def handle_page_created(page_data: Dict[str, Any]):
    # Similar to handlePageUpdate but for new pages
    await handle_page_update(page_data)

async def handle_page_deleted(page_data: Dict[str, Any]):
    db = get_db()
    notion_page_id = page_data.get('id')
    await db.delete_document(notion_page_id)

def extract_title(properties: Dict[str, Any]) -> str:
    # Extract title from Notion page properties
    title_property = properties.get('title') or properties.get('Name') or properties.get('name')
    if title_property and title_property.get('title'):
        return ''.join([t.get('plain_text', '') for t in title_property['title']])
    return 'Untitled'

async def extract_page_content(page_id: str) -> str:
    # In production, use Notion API to fetch page content
    # This is a placeholder implementation
    return f"Content for page {page_id}"