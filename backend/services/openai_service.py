from openai import OpenAI
import os
import asyncio
from typing import List, Dict, Any, AsyncGenerator
from models import EmbeddingResponse, ChatResponse
from config.model_config import get_model_config

class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model_config = get_model_config()
    
    async def generate_embedding(self, text: str) -> EmbeddingResponse:
        """Generate embedding using configured model."""
        embedding_config = self.model_config.get_embedding_config()
        performance_config = self.model_config.get_performance_config()
        
        # Add delay for rate limiting
        await asyncio.sleep(performance_config.embedding_delay_seconds)
        
        response = self.client.embeddings.create(
            model=embedding_config.model,
            input=text,
            dimensions=embedding_config.dimensions
        )
        
        return EmbeddingResponse(
            embedding=response.data[0].embedding,
            tokens=response.usage.total_tokens
        )
    
    async def generate_chat_response(self, messages: List[Dict[str, str]], context: str = None) -> ChatResponse:
        """Generate chat response using configured model."""
        chat_config = self.model_config.get_chat_config()
        performance_config = self.model_config.get_performance_config()
        
        # Add delay for rate limiting
        await asyncio.sleep(performance_config.chat_delay_seconds)
        
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
            model=chat_config.model,
            messages=[system_message] + messages,
            temperature=chat_config.temperature,
            max_tokens=chat_config.max_tokens,
        )
        
        return ChatResponse(
            content=response.choices[0].message.content or '',
            tokens=response.usage.total_tokens if response.usage else 0
        )
    
    async def generate_streaming_response(self, messages: List[Dict[str, str]], context: str = None) -> AsyncGenerator[str, None]:
        """Generate streaming chat response using configured model."""
        chat_config = self.model_config.get_chat_config()
        
        system_message = {
            "role": "system",
            "content": f"""You are a helpful AI assistant that answers questions based on the user's Notion workspace content. 
            {f"Here is relevant context from their workspace: {context}" if context else ""}"""
        }
        
        stream = self.client.chat.completions.create(
            model=chat_config.model,
            messages=[system_message] + messages,
            temperature=chat_config.temperature,
            max_tokens=chat_config.max_tokens,
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
        summarization_config = self.model_config.get_summarization_config()
        limits_config = self.model_config.get_limits_config()
        performance_config = self.model_config.get_performance_config()
        
        # Add delay for rate limiting
        await asyncio.sleep(performance_config.summarization_delay_seconds)
        
        # Truncate content to fit within token limits (roughly 4 chars per token)
        max_content_chars = limits_config.max_summary_input_tokens * 4
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
            model=summarization_config.model,
            messages=[{
                "role": "user", 
                "content": prompt
            }],
            temperature=summarization_config.temperature,
            max_tokens=summarization_config.max_tokens,
        )
        
        summary = response.choices[0].message.content or ''
        return summary.strip()
    
    def get_token_limits(self) -> Dict[str, int]:
        """Get token limits for different operations."""
        limits_config = self.model_config.get_limits_config()
        return {
            "max_embedding_tokens": limits_config.max_embedding_tokens,
            "max_summary_input_tokens": limits_config.max_summary_input_tokens,
            "max_chat_context_tokens": limits_config.max_chat_context_tokens,
            "chunk_size_tokens": limits_config.chunk_size_tokens,
            "chunk_overlap_tokens": limits_config.chunk_overlap_tokens
        }
    

# Global OpenAI service instance
openai_service = OpenAIService()

def get_openai_service() -> OpenAIService:
    return openai_service