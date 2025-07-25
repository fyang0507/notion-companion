from notion_client import Client
from typing import List, Dict, Any, Optional
import os
import asyncio
from datetime import datetime
import re

class NotionService:
    def __init__(self, access_token: str):
        self.client = Client(auth=access_token)
    
    async def search_pages(self, query: str = "", page_size: int = 100) -> List[Dict[str, Any]]:
        """Search for pages in the Notion workspace."""
        try:
            if query:
                response = self.client.search(
                    query=query,
                    filter={"property": "object", "value": "page"},
                    page_size=page_size
                )
            else:
                # Get all pages if no query provided
                response = self.client.search(
                    filter={"property": "object", "value": "page"},
                    page_size=page_size
                )
            
            pages = response.get("results", [])
            
            # Handle pagination
            while response.get("has_more") and len(pages) < 1000:  # Safety limit
                response = self.client.search(
                    filter={"property": "object", "value": "page"},
                    page_size=page_size,
                    start_cursor=response.get("next_cursor")
                )
                pages.extend(response.get("results", []))
            
            return pages
        
        except Exception as e:
            raise Exception(f"Failed to search Notion pages: {str(e)}")
    
    async def get_page(self, page_id: str) -> Dict[str, Any]:
        """Get a specific page by ID."""
        try:
            return self.client.pages.retrieve(page_id=page_id)
        except Exception as e:
            raise Exception(f"Failed to retrieve page {page_id}: {str(e)}")
    
    async def get_page_content(self, page_id: str) -> str:
        """Extract text content from a Notion page."""
        try:
            # Get page blocks
            blocks_response = self.client.blocks.children.list(block_id=page_id, page_size=100)
            blocks = blocks_response.get("results", [])
            
            # Handle pagination for blocks
            while blocks_response.get("has_more"):
                blocks_response = self.client.blocks.children.list(
                    block_id=page_id,
                    page_size=100,
                    start_cursor=blocks_response.get("next_cursor")
                )
                blocks.extend(blocks_response.get("results", []))
            
            content = await self._extract_text_from_blocks(blocks)
            return content.strip()
        
        except Exception as e:
            raise Exception(f"Failed to get content for page {page_id}: {str(e)}")
    
    async def get_page_content_with_multimedia(self, page_id: str) -> tuple[str, List[Dict[str, Any]]]:
        """Extract text content and multimedia references from a Notion page."""
        try:
            # Get page blocks
            blocks_response = self.client.blocks.children.list(block_id=page_id, page_size=100)
            blocks = blocks_response.get("results", [])
            
            # Handle pagination for blocks
            while blocks_response.get("has_more"):
                blocks_response = self.client.blocks.children.list(
                    block_id=page_id,
                    page_size=100,
                    start_cursor=blocks_response.get("next_cursor")
                )
                blocks.extend(blocks_response.get("results", []))
            
            content, multimedia_refs = await self._extract_text_and_multimedia_from_blocks(blocks)
            return content.strip(), multimedia_refs
        
        except Exception as e:
            raise Exception(f"Failed to get content for page {page_id}: {str(e)}")
    
    async def _extract_text_from_blocks(self, blocks: List[Dict[str, Any]]) -> str:
        """Recursively extract text from Notion blocks."""
        content_parts = []
        
        for block in blocks:
            block_type = block.get("type")
            
            if not block_type:
                continue
            
            # Handle different block types
            text_content = ""
            
            if block_type in ["paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item", "numbered_list_item", "to_do", "quote", "callout"]:
                rich_text = block.get(block_type, {}).get("rich_text", [])
                text_content = self._extract_plain_text(rich_text)
                
                # Add formatting for headings
                if block_type.startswith("heading"):
                    level = int(block_type.split("_")[1])
                    text_content = f"{'#' * level} {text_content}"
                elif block_type == "bulleted_list_item":
                    text_content = f"• {text_content}"
                elif block_type == "numbered_list_item":
                    text_content = f"1. {text_content}"
                elif block_type == "to_do":
                    checked = block.get(block_type, {}).get("checked", False)
                    checkbox = "☑" if checked else "☐"
                    text_content = f"{checkbox} {text_content}"
                elif block_type == "quote":
                    text_content = f"> {text_content}"
            
            elif block_type == "code":
                code_data = block.get("code", {})
                language = code_data.get("language", "")
                rich_text = code_data.get("rich_text", [])
                code_content = self._extract_plain_text(rich_text)
                text_content = f"```{language}\n{code_content}\n```"
            
            elif block_type == "table":
                # For tables, we'll get the table rows
                table_width = block.get("table", {}).get("table_width", 0)
                if block.get("has_children"):
                    try:
                        table_rows = self.client.blocks.children.list(block_id=block["id"])
                        table_content = await self._extract_table_content(table_rows.get("results", []))
                        text_content = table_content
                    except:
                        text_content = "[Table content]"
            
            elif block_type == "image":
                image_data = block.get("image", {})
                caption = image_data.get("caption", [])
                caption_text = self._extract_plain_text(caption)
                text_content = f"[Image: {caption_text}]" if caption_text else "[Image]"
            
            elif block_type == "file":
                file_data = block.get("file", {})
                caption = file_data.get("caption", [])
                caption_text = self._extract_plain_text(caption)
                text_content = f"[File: {caption_text}]" if caption_text else "[File]"
            
            elif block_type == "bookmark":
                bookmark_data = block.get("bookmark", {})
                url = bookmark_data.get("url", "")
                caption = bookmark_data.get("caption", [])
                caption_text = self._extract_plain_text(caption)
                text_content = f"[Bookmark: {caption_text or url}]"
            
            elif block_type == "divider":
                text_content = "---"
            
            # Handle child blocks recursively
            if block.get("has_children") and block_type not in ["table"]:  # Table children handled separately
                try:
                    child_blocks = self.client.blocks.children.list(block_id=block["id"])
                    child_content = await self._extract_text_from_blocks(child_blocks.get("results", []))
                    if child_content.strip():
                        text_content += f"\n{child_content}"
                except:
                    pass  # Skip if we can't get child blocks
            
            if text_content.strip():
                content_parts.append(text_content)
        
        return "\n\n".join(content_parts)
    
    async def _extract_text_and_multimedia_from_blocks(self, blocks: List[Dict[str, Any]]) -> tuple[str, List[Dict[str, Any]]]:
        """Recursively extract text and multimedia references from Notion blocks."""
        content_parts = []
        multimedia_refs = []
        position = 0
        
        for block in blocks:
            block_type = block.get("type")
            
            if not block_type:
                continue
            
            # Handle different block types
            text_content = ""
            
            if block_type in ["paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item", "numbered_list_item", "to_do", "quote", "callout"]:
                rich_text = block.get(block_type, {}).get("rich_text", [])
                text_content = self._extract_plain_text(rich_text)
                
                # Add formatting for headings
                if block_type.startswith("heading"):
                    level = int(block_type.split("_")[1])
                    text_content = f"{'#' * level} {text_content}"
                elif block_type == "bulleted_list_item":
                    text_content = f"• {text_content}"
                elif block_type == "numbered_list_item":
                    text_content = f"1. {text_content}"
                elif block_type == "to_do":
                    checked = block.get(block_type, {}).get("checked", False)
                    checkbox = "☑" if checked else "☐"
                    text_content = f"{checkbox} {text_content}"
                elif block_type == "quote":
                    text_content = f"> {text_content}"
            
            elif block_type == "code":
                code_data = block.get("code", {})
                language = code_data.get("language", "")
                rich_text = code_data.get("rich_text", [])
                code_content = self._extract_plain_text(rich_text)
                text_content = f"```{language}\n{code_content}\n```"
            
            elif block_type == "table":
                # For tables, we'll get the table rows
                table_width = block.get("table", {}).get("table_width", 0)
                if block.get("has_children"):
                    try:
                        table_rows = self.client.blocks.children.list(block_id=block["id"])
                        table_content = await self._extract_table_content(table_rows.get("results", []))
                        text_content = table_content
                    except:
                        text_content = "[Table content]"
            
            elif block_type == "image":
                image_data = block.get("image", {})
                caption = image_data.get("caption", [])
                caption_text = self._extract_plain_text(caption)
                
                # Extract image URL
                image_url = self._get_file_url(image_data)
                
                # Add to multimedia references
                multimedia_refs.append({
                    'type': 'image',
                    'url': image_url,
                    'caption': caption_text,
                    'position': position,
                    'block_id': block.get('id')
                })
                
                text_content = f"[Image: {caption_text}]" if caption_text else "[Image]"
            
            elif block_type == "file":
                file_data = block.get("file", {})
                caption = file_data.get("caption", [])
                caption_text = self._extract_plain_text(caption)
                
                # Extract file URL
                file_url = self._get_file_url(file_data)
                
                # Add to multimedia references
                multimedia_refs.append({
                    'type': 'file',
                    'url': file_url,
                    'caption': caption_text,
                    'position': position,
                    'block_id': block.get('id')
                })
                
                text_content = f"[File: {caption_text}]" if caption_text else "[File]"
            
            elif block_type == "video":
                video_data = block.get("video", {})
                caption = video_data.get("caption", [])
                caption_text = self._extract_plain_text(caption)
                
                # Extract video URL
                video_url = self._get_file_url(video_data)
                
                # Add to multimedia references
                multimedia_refs.append({
                    'type': 'video',
                    'url': video_url,
                    'caption': caption_text,
                    'position': position,
                    'block_id': block.get('id')
                })
                
                text_content = f"[Video: {caption_text}]" if caption_text else "[Video]"
            
            elif block_type == "bookmark":
                bookmark_data = block.get("bookmark", {})
                url = bookmark_data.get("url", "")
                caption = bookmark_data.get("caption", [])
                caption_text = self._extract_plain_text(caption)
                
                # Add to multimedia references
                multimedia_refs.append({
                    'type': 'bookmark',
                    'url': url,
                    'caption': caption_text,
                    'position': position,
                    'block_id': block.get('id')
                })
                
                text_content = f"[Bookmark: {caption_text or url}]"
            
            elif block_type == "divider":
                text_content = "---"
            
            # Handle child blocks recursively
            if block.get("has_children") and block_type not in ["table"]:  # Table children handled separately
                try:
                    child_blocks = self.client.blocks.children.list(block_id=block["id"])
                    child_content, child_multimedia = await self._extract_text_and_multimedia_from_blocks(child_blocks.get("results", []))
                    if child_content.strip():
                        text_content += f"\n{child_content}"
                    multimedia_refs.extend(child_multimedia)
                except:
                    pass  # Skip if we can't get child blocks
            
            if text_content.strip():
                content_parts.append(text_content)
                position += 1
        
        return "\n\n".join(content_parts), multimedia_refs
    
    def _get_file_url(self, file_data: Dict[str, Any]) -> str:
        """Extract file URL from Notion file data."""
        if 'external' in file_data:
            return file_data['external'].get('url', '')
        elif 'file' in file_data:
            return file_data['file'].get('url', '')
        return ''
    
    async def _extract_table_content(self, table_rows: List[Dict[str, Any]]) -> str:
        """Extract content from table rows."""
        table_content = []
        
        for row in table_rows:
            if row.get("type") == "table_row":
                cells = row.get("table_row", {}).get("cells", [])
                cell_texts = []
                for cell in cells:
                    cell_text = self._extract_plain_text(cell)
                    cell_texts.append(cell_text)
                table_content.append(" | ".join(cell_texts))
        
        return "\n".join(table_content)
    
    def _extract_plain_text(self, rich_text: List[Dict[str, Any]]) -> str:
        """Extract plain text from Notion rich text objects."""
        if not rich_text:
            return ""
        
        text_parts = []
        for text_obj in rich_text:
            if text_obj.get("type") == "text":
                text_parts.append(text_obj.get("plain_text", ""))
            elif text_obj.get("type") == "mention":
                # Handle mentions (users, pages, dates, etc.)
                mention_text = text_obj.get("plain_text", "")
                text_parts.append(mention_text)
            elif text_obj.get("type") == "equation":
                # Handle equations
                equation = text_obj.get("equation", {}).get("expression", "")
                text_parts.append(f"[Equation: {equation}]")
        
        return "".join(text_parts)
    
    def extract_title_from_page(self, page: Dict[str, Any]) -> str:
        """Extract title from a Notion page object."""
        properties = page.get("properties", {})
        
        # Look for title property
        for prop_name, prop_data in properties.items():
            if prop_data.get("type") == "title" and prop_data.get("title"):
                return self._extract_plain_text(prop_data["title"])
        
        # Fallback to page object title
        if "title" in page and page["title"]:
            return self._extract_plain_text(page["title"])
        
        return "Untitled"
    
    def get_page_url(self, page: Dict[str, Any]) -> str:
        """Get the public URL for a Notion page."""
        page_id = page.get("id", "").replace("-", "")
        return f"https://www.notion.so/{page_id}"
    
    def get_last_edited_time(self, page: Dict[str, Any]) -> Optional[datetime]:
        """Extract last edited time from page."""
        last_edited = page.get("last_edited_time")
        if last_edited:
            try:
                return datetime.fromisoformat(last_edited.replace("Z", "+00:00"))
            except:
                pass
        return None
    
    async def get_database(self, database_id: str) -> Dict[str, Any]:
        """Get database schema and properties."""
        try:
            return self.client.databases.retrieve(database_id=database_id)
        except Exception as e:
            raise Exception(f"Failed to get database {database_id}: {str(e)}")
    
    async def get_database_pages(self, database_id: str) -> List[Dict[str, Any]]:
        """Get all pages from a specific database."""
        try:
            response = self.client.databases.query(database_id=database_id, page_size=100)
            pages = response.get("results", [])
            
            # Handle pagination
            while response.get("has_more"):
                response = self.client.databases.query(
                    database_id=database_id,
                    page_size=100,
                    start_cursor=response.get("next_cursor")
                )
                pages.extend(response.get("results", []))
            
            return pages
        
        except Exception as e:
            raise Exception(f"Failed to get database pages for {database_id}: {str(e)}")
    
    async def get_all_pages_content_from_database(self, database_id: str) -> List[Dict[str, Any]]:
        """
        Get all pages from a database with their full content ready for chunking.
        
        Returns a list of dictionaries containing:
        - id: page ID
        - title: extracted page title
        - content: full text content 
        - created_time: creation timestamp
        - last_edited_time: last edit timestamp
        - url: page URL
        - properties: page properties
        
        This is the single interface for getting all page content from a database for chunking.
        """
        try:
            # Get all pages from the database
            pages = await self.get_database_pages(database_id)
            
            page_contents = []
            for page in pages:
                page_id = page['id']
                
                # Extract title
                title = self.extract_title_from_page(page)
                
                # Get full text content
                try:
                    content = await self.get_page_content(page_id)
                except Exception as e:
                    # Log error but continue with other pages
                    print(f"Warning: Could not fetch content for page {page_id}: {e}")
                    content = ""
                
                # Build complete page content object
                page_content = {
                    'id': page_id,
                    'title': title,
                    'content': content,
                    'created_time': page.get('created_time'),
                    'last_edited_time': page.get('last_edited_time'),
                    'url': self.get_page_url(page),
                    'properties': page.get('properties', {})
                }
                
                page_contents.append(page_content)
            
            return page_contents
            
        except Exception as e:
            raise Exception(f"Failed to get all pages content from database {database_id}: {str(e)}")

def get_notion_service(access_token: str) -> NotionService:
    """Factory function to create NotionService instance."""
    return NotionService(access_token)