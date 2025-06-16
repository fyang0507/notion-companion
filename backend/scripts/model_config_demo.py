#!/usr/bin/env python3
"""
Model Configuration Demo

Demonstrates how to use and switch between different model configurations
for cost optimization and performance tuning.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.model_config import get_model_config, ModelConfigManager

# Only import OpenAI service if API key is available
def get_openai_service_safe():
    """Safely get OpenAI service if API key is available."""
    if os.getenv("OPENAI_API_KEY"):
        from services.openai_service import get_openai_service
        return get_openai_service()
    return None

def demo_model_configs():
    """Demonstrate different model configurations."""
    print("🔧 Model Configuration Demo")
    print("=" * 50)
    
    # Load different environment configurations
    environments = ["development", "production", "testing"]
    
    for env in environments:
        print(f"\n📱 Environment: {env.upper()}")
        print("-" * 30)
        
        config = ModelConfigManager(environment=env)
        
        # Show embedding config
        embedding = config.get_embedding_config()
        print(f"Embedding: {embedding.model} (batch: {embedding.batch_size})")
        
        # Show chat config
        chat = config.get_chat_config()
        print(f"Chat: {chat.model} (temp: {chat.temperature})")
        
        # Show summarization config
        summary = config.get_summarization_config()
        print(f"Summary: {summary.model} (temp: {summary.temperature})")
        
        # Show performance settings
        performance = config.get_performance_config()
        print(f"Performance: Batch {performance.embedding_batch_size}, Retries {performance.max_retries}")

def demo_token_limits():
    """Demonstrate token limits for different operations."""
    print("\n🎯 Token Limits Demo")
    print("=" * 50)
    
    config = get_model_config()
    limits = config.get_limits_config()
    
    scenarios = [
        ("Small document", 1000),
        ("Medium document", 5000),
        ("Large document", 20000),
        ("Very large document", 50000)
    ]
    
    for name, tokens in scenarios:
        needs_chunking = tokens > limits.chunk_size_tokens
        needs_summary = tokens > limits.max_embedding_tokens
        chunks_needed = (tokens // limits.chunk_size_tokens) + 1 if needs_chunking else 1
        
        print(f"{name} ({tokens} tokens):")
        print(f"  Chunking needed: {needs_chunking}")
        print(f"  Summary needed: {needs_summary}")
        print(f"  Chunks: {chunks_needed}")
        print()

def demo_current_models():
    """Show currently configured models."""
    print("\n🤖 Current Model Configuration")
    print("=" * 50)
    
    config = get_model_config()
    
    # Show actual configured models
    embedding = config.get_embedding_config()
    chat = config.get_chat_config() 
    summary = config.get_summarization_config()
    
    print("Currently Active Models:")
    print(f"  Embedding: {embedding.model} ({embedding.dimensions}d, batch: {embedding.batch_size})")
    print(f"  Chat: {chat.model} (max: {chat.max_tokens}, temp: {chat.temperature})")
    print(f"  Summary: {summary.model} (max: {summary.max_tokens}, temp: {summary.temperature})")

async def demo_service_integration():
    """Demonstrate how services use the model configuration."""
    print("\n🔗 Service Integration Demo")
    print("=" * 50)
    
    # Check if we have API key for live demo
    service = get_openai_service_safe()
    
    if not service:
        print("ℹ️ No OpenAI API key found - showing configuration only")
        config = get_model_config()
        limits = config.get_limits_config()
        
        print("Token Limits from Configuration:")
        print(f"  max_embedding_tokens: {limits.max_embedding_tokens}")
        print(f"  max_summary_input_tokens: {limits.max_summary_input_tokens}")
        print(f"  max_chat_context_tokens: {limits.max_chat_context_tokens}")
        print(f"  chunk_size_tokens: {limits.chunk_size_tokens}")
        return
    
    # If we have API key, show cost estimation
    limits = service.get_token_limits()
    
    print("Token Limits from Service:")
    for key, value in limits.items():
        print(f"  {key}: {value}")
    
    # Show that service is using the same configurations  
    print("\n✅ Service is using centralized model configuration")

def main():
    """Run all demos."""
    demo_model_configs()
    demo_token_limits()
    demo_current_models()
    
    # Run async demo
    asyncio.run(demo_service_integration())
    
    print("\n✅ Model configuration system is ready!")
    print("\n💡 To switch models:")
    print("   1. Edit config/models.toml")
    print("   2. Set ENVIRONMENT=production for prod models")
    print("   3. Uncomment alternatives in config when needed")

if __name__ == "__main__":
    main()