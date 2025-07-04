from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import date

class ChatMessage(BaseModel):
    role: str
    content: str

# ============================================================================
# ENHANCED METADATA FILTERING MODELS
# ============================================================================

class MetadataFilter(BaseModel):
    field_name: str
    operator: str  # 'equals', 'contains', 'in', 'range', 'exists'
    values: List[Any]
    field_type: Optional[str] = None  # For type-specific handling

class DateRangeFilter(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    database_filters: Optional[List[str]] = None
    session_id: str  # Required session ID for conversation history
    
    # Enhanced metadata filtering
    metadata_filters: Optional[List[MetadataFilter]] = None
    content_type_filters: Optional[List[str]] = None
    date_range_filter: Optional[DateRangeFilter] = None
    author_filters: Optional[List[str]] = None
    tag_filters: Optional[List[str]] = None
    status_filters: Optional[List[str]] = None
    
    # Single-user, single-workspace app - no workspace ID needed

class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    database_filters: Optional[List[str]] = None
    
    # Enhanced metadata filtering
    metadata_filters: Optional[List[MetadataFilter]] = None
    content_type_filters: Optional[List[str]] = None
    date_range_filter: Optional[DateRangeFilter] = None
    author_filters: Optional[List[str]] = None
    tag_filters: Optional[List[str]] = None
    status_filters: Optional[List[str]] = None
    
    # Single-user, single-workspace app - no workspace ID needed

class SearchResult(BaseModel):
    id: str
    title: str
    content: str
    similarity: float
    metadata: Dict[str, Any]
    notion_page_id: str
    
    # Enhanced metadata fields (simplified)
    result_type: Optional[str] = None  # 'document' or 'chunk'
    chunk_context: Optional[str] = None
    chunk_summary: Optional[str] = None
    document_metadata: Optional[Dict[str, Any]] = None  # Now contains extracted_fields from config
    page_url: Optional[str] = None
    has_adjacent_context: Optional[bool] = None
    database_id: Optional[str] = None

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