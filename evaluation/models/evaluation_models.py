from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


class Document(BaseModel):
    """Simple document model for evaluation."""
    id: str
    title: str
    content: str
    database_id: str
    created_time: Optional[datetime] = None
    last_edited_time: Optional[datetime] = None
    url: Optional[str] = None


class CollectionStats(BaseModel):
    """Simple collection statistics."""
    total_documents: int
    successful: int
    failed: int
    skipped: int
    errors: List[str] = Field(default_factory=list) 