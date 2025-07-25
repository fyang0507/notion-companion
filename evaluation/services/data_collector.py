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

from ingestion.services.notion_service import NotionService
from evaluation.models.evaluation_models import Document, CollectionStats


class DataCollector:
    """Data collector for evaluation with metadata support."""
    
    def __init__(self, notion_token: str = None):
        # Load notion token from environment if not provided
        if notion_token is None:
            notion_token = os.getenv("NOTION_ACCESS_TOKEN")
        
        if not notion_token:
            raise ValueError("NOTION_ACCESS_TOKEN environment variable is required")
        
        self.notion_service = NotionService(notion_token)
        self.documents: List[Document] = []
        self.errors: List[str] = []
    
    def _extract_metadata(self, notion_page: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and process metadata from a Notion page's properties."""
        metadata = {}
        properties = notion_page.get("properties", {})
        
        for prop_name, prop_data in properties.items():
            prop_type = prop_data.get("type")
            
            try:
                if prop_type == "title":
                    # Title is already extracted as the main title
                    continue
                elif prop_type == "rich_text":
                    text_content = prop_data.get("rich_text", [])
                    if text_content:
                        metadata[prop_name] = "".join([t.get("plain_text", "") for t in text_content])
                elif prop_type == "multi_select":
                    options = prop_data.get("multi_select", [])
                    metadata[prop_name] = [opt.get("name") for opt in options]
                elif prop_type == "select":
                    option = prop_data.get("select")
                    if option:
                        metadata[prop_name] = option.get("name")
                elif prop_type == "date":
                    date_obj = prop_data.get("date")
                    if date_obj:
                        metadata[prop_name] = date_obj.get("start")
                elif prop_type == "status":
                    status = prop_data.get("status")
                    if status:
                        metadata[prop_name] = status.get("name")
                elif prop_type == "url":
                    url = prop_data.get("url")
                    if url:
                        metadata[prop_name] = url
                elif prop_type == "number":
                    number = prop_data.get("number")
                    if number is not None:
                        metadata[prop_name] = number
                elif prop_type == "checkbox":
                    metadata[prop_name] = prop_data.get("checkbox", False)
                elif prop_type == "people":
                    people = prop_data.get("people", [])
                    metadata[prop_name] = [person.get("name", "") for person in people]
                elif prop_type == "files":
                    files = prop_data.get("files", [])
                    metadata[prop_name] = [file.get("name", "") for file in files]
                elif prop_type == "formula":
                    formula = prop_data.get("formula", {})
                    formula_type = formula.get("type")
                    if formula_type in ["string", "number", "boolean", "date"]:
                        metadata[prop_name] = formula.get(formula_type)
                # Add more property types as needed
                
            except Exception as e:
                print(f"Error processing property {prop_name}: {e}")
                continue
        
        return metadata
    
    def _detect_multimedia(self, content: str) -> tuple[bool, List[str]]:
        """Detect if content has multimedia and extract references."""
        multimedia_refs = []
        has_multimedia = False
        
        # Look for common multimedia patterns in Notion content
        # This is a simplified version - could be enhanced based on actual content structure
        if "![" in content or "](http" in content:
            has_multimedia = True
            # Extract URLs - simplified pattern
            import re
            urls = re.findall(r'https?://[^\s\)]+', content)
            multimedia_refs.extend(urls)
        
        return has_multimedia, multimedia_refs
    
    async def collect_database(self, database_id: str, limit: int = None) -> List[Document]:
        """Collect documents from a specific database with metadata."""
        print(f"Collecting data from database: {database_id}")
        
        try:
            # Get all pages from the database
            pages = await self.notion_service.get_database_pages(database_id)
            print(f"Database: {database_id}")
            
            if limit:
                pages = pages[:limit]
            
            print(f"Found {len(pages)} pages")
            
            for page in pages:
                try:
                    # Get page content
                    content = await self.notion_service.get_page_content(page["id"])
                    
                    # Extract metadata
                    extracted_metadata = self._extract_metadata(page)
                    
                    # Detect multimedia
                    has_multimedia, multimedia_refs = self._detect_multimedia(content)
                    
                    # Create document
                    doc = Document(
                        id=page["id"],
                        title=self.notion_service.extract_title_from_page(page),
                        content=content,
                        database_id=database_id,
                        created_time=datetime.fromisoformat(page["created_time"].replace("Z", "+00:00")) if page.get("created_time") else None,
                        last_edited_time=datetime.fromisoformat(page["last_edited_time"].replace("Z", "+00:00")) if page.get("last_edited_time") else None,
                        url=page.get("url"),
                        extracted_metadata=extracted_metadata,
                        content_length=len(content),
                        has_multimedia=has_multimedia,
                        multimedia_refs=multimedia_refs
                    )
                    
                    self.documents.append(doc)
                    print(f"✓ Collected: {doc.title[:50]}...")
                    
                except Exception as e:
                    error_msg = f"Error processing page {page.get('id', 'unknown')}: {str(e)}"
                    print(f"✗ {error_msg}")
                    self.errors.append(error_msg)
                    continue
            
            print(f"Successfully collected {len(self.documents)} documents")
            return self.documents
            
        except Exception as e:
            error_msg = f"Error collecting database {database_id}: {str(e)}"
            print(f"✗ {error_msg}")
            self.errors.append(error_msg)
            return []
    
    async def collect_multiple_databases(self, database_ids: List[str], limit: int = None) -> List[Document]:
        """Collect documents from multiple databases."""
        all_documents = []
        
        for db_id in database_ids:
            documents = await self.collect_database(db_id, limit)
            all_documents.extend(documents)
        
        self.documents = all_documents
        return all_documents
    
    def get_collection_stats(self) -> CollectionStats:
        """Get collection statistics."""
        total_docs = len(self.documents)
        avg_content_length = sum(doc.content_length or 0 for doc in self.documents) / total_docs if total_docs > 0 else 0
        
        # Content length distribution
        content_length_dist = {"short": 0, "medium": 0, "long": 0}
        for doc in self.documents:
            length = doc.content_length or 0
            if length < 1000:
                content_length_dist["short"] += 1
            elif length < 5000:
                content_length_dist["medium"] += 1
            else:
                content_length_dist["long"] += 1
        
        # Metadata field coverage
        metadata_coverage = {}
        for doc in self.documents:
            for field in doc.extracted_metadata.keys():
                metadata_coverage[field] = metadata_coverage.get(field, 0) + 1
        
        return CollectionStats(
            total_documents=total_docs,
            total_databases=len(set(doc.database_id for doc in self.documents)),
            collection_time=datetime.now(),
            avg_content_length=avg_content_length,
            content_length_distribution=content_length_dist,
            metadata_field_coverage=metadata_coverage
        )
    
    def save_to_json(self, output_path: str):
        """Save collected documents to JSON file."""
        # Create output directory if it doesn't exist
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare data for JSON serialization
        data = {
            "documents": [doc.model_dump() for doc in self.documents],
            "stats": self.get_collection_stats().model_dump(),
            "errors": self.errors
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"Saved {len(self.documents)} documents to {output_path}")
    
    def clear(self):
        """Clear collected data."""
        self.documents = []
        self.errors = []