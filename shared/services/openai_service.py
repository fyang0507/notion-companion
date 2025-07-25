"""
Decentralized OpenAI Service for handling AI model interactions.
Provides a stateless interface for OpenAI API calls with configuration passed as parameters.
No global configuration dependency - each call receives its required config.
"""

import asyncio
from typing import List, Dict, Any, AsyncGenerator, Optional
from openai import AsyncOpenAI
from pydantic import BaseModel

class EmbeddingResponse(BaseModel):
    embedding: List[float]
    tokens: int

class ChatResponse(BaseModel):
    content: str
    tokens: int

class OpenAIService:
    """
    Decentralized OpenAI service that accepts configuration parameters per method call.
    Uses nested config structure: config.openai contains API params, top-level contains internal params.
    """
    
    def __init__(self):
        """Initialize only the OpenAI client - no configuration loading."""
        self.client = AsyncOpenAI()
    
    async def generate_embedding(self, text: str, config: Dict[str, Any]) -> EmbeddingResponse:
        """
        Generate embedding for the given text.
        
        Args:
            text: Text to embed
            config: Configuration dict with separate 'openai' section for API params
                   and top-level internal params (delay_seconds, batch_size, etc.)
        """
        # Extract internal parameters
        delay_seconds = config.get('delay_seconds', 0.0)
        
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)
        
        # Extract OpenAI API parameters from nested config
        api_params = config.get('openai', {}).copy()
        api_params["input"] = text
        
        response = await self.client.embeddings.create(**api_params)
        
        return EmbeddingResponse(
            embedding=response.data[0].embedding,
            tokens=response.usage.total_tokens
        )
    
    async def generate_embeddings_batch(self, texts: List[str], config: Dict[str, Any]) -> List[EmbeddingResponse]:
        """
        Generate embeddings for multiple texts in a single API call.
        
        Args:
            texts: List of texts to embed
            config: Configuration dict with separate 'openai' section for API params
                   and top-level internal params (delay_seconds, batch_size, etc.)
        """
        if not texts:
            return []
        
        # Extract internal parameters
        delay_seconds = config.get('delay_seconds', 0.0)
        
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)
        
        # Extract OpenAI API parameters from nested config
        api_params = config.get('openai', {}).copy()
        api_params["input"] = texts
        
        response = await self.client.embeddings.create(**api_params)
        
        # Convert response to list of EmbeddingResponse objects
        embeddings = []
        total_tokens = response.usage.total_tokens
        tokens_per_embedding = total_tokens // len(response.data) if response.data else 0
        
        for embedding_data in response.data:
            embeddings.append(EmbeddingResponse(
                embedding=embedding_data.embedding,
                tokens=tokens_per_embedding
            ))
        
        return embeddings
    
    async def generate_chat_response(self, messages: List[Dict[str, str]], config: Dict[str, Any]) -> ChatResponse:
        """
        Generate chat response using specified configuration.
        
        Args:
            messages: List of chat messages
            config: Configuration dict with separate 'openai' section for API params
                   and top-level internal params (delay_seconds, etc.)
        """
        # Extract internal parameters
        delay_seconds = config.get('delay_seconds', 0.0)
        
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)
        
        # Extract OpenAI API parameters from nested config
        api_params = config.get('openai', {}).copy()
        api_params["messages"] = messages
        
        response = await self.client.chat.completions.create(**api_params)
        
        return ChatResponse(
            content=response.choices[0].message.content or '',
            tokens=response.usage.total_tokens if response.usage else 0
        )
    
    async def generate_streaming_response(self, messages: List[Dict[str, str]], config: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """
        Generate streaming chat response using specified configuration.
        
        Args:
            messages: List of chat messages
            config: Configuration dict with separate 'openai' section for API params
                   and top-level internal params (delay_seconds, etc.)
                   'stream': True is automatically added for streaming.
        """
        # Extract OpenAI API parameters from nested config
        api_params = config.get('openai', {}).copy()
        api_params["messages"] = messages
        api_params["stream"] = True  # Force streaming
        
        stream = await self.client.chat.completions.create(**api_params)
        
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content