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

# Frontend-compatible date range filter
class FrontendDateRangeFilter(BaseModel):
    from_: Optional[str] = None  # Frontend sends as string
    to: Optional[str] = None

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    database_filters: Optional[List[str]] = None
    session_id: str  # Required session ID for conversation history
    
    # Frontend-compatible metadata filters
    metadata_filters: Optional[Dict[str, List[str]]] = None  # Frontend sends as Record<string, string[]>
    content_type_filters: Optional[List[str]] = None
    date_range_filter: Optional[FrontendDateRangeFilter] = None  # Frontend format
    search_query_filter: Optional[str] = None  # Frontend field
    
    # Add fields that the chat endpoint expects
    stream: Optional[bool] = True  # Default to streaming
    limit: Optional[int] = 10  # Default limit
    
    # Single-user, single-workspace app - no workspace ID needed

class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    database_filters: Optional[List[str]] = None
    
    # Enhanced metadata filtering with typed filters
    metadata_filters: Optional[List[MetadataFilter]] = None
    content_type_filters: Optional[List[str]] = None
    date_range_filter: Optional[DateRangeFilter] = None
    
    # Single-user, single-workspace app - no workspace ID needed

class SearchResult(BaseModel):
    id: str
    title: str
    content: str
    similarity: float
    metadata: Dict[str, Any]
    notion_page_id: str
    
    # Enhanced metadata fields (configuration-driven)
    result_type: Optional[str] = None  # 'document' or 'chunk'
    chunk_context: Optional[str] = None
    chunk_summary: Optional[str] = None
    document_metadata: Optional[Dict[str, Any]] = None  # Contains extracted_fields from databases.toml config
    page_url: Optional[str] = None
    has_adjacent_context: Optional[bool] = None
    database_id: Optional[str] = None

class SearchResponse(BaseModel):
    results: List[SearchResult]
    query: str
    total: int

# Chat response models for different response types
class ChatResponse(BaseModel):
    message: str
    sources: List[SearchResult]
    session_id: str
    tokens_used: int

class StreamChatChunk(BaseModel):
    content: str
    done: bool
    error: Optional[str] = None

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