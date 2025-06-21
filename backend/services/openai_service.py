from openai import OpenAI
import os
from dotenv import load_dotenv
import asyncio
from typing import List, Dict, Any, AsyncGenerator
from models import EmbeddingResponse, ChatResponse
from config.model_config import get_model_config

# Load environment variables
load_dotenv(dotenv_path="../.env")

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
    
    async def generate_chat_title(self, messages: List[Dict[str, str]]) -> str:
        """
        Generate a concise, descriptive title for a chat session based on the conversation.
        
        Args:
            messages: List of chat messages (user and assistant)
            
        Returns:
            A concise title (max 50 characters) that describes the conversation topic
        """
        summarization_config = self.model_config.get_summarization_config()
        performance_config = self.model_config.get_performance_config()
        
        # Add delay for rate limiting
        await asyncio.sleep(performance_config.summarization_delay_seconds)
        
        # Take only the first few messages to determine the topic
        first_messages = messages[:4]  # First 4 messages should be enough for topic identification
        
        # Build conversation context
        conversation_text = ""
        for msg in first_messages:
            role = "User" if msg["role"] == "user" else "Assistant" 
            conversation_text += f"{role}: {msg['content']}\n"
        
        prompt = f"""Based on this conversation, generate a concise, descriptive title that captures the main topic or question being discussed. 

Guidelines:
- Maximum 50 characters
- Be specific and descriptive
- Focus on the main topic/question
- Use clear, simple language
- No quotes or special formatting

Conversation:
{conversation_text}

Title:"""

        try:
            response = self.client.chat.completions.create(
                model=summarization_config.model,
                messages=[{
                    "role": "user", 
                    "content": prompt
                }],
                temperature=0.3,  # Lower temperature for more consistent titles
                max_tokens=20,    # Short response for titles
            )
            
            title = response.choices[0].message.content or ''
            title = title.strip().strip('"').strip("'")  # Remove quotes
            
            # Ensure it's not too long
            if len(title) > 50:
                title = title[:47] + "..."
                
            return title if title else "New Chat"
            
        except Exception as e:
            # Fallback to simple title generation if AI fails
            first_user_message = next((msg['content'] for msg in messages if msg['role'] == 'user'), '')
            if first_user_message:
                return first_user_message[:47] + "..." if len(first_user_message) > 50 else first_user_message
            return "New Chat"
    
    async def generate_chat_summary(self, messages: List[Dict[str, str]]) -> str:
        """Generate a concise summary of the chat conversation."""
        try:
            # Apply rate limiting
            await asyncio.sleep(self.performance_config.title_generation_delay)
            
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
            
            summary_prompt = f"""Generate a concise 1-2 sentence summary of this conversation. Focus on the main topic and key points discussed.

Conversation:
{conversation_text}

Summary (max 150 characters):"""
            
            model_config = self.model_config.get_summary_model()
            response = await self.client.chat.completions.create(
                model=model_config.model_name,
                messages=[
                    {"role": "user", "content": summary_prompt}
                ],
                max_tokens=40,  # Short summary
                temperature=0.3,  # Low temperature for consistency
                timeout=10.0
            )
            
            summary = response.choices[0].message.content.strip() if response.choices else ""
            
            # Clean up the summary
            summary = summary.strip('"').strip("'").strip()
            
            # Ensure it's not too long
            if len(summary) > 150:
                summary = summary[:147] + "..."
                
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