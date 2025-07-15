"""
Ingestion Interface

Public interface for the ingestion module.
This defines the contract for data ingestion operations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class SyncResult:
    """Result of a database sync operation."""
    success: bool
    database_id: str
    documents_processed: int
    chunks_generated: int
    embeddings_created: int
    sync_time_seconds: float
    error_message: Optional[str] = None

class IngestionInterface(ABC):
    """
    Interface for data ingestion operations.
    
    This interface defines the contract for ingesting data from Notion
    into the database with proper processing and embedding generation.
    """
    
    @abstractmethod
    async def sync_database(self, database_id: str, **kwargs) -> SyncResult:
        """
        Sync a Notion database to the local database.
        
        Args:
            database_id: Notion database ID to sync
            **kwargs: Additional sync parameters
            
        Returns:
            SyncResult with sync statistics and status
        """
        pass
    
    @abstractmethod
    async def process_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single document through the ingestion pipeline.
        
        Args:
            document: Document data from Notion
            
        Returns:
            Processed document with chunks and embeddings
        """
        pass
    
    @abstractmethod
    async def generate_embeddings(self, text_chunks: List[str]) -> List[List[float]]:
        """
        Generate embeddings for text chunks.
        
        Args:
            text_chunks: List of text chunks to embed
            
        Returns:
            List of embedding vectors
        """
        pass 