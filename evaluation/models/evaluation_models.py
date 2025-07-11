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


class QuestionAnswerPair(BaseModel):
    """Question-answer pair for evaluation dataset."""
    question: str
    answer: str
    chunk_id: str
    chunk_content: str
    database_id: str
    confidence: float = 1.0
    # Metadata for chunk information (token count, text units, etc.)
    chunk_metadata: Dict[str, Any] = Field(default_factory=dict)


class ChunkQualificationStats(BaseModel):
    """Statistics for chunk qualification process."""
    total_chunks_analyzed: int = 0
    qualified_chunks: int = 0
    skipped_too_short: int = 0
    skipped_too_long: int = 0
    skipped_headers: int = 0
    skipped_short_questions: int = 0
    headers_trimmed: int = 0
    average_token_count: float = 0.0
    token_distribution: Dict[str, int] = Field(default_factory=dict)  # e.g., {"0-200": 5, "200-500": 10}


class QuestionGenerationStats(BaseModel):
    """Statistics for question generation process."""
    total_chunks_processed: int
    successful_chunks: int
    failed_chunks: int
    total_questions_generated: int
    generation_time_seconds: float
    qualification_stats: Optional[ChunkQualificationStats] = None
    heuristic_breakdown: Dict[str, int] = Field(default_factory=dict)  # e.g., {"1_question": 20, "2_questions": 30}
    sampling_stats: Dict[str, Any] = Field(default_factory=dict)  # Random sampling statistics
    errors: List[str] = Field(default_factory=list) 