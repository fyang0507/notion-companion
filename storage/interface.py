"""
Storage Interface

Public interface for the storage module.
This defines the contract for database operations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class Document:
    """Document data structure."""
    id: str
    title: str
    content: str
    notion_page_id: str
    notion_database_id: str
    page_url: Optional[str] = None
    created_time: Optional[str] = None
    last_edited_time: Optional[str] = None
    extracted_metadata: Optional[Dict[str, Any]] = None

@dataclass
class DocumentChunk:
    """Document chunk data structure."""
    id: str
    document_id: str
    content: str
    embedding: List[float]
    chunk_index: int
    token_count: int

class StorageInterface(ABC):
    """
    Interface for database storage operations.
    
    This interface defines the contract for storing and retrieving
    documents and chunks in the database.
    """
    
    @abstractmethod
    async def get_documents(self, database_id: Optional[str] = None, limit: int = 50) -> List[Document]:
        """
        Get documents from the database.
        
        Args:
            database_id: Optional database ID filter
            limit: Maximum number of documents to return
            
        Returns:
            List of documents
        """
        pass
    
    @abstractmethod
    async def store_document(self, document: Document) -> bool:
        """
        Store a document in the database.
        
        Args:
            document: Document to store
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def search_chunks(self, query_embedding: List[float], filters: Dict[str, Any]) -> List[DocumentChunk]:
        """
        Search for document chunks using vector similarity.
        
        Args:
            query_embedding: Query embedding vector
            filters: Search filters
            
        Returns:
            List of matching document chunks
        """
        pass
    
    @abstractmethod
    async def store_chunks(self, chunks: List[DocumentChunk]) -> bool:
        """
        Store document chunks in the database.
        
        Args:
            chunks: List of document chunks to store
            
        Returns:
            True if successful, False otherwise
        """
        pass 