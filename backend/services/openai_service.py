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

# Global OpenAI service instance
openai_service = OpenAIService()

def get_openai_service() -> OpenAIService:
    return openai_service