from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    database_filters: Optional[List[str]] = None
    # Single-user, single-workspace app - no workspace ID needed

class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    database_filters: Optional[List[str]] = None
    # Single-user, single-workspace app - no workspace ID needed

class SearchResult(BaseModel):
    id: str
    title: str
    content: str
    similarity: float
    metadata: Dict[str, Any]
    notion_page_id: str

class SearchResponse(BaseModel):
    results: List[SearchResult]
    query: str
    total: int

class NotionWebhookPayload(BaseModel):
    object: str
    event_type: str
    data: Dict[str, Any]

class WebhookResponse(BaseModel):
    success: bool
    message: Optional[str] = None

class EmbeddingResponse(BaseModel):
    embedding: List[float]
    tokens: int

class ChatResponse(BaseModel):
    content: str
    tokens: int