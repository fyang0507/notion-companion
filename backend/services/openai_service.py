"""
OpenAI Service for handling AI model interactions.
Provides a centralized interface for all OpenAI API calls with proper error handling,
rate limiting, and configuration management.
"""

import asyncio
import time
from typing import List, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
from pydantic import BaseModel

from config.model_config import get_model_config
from logging_config import get_logger

logger = get_logger(__name__)

class EmbeddingResponse(BaseModel):
    embedding: List[float]
    tokens: int

class ChatResponse(BaseModel):
    content: str
    tokens: int

class OpenAIService:
    def __init__(self):
        self.client = AsyncOpenAI()
        self.model_config = get_model_config()
    
    async def generate_embedding(self, text: str) -> EmbeddingResponse:
        """Generate embedding for the given text using configured model."""
        embedding_config = self.model_config.get_embedding_config()
        performance_config = self.model_config.get_performance_config()
        
        # Add delay for rate limiting
        await asyncio.sleep(performance_config.embedding_delay_seconds)
        
        response = await self.client.embeddings.create(
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
        
        # Use centralized prompt management
        system_prompt = self.model_config.format_chat_system_prompt(context=context, use_streaming=False)
        
        system_message = {
            "role": "system",
            "content": system_prompt
        }
        
        response = await self.client.chat.completions.create(
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
        
        # Use centralized prompt management for streaming
        system_prompt = self.model_config.format_chat_system_prompt(context=context, use_streaming=True)
        
        system_message = {
            "role": "system",
            "content": system_prompt
        }
        
        stream = await self.client.chat.completions.create(
            model=chat_config.model,
            messages=[system_message] + messages,
            temperature=chat_config.temperature,
            max_tokens=chat_config.max_tokens,
            stream=True,
        )
        
        async for chunk in stream:
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
        
        # Use centralized prompt management
        prompt = self.model_config.format_document_summary_prompt(
            title=title,
            content=truncated_content,
            max_length=max_length
        )

        response = await self.client.chat.completions.create(
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
    
    async def generate_chat_title(self, messages: List[Dict[str, str]], max_words: int = 8) -> str:
        """
        Generate a concise, descriptive title for a chat session based on the conversation.
        
        Args:
            messages: List of chat messages (user and assistant)
            max_words: Maximum number of words in the title (default 8, max 10)
            
        Returns:
            A concise title (max 10 words) that describes the conversation topic
        """
        summarization_config = self.model_config.get_summarization_config()
        performance_config = self.model_config.get_performance_config()
        prompts_config = self.model_config.get_prompts_config()
        
        # Add delay for rate limiting
        await asyncio.sleep(performance_config.summarization_delay_seconds)
        
        # Take only the first few messages to determine the topic
        first_messages = messages[:4]  # First 4 messages should be enough for topic identification
        
        # Build conversation context
        conversation_text = ""
        for msg in first_messages:
            role = "User" if msg["role"] == "user" else "Assistant" 
            conversation_text += f"{role}: {msg['content']}\n"
        
        # Use centralized prompt management
        prompt = self.model_config.format_title_prompt(
            conversation_text=conversation_text,
            max_words=max_words
        )

        try:
            response = await self.client.chat.completions.create(
                model=summarization_config.model,
                messages=[{
                    "role": "user", 
                    "content": prompt
                }],
                temperature=prompts_config.title_generation.temperature_override,
                max_tokens=prompts_config.title_generation.max_tokens_override,
            )
            
            title = response.choices[0].message.content or ''
            title = title.strip().strip('"').strip("'")  # Remove quotes
            
            # Ensure it doesn't exceed word limit
            words = title.split()
            if len(words) > max_words:
                title = ' '.join(words[:max_words])
                
            return title if title else "New Chat"
            
        except Exception as e:
            # Fallback to simple title generation if AI fails
            first_user_message = next((msg['content'] for msg in messages if msg['role'] == 'user'), '')
            if first_user_message:
                words = first_user_message.split()
                if len(words) <= max_words:
                    return first_user_message
                else:
                    return ' '.join(words[:max_words])
            return "New Chat"
    
    async def generate_chat_summary(self, messages: List[Dict[str, str]]) -> str:
        """Generate a concise summary of the chat conversation."""
        try:
            summarization_config = self.model_config.get_summarization_config()
            performance_config = self.model_config.get_performance_config()
            prompts_config = self.model_config.get_prompts_config()
            
            # Apply rate limiting
            await asyncio.sleep(performance_config.summarization_delay_seconds)
            
            if not messages:
                return ""
            
            # Use only a subset of messages for efficiency (first 6 exchanges)
            summary_messages = messages[:12]  # 6 exchanges max
            
            # Build conversation text
            conversation_text = ""
            for msg in summary_messages:
                role = "User" if msg['role'] == 'user' else "Assistant"
                conversation_text += f"{role}: {msg['content'][:500]}\n\n"  # Limit each message to 500 chars
            
            if len(conversation_text) > 3000:  # Limit total input
                conversation_text = conversation_text[:3000] + "..."
            
            # Use centralized prompt management
            summary_prompt = self.model_config.format_chat_summary_prompt(conversation_text)
            
            response = await self.client.chat.completions.create(
                model=summarization_config.model,
                messages=[
                    {"role": "user", "content": summary_prompt}
                ],
                max_tokens=prompts_config.summarization.chat_summary_max_tokens,
                temperature=prompts_config.summarization.chat_summary_temperature,
            )
            
            summary = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
            
            # Clean up the summary
            summary = summary.strip('"').strip("'").strip()
            
            # Ensure it's not too long
            max_chars = prompts_config.summarization.chat_summary_max_chars
            if len(summary) > max_chars:
                summary = summary[:max_chars-3] + "..."
                
            return summary if summary else ""
            
        except Exception as e:
            # Return empty string if summary generation fails
            return ""
    
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