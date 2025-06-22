#!/usr/bin/env python3
"""
LLM Configuration System Demo

Comprehensive demonstration of the centralized LLM configuration system that manages
all AI model configurations and prompts for the Notion Companion webapp.
"""

import sys
from pathlib import Path

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config.model_config import ModelConfigManager

def main():
    print("🔧 LLM Configuration System Demo")
    print("=" * 50)
    
    # Initialize configuration manager
    print("\n1. 🚀 Initializing Configuration Manager")
    config = ModelConfigManager()
    print("✅ Configuration loaded successfully from models.toml")
    
    # Display model configurations
    print("\n2. 🤖 Model Configurations")
    print("-" * 30)
    
    embedding = config.get_embedding_config()
    print(f"🔤 Embedding: {embedding.model}")
    print(f"   • Dimensions: {embedding.dimensions}")
    print(f"   • Max Input Tokens: {embedding.max_input_tokens:,}")
    print(f"   • Batch Size: {embedding.batch_size}")
    
    chat = config.get_chat_config()
    print(f"💬 Chat: {chat.model}")
    print(f"   • Max Tokens: {chat.max_tokens:,}")
    print(f"   • Temperature: {chat.temperature}")
    
    summary = config.get_summarization_config()
    print(f"📝 Summarization: {summary.model}")
    print(f"   • Max Tokens: {summary.max_tokens}")
    print(f"   • Temperature: {summary.temperature}")
    
    # Display processing limits
    print("\n3. 📊 Processing Limits")
    print("-" * 30)
    limits = config.get_limits_config()
    print(f"Max Embedding Tokens: {limits.max_embedding_tokens:,}")
    print(f"Max Summary Input: {limits.max_summary_input_tokens:,}")
    print(f"Max Chat Context: {limits.max_chat_context_tokens:,}")
    print(f"Chunk Size: {limits.chunk_size_tokens:,}")
    print(f"Chunk Overlap: {limits.chunk_overlap_tokens}")
    
    # Display performance settings
    print("\n4. ⚡ Performance Settings")
    print("-" * 30)
    perf = config.get_performance_config()
    print(f"Embedding Batch Size: {perf.embedding_batch_size}")
    print(f"Embedding Delay: {perf.embedding_delay_seconds}s")
    print(f"Chat Delay: {perf.chat_delay_seconds}s")
    print(f"Max Retries: {perf.max_retries}")
    print(f"Retry Delay: {perf.retry_delay_seconds}s")
    
    # Show prompt management capabilities
    print("\n5. 📝 Prompt Management")
    print("-" * 30)
    prompts = config.get_prompts_config()
    print(f"Title Max Words: {prompts.title_generation.max_words}")
    print(f"Title Temperature Override: {prompts.title_generation.temperature_override}")
    print(f"Title Max Tokens Override: {prompts.title_generation.max_tokens_override}")
    print(f"Default Summary Length: {prompts.summarization.default_max_length} words")
    print(f"Chat Summary Max Tokens: {prompts.summarization.chat_summary_max_tokens}")
    print(f"Chat Summary Max Characters: {prompts.summarization.chat_summary_max_chars}")
    
    # Demonstrate dynamic prompt formatting
    print("\n6. 🎨 Dynamic Prompt Formatting")
    print("-" * 30)
    
    # Sample data for demonstrations
    sample_context = "Document 1: Q4 Planning Meeting Notes\nDocument 2: Product Roadmap 2024"
    sample_conversation = "User: What are our Q4 goals?\nAssistant: Based on your planning documents, the main Q4 goals include increasing user engagement by 25% and launching 3 new features."
    
    # Chat system prompt with context
    chat_prompt = config.format_chat_system_prompt(context=sample_context)
    print("💬 Chat System Prompt (with context):")
    print(f"   Length: {len(chat_prompt)} characters")
    print(f"   Preview: '{chat_prompt[:80]}...'")
    
    # Streaming chat prompt
    streaming_prompt = config.format_chat_system_prompt(context=sample_context, use_streaming=True)
    print("🔄 Streaming Chat Prompt:")
    print(f"   Length: {len(streaming_prompt)} characters")
    print(f"   Preview: '{streaming_prompt[:80]}...'")
    
    # Title generation prompt
    title_prompt = config.format_title_prompt(sample_conversation)
    print("🏷️  Title Generation Prompt:")
    print(f"   Length: {len(title_prompt)} characters")
    print(f"   Preview: '{title_prompt[:80]}...'")
    
    # Document summary prompt
    doc_summary_prompt = config.format_document_summary_prompt(
        title="Q4 Planning Meeting", 
        content="We discussed quarterly goals, key metrics, timeline, and resource allocation for Q4 2024..."
    )
    print("📄 Document Summary Prompt:")
    print(f"   Length: {len(doc_summary_prompt)} characters")
    print(f"   Preview: '{doc_summary_prompt[:80]}...'")
    
    # Chat summary prompt
    chat_summary_prompt = config.format_chat_summary_prompt(sample_conversation)
    print("💭 Chat Summary Prompt:")
    print(f"   Length: {len(chat_summary_prompt)} characters")
    print(f"   Preview: '{chat_summary_prompt[:80]}...'")
    
    # Demonstrate service integration simulation
    print("\n7. 🔧 Service Integration Simulation")
    print("-" * 30)
    print("Simulating how services would use centralized configuration:")
    print(f"✅ Chat responses use: {chat.model} (temp: {chat.temperature})")
    print(f"✅ Title generation uses: {chat.model} (temp: {prompts.title_generation.temperature_override})")
    print(f"✅ Document summaries use: {summary.model} (temp: {summary.temperature})")
    print(f"✅ Embeddings use: {embedding.model} ({embedding.dimensions}D, batch: {embedding.batch_size})")
    print("✅ All prompts are centrally managed and dynamically formatted")
    
    # Show LLM-enabled processes
    print("\n8. 🎯 LLM-Enabled Processes")
    print("-" * 30)
    
    active_processes = [
        ("💬 Chat Responses", f"{chat.model} • RAG-enhanced conversations"),
        ("🏷️ Title Generation", f"{chat.model} • {prompts.title_generation.max_words}-word session titles"),
        ("📝 Chat Summaries", f"{summary.model} • {prompts.summarization.chat_summary_max_chars}-char summaries"),
        ("📄 Document Summaries", f"{summary.model} • {prompts.summarization.default_max_length}-word summaries"),
        ("📊 Embeddings", f"{embedding.model} • {embedding.dimensions}D vectors"),
        ("🔍 Document Processing", "Content extraction and chunking"),
    ]
    
    print("Currently Active:")
    for process, details in active_processes:
        print(f"  {process}: {details}")
    
    future_processes = [
        "🔍 Query Expansion (prompts ready)",
        "📊 Result Ranking (prompts ready)", 
        "🏷️ Content Classification (prompts ready)",
        "📊 Metadata Extraction (prompts ready)"
    ]
    
    print("\nFuture-Ready:")
    for process in future_processes:
        print(f"  {process}")
    
    # Configuration reloading test
    print("\n9. 🔄 Configuration Management")
    print("-" * 30)
    print("Testing configuration reload capability...")
    config.reload_config()
    print("✅ Configuration reloaded successfully")
    print("💡 For production: edit models.toml values and redeploy")
    
    # Summary and key benefits
    print("\n" + "=" * 50)
    print("✅ LLM Configuration System Demo Complete!")
    print("\n🌟 Key Benefits:")
    print("• 🎯 Single source of truth for all AI models and prompts")
    print("• 🔧 Type-safe configuration with validation")
    print("• 🎨 Dynamic prompt formatting with context injection")
    print("• 🚀 Easy production deployment (update models.toml)")
    print("• 📈 Future-proof architecture for new LLM features")
    print("• 💰 Cost-optimized defaults for development")
    
    print("\n🔧 Usage:")
    print("• Development: Use current settings (gpt-4o-mini, small batches)")
    print("• Production: Update models.toml with gpt-4o, larger batches")
    print("• Customization: Modify prompts in models.toml as needed")

if __name__ == "__main__":
    main()