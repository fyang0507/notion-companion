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

from shared.config.model_config import get_model_config
from shared.logging.logging_config import get_logger

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
    
    

# Global OpenAI service instance
openai_service = OpenAIService()

def get_openai_service() -> OpenAIService:
    return openai_service