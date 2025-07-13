from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


class Document(BaseModel):
    """Document model for evaluation with metadata support."""
    id: str
    title: str
    content: str
    database_id: str
    created_time: Optional[datetime] = None
    last_edited_time: Optional[datetime] = None
    url: Optional[str] = None
    
    # Metadata fields
    extracted_metadata: Dict[str, Any] = Field(default_factory=dict)  # Processed metadata
    content_length: Optional[int] = None
    has_multimedia: bool = False
    multimedia_refs: List[str] = Field(default_factory=list)  # URLs/references to multimedia

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CollectionStats(BaseModel):
    """Statistics about the collected data."""
    total_documents: int
    total_databases: int
    collection_time: datetime
    avg_content_length: Optional[float] = None
    content_length_distribution: Dict[str, int] = Field(default_factory=dict)
    metadata_field_coverage: Dict[str, int] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class QuestionAnswerPair(BaseModel):
    """Question-answer pair for evaluation dataset."""
    question: str
    answer: str
    # Optional metadata about the question for richer evaluation
    question_type: str | None = None  # e.g., factual, explanatory, analytical
    difficulty: str | None = None     # e.g., easy, medium, hard
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