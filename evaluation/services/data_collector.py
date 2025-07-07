import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import sys
from dotenv import load_dotenv

# Add parent directories to path to import backend services
sys.path.append(str(Path(__file__).parent.parent.parent))

# Load environment variables from root folder
root_dir = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=root_dir / ".env")

from backend.services.notion_service import NotionService
from evaluation.models.evaluation_models import Document, CollectionStats


class DataCollector:
    """Simple data collector for evaluation."""
    
    def __init__(self, notion_token: str = None, output_dir: str = "data"):
        # Load notion token from environment if not provided
        if not notion_token:
            notion_token = os.getenv("NOTION_ACCESS_TOKEN")
            if not notion_token:
                raise ValueError("NOTION_ACCESS_TOKEN environment variable is required")
        
        self.notion_service = NotionService(notion_token)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def collect_database(self, database_id: str, min_content_length: int = 10) -> CollectionStats:
        """Collect all documents from a database."""
        print(f"📚 Collecting database: {database_id}")
        
        stats = CollectionStats(
            total_documents=0,
            successful=0,
            failed=0,
            skipped=0
        )
        
        try:
            # Get all pages from the database
            pages = await self.notion_service.get_database_pages(database_id)
            stats.total_documents = len(pages)
            
            print(f"Found {len(pages)} pages")
            
            documents = []
            
            for page in pages:
                try:
                    # Get page content
                    content = await self.notion_service.get_page_content(page['id'])
                    
                    # Skip if too short
                    if len(content.strip()) < min_content_length:
                        stats.skipped += 1
                        continue
                    
                    # Extract title
                    title = self._extract_title(page)
                    
                    # Create document
                    doc = Document(
                        id=page['id'],
                        title=title,
                        content=content,
                        database_id=database_id,
                        created_time=self._parse_datetime(page.get('created_time')),
                        last_edited_time=self._parse_datetime(page.get('last_edited_time')),
                        url=page.get('url')
                    )
                    
                    documents.append(doc)
                    stats.successful += 1
                    
                    print(f"✅ {title}")
                    
                except Exception as e:
                    print(f"❌ Error processing page {page.get('id', 'unknown')}: {e}")
                    stats.failed += 1
                    stats.errors.append(f"Page {page.get('id', 'unknown')}: {str(e)}")
            
            # Save documents
            if documents:
                await self._save_documents(documents, database_id)
                print(f"💾 Saved {len(documents)} documents")
            
            return stats
            
        except Exception as e:
            print(f"❌ Error collecting database: {e}")
            stats.errors.append(f"Database collection failed: {str(e)}")
            return stats
    
    def _extract_title(self, page: Dict[str, Any]) -> str:
        """Extract page title."""
        properties = page.get('properties', {})
        
        # Try common title field names
        for field_name in ['Name', 'Title', 'title', 'name', '标题', '名称']:
            if field_name in properties:
                prop = properties[field_name]
                if prop.get('type') == 'title' and prop.get('title'):
                    title_parts = prop['title']
                    if title_parts:
                        return title_parts[0].get('plain_text', 'Untitled')
        
        return 'Untitled'
    
    def _parse_datetime(self, dt_str: str) -> datetime:
        """Parse datetime string."""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except:
            return None
    
    async def _save_documents(self, documents: List[Document], database_id: str):
        """Save documents to JSON file."""
        filename = f"{database_id[-10:]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.output_dir / filename
        
        # Convert to dict for JSON serialization
        data = {
            'database_id': database_id,
            'collected_at': datetime.now().isoformat(),
            'total_documents': len(documents),
            'documents': [doc.model_dump() for doc in documents]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"📄 Saved to: {filepath}")
    
    async def collect_multiple(self, database_ids: List[str], min_content_length: int = 10) -> Dict[str, CollectionStats]:
        """Collect from multiple databases."""
        results = {}
        
        for database_id in database_ids:
            stats = await self.collect_database(database_id, min_content_length)
            results[database_id] = stats
        
        return results 