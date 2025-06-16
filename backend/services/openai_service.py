from openai import OpenAI
import os
from typing import List, Dict, Any, AsyncGenerator
from models import EmbeddingResponse, ChatResponse

class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    async def generate_embedding(self, text: str) -> EmbeddingResponse:
        response = self.client.embeddings.create(
            model='text-embedding-3-small',
            input=text,
        )
        
        return EmbeddingResponse(
            embedding=response.data[0].embedding,
            tokens=response.usage.total_tokens
        )
    
    async def generate_chat_response(self, messages: List[Dict[str, str]], context: str = None) -> ChatResponse:
        system_message = {
            "role": "system",
            "content": f"""You are a helpful AI assistant that answers questions based on the user's Notion workspace content. 
            {f"Here is relevant context from their workspace: {context}" if context else ""}
            
            Guidelines:
            - Be concise and helpful
            - Reference specific documents when possible
            - If you're not sure about something, say so
            - Format responses in markdown when appropriate"""
        }
        
        response = self.client.chat.completions.create(
            model='gpt-4',
            messages=[system_message] + messages,
            temperature=0.7,
            max_tokens=1000,
        )
        
        return ChatResponse(
            content=response.choices[0].message.content or '',
            tokens=response.usage.total_tokens if response.usage else 0
        )
    
    async def generate_streaming_response(self, messages: List[Dict[str, str]], context: str = None) -> AsyncGenerator[str, None]:
        system_message = {
            "role": "system",
            "content": f"""You are a helpful AI assistant that answers questions based on the user's Notion workspace content. 
            {f"Here is relevant context from their workspace: {context}" if context else ""}"""
        }
        
        stream = self.client.chat.completions.create(
            model='gpt-4',
            messages=[system_message] + messages,
            temperature=0.7,
            max_tokens=1000,
            stream=True,
        )
        
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    
    async def generate_document_summary(self, title: str, content: str, max_length: int = 500) -> str:
        """
        Generate a concise summary of a document for embedding purposes.
        
        Args:
            title: Document title
            content: Full document content  
            max_length: Maximum length of summary in words
            
        Returns:
            Concise summary suitable for embeddings
        """
        # Truncate content to fit within token limits (roughly 4 chars per token)
        max_content_chars = 20000  # ~5000 tokens, leaving room for prompt
        truncated_content = content[:max_content_chars]
        if len(content) > max_content_chars:
            truncated_content += "\n\n[Content truncated...]"
        
        prompt = f"""Please create a comprehensive but concise summary of this document that captures:
1. Main topics and key points
2. Important concepts and themes  
3. Essential information and takeaways
4. Context and purpose

The summary should be roughly {max_length} words and be optimized for semantic search.

Title: {title}

Content:
{truncated_content}

Summary:"""

        response = self.client.chat.completions.create(
            model='gpt-4o-mini',  # Faster and cheaper for summarization
            messages=[{
                "role": "user", 
                "content": prompt
            }],
            temperature=0.3,  # Lower temperature for consistent summaries
            max_tokens=800,   # Enough for a good summary
        )
        
        summary = response.choices[0].message.content or ''
        return summary.strip()

# Global OpenAI service instance
openai_service = OpenAIService()

def get_openai_service() -> OpenAIService:
    return openai_service