"""
Ingestion Module - Data Ingestion Pipeline

This module handles the complete data ingestion pipeline:
1. Notion API data retrieval
2. Document processing and chunking
3. Embedding generation
4. Database synchronization

Key Components:
- notion_service: Notion API client
- document_processor: Document processing and chunking
- sync_databases: Database synchronization script
"""

__version__ = "1.0.0" 