#!/usr/bin/env python3
"""
Benchmark Basic RAG Experiment Runner

Self-contained script to orchestrate the complete basic RAG benchmark experiment:
1. Complete data clearing: All tables (notion_databases, documents, document_chunks, document_metadata)
2. Self-contained ingestion: Auto-creates database entries -> fetches pages -> generates embeddings
3. Basic similarity search: Cosine similarity on paragraph chunks
4. Precision@K evaluation: Using verified QA pairs

This script is fully self-contained and coordinates all modular components.

Usage:
    python run_benchmark_basic_rag.py --clear-data     # Complete fresh start (all tables)
    python run_benchmark_basic_rag.py --ingest        # Self-contained ingestion pipeline
    python run_benchmark_basic_rag.py --full --qa-data my_qa_file.json         # Full pipeline
    python run_benchmark_basic_rag.py --offline --ingest  # Run offline ingestion only
    python run_benchmark_basic_rag.py --evaluate --qa-data my_qa_file.json # Run evaluation with QA data (always saves results)
"""

import argparse
import asyncio
import json
import os
import sys
import tomllib
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from dotenv import load_dotenv
import logging

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import our modular components
from storage.database import Database
from ingestion.services.notion_service import NotionService
from shared.services.openai_service import OpenAIService
from ingestion.services.basic_paragraph_chunker import get_basic_paragraph_chunker
from rag.strategies.basic_similarity_strategy import get_basic_similarity_strategy
from evaluation.services.retrieval_evaluator import get_retrieval_metrics_evaluator, RetrievalResults
from shared.utils.data_cleaner import get_data_cleaner
from shared.utils import count_tokens

# Load environment variables
load_dotenv(dotenv_path=str(Path(__file__).parent.parent.parent / ".env"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BenchmarkBasicRAGRunner:
    """
    Orchestrates the complete basic RAG benchmark experiment.
    
    This runner coordinates:
    - Data cleaning (shared/utils)
    - Basic ingestion pipeline (ingestion/services)
    - Basic similarity retrieval (rag/strategies)
    - Precision@K evaluation (evaluation/services)
    """
    
    def __init__(self, offline_mode: bool, benchmark_config: Dict[str, Any]):
        """Initialize all services and components."""
        self.offline_mode = offline_mode
        self.benchmark_config = benchmark_config
        
        logger.info(f"🚀 Initializing Benchmark Basic RAG Runner (offline_mode={offline_mode})...")
        
        # Create offline data directory
        if self.offline_mode:
            self.offline_dir = Path(__file__).parent.parent / "data" / "temp" / "chunks"
            self.offline_dir.mkdir(parents=True, exist_ok=True)
        
        # Load database configuration
        databases_config_path = Path(__file__).parent.parent.parent / "shared" / "config" / "databases.toml"
        try:
            with open(databases_config_path, 'rb') as f:
                self.databases_config = tomllib.load(f)
        except FileNotFoundError:
            logger.error(f"Database configuration file not found: {databases_config_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to load database configuration: {e}")
            raise RuntimeError(f"Configuration loading failed: {e}") from e
        
        # Initialize services
        notion_token = os.getenv("NOTION_ACCESS_TOKEN")
        self.notion_service = NotionService(notion_token)
        
        # Initialize components
        max_tokens = benchmark_config['ingestion']['max_tokens']
        self.chunker = get_basic_paragraph_chunker(max_tokens=max_tokens)
        
        # Store embeddings configurations for runtime use
        self.embeddings_config = benchmark_config['embeddings']
        
        # Initialize database and Supabase-dependent components (skip in offline mode)
        if not self.offline_mode:
            # Note: Database init is async, so we'll handle it in the async methods that need it
            self.database = None
            self.openai_service = OpenAIService()
            # Rouge threshold can be overridden by config, but defaults to 0.3
            rouge_threshold = benchmark_config['evaluation']['rouge_threshold']
            self.evaluator = get_retrieval_metrics_evaluator(rouge_threshold=rouge_threshold)
        else:
            self.database = None
            self.openai_service = None
            self.evaluator = None
            
        # These will be set when database is needed
        self.retrieval_strategy = None
        self.data_cleaner = None
        
        logger.info("✅ All components initialized successfully")
    
    async def _ensure_database_initialized(self):
        """Ensure database is initialized (called by methods that need it)."""
        if not self.offline_mode and self.database is None:
            self.database = Database()
            await self.database.init()
            # Initialize database-dependent components
            # Pass the decentralized OpenAI service to retrieval strategy
            self.retrieval_strategy = get_basic_similarity_strategy(self.database, self.openai_service, self.embeddings_config)
            self.data_cleaner = get_data_cleaner(self.database)
    
    async def clear_data(self):
        """Clear all data for a completely fresh experiment."""
        if self.offline_mode:
            logger.info("🧹 Clearing offline chunk files...")
            # Clear offline files
            for file in self.offline_dir.glob("*.json"):
                file.unlink()
            logger.info("✅ Cleared offline chunk files")
            return {'status': 'success', 'tables_cleared': ['offline_files']}
        
        # Initialize basic database connection and data_cleaner
        if self.database is None:
            self.database = Database()
            await self.database.init()
        
        # Use the data_cleaner utility for comprehensive clearing
        data_cleaner = get_data_cleaner(self.database)
        result = await data_cleaner.clear_all_data(confirm=False)  # No confirmation in automated script
        
        return result
    
    async def run_ingestion(self):
        """
        Run basic data ingestion pipeline for all configured databases.
        
        This method is self-contained and will:
        1. Create database entries in notion_databases table if they don't exist
        2. Fetch all pages from each configured Notion database  
        3. Generate embeddings for document chunks
        4. Store documents and chunks with positional linking
        """
        logger.info("📥 Starting basic data ingestion...")
        
        # Process all databases from config
        databases = self.databases_config['databases']
        logger.info(f"📚 Processing {len(databases)} database(s)")
        
        total_chunks_all = 0
        total_processed_pages_all = 0
        total_pages_all = 0
        
        for db_idx, database_config in enumerate(databases):
            database_id = database_config['database_id']
            database_name = database_config['name']
            
            logger.info(f"📚 Processing database {db_idx + 1}/{len(databases)}: {database_name} ({database_id})")
            
            # Get all pages with their content from the database
            pages_content = await self.notion_service.get_all_pages_content_from_database(database_id)
            logger.info(f"📄 Found {len(pages_content)} pages in database: {database_name}")
            
            total_chunks = 0
            processed_pages = 0
            
            for i, page_content in enumerate(pages_content):
                try:
                    if not page_content['content']:
                        logger.debug(f"⚠️  Skipping page {i+1}/{len(pages_content)} in {database_name}: No content")
                        continue
                    
                    # Create paragraph chunks
                    chunks_data = await self.chunker.chunk(
                        page_content['content'], 
                        page_content['title']
                    )
                    
                    if not chunks_data:
                        logger.debug(f"⚠️  Skipping page {i+1}/{len(pages_content)} in {database_name}: No chunks generated")
                        continue
                    
                    if self.offline_mode:
                        # Store chunks offline without embeddings
                        await self._store_chunks_offline(page_content, chunks_data, database_id)
                    else:
                        # Ensure database is initialized
                        await self._ensure_database_initialized()
                        
                        # Generate embeddings for chunks
                        chunk_texts = [chunk['content'] for chunk in chunks_data]
                        embeddings = await self._create_embeddings_batch(chunk_texts)
                        
                        # Store chunks in database
                        await self._store_chunks(page_content, chunks_data, embeddings, database_id)
                    
                    total_chunks += len(chunks_data)
                    processed_pages += 1
                    logger.info(f"✅ Processed page {processed_pages}/{len(pages_content)} in {database_name}: {len(chunks_data)} chunks")
                    
                    # Small delay to be respectful to APIs
                    api_delay = self.benchmark_config['ingestion']['api_delay']
                    await asyncio.sleep(api_delay)
                    
                except Exception as e:
                    logger.error(f"❌ Error processing page {i+1}/{len(pages_content)} in {database_name}: {e}")
                    logger.error(f"Full traceback: {traceback.format_exc()}")
                    continue
            
            logger.info(f"✅ Database {database_name} complete! Processed {processed_pages}/{len(pages_content)} pages, created {total_chunks} chunks")
            
            # Accumulate totals
            total_chunks_all += total_chunks
            total_processed_pages_all += processed_pages
            total_pages_all += len(pages_content)
        
        logger.info(f"🎉 All databases ingestion complete! Processed {total_processed_pages_all}/{total_pages_all} pages across {len(databases)} databases, created {total_chunks_all} chunks")
        
        return {
            'processed_pages': total_processed_pages_all,
            'total_pages': total_pages_all,
            'total_chunks': total_chunks_all,
            'databases_processed': len(databases)
        }
    
    async def run_evaluation(self, k_values: List[int], qa_data_path: Path, metrics: List[str] = None):
        """Run comprehensive retrieval evaluation with multiple metrics."""
        if metrics is None:
            metrics = ['precision', 'recall', 'mrr', 'ndcg']
        
        logger.info(f"📊 Starting evaluation for k values: {k_values}")
        logger.info(f"📊 Evaluating metrics: {metrics}")
        logger.info(f"📁 Using QA data file: {qa_data_path}")
        
        if self.offline_mode:
            logger.error("❌ Evaluation requires online mode (Supabase and OpenAI services)")
            return None
        
        # Ensure database is initialized
        await self._ensure_database_initialized()
        
        # Step 1: Read QA data
        logger.info("📖 Step 1: Loading QA data...")
        with open(qa_data_path, 'r', encoding='utf-8') as f:
            qa_data = json.load(f)
        
        # Handle different QA data formats
        if isinstance(qa_data, dict) and 'verified_pairs' in qa_data:
            qa_pairs = qa_data['verified_pairs']
            qa_metadata = qa_data.get('metadata', {})
        else:
            raise ValueError(f"Unsupported QA data format. Expected dict with 'verified_pairs' key")
        
        logger.info(f"📝 Loaded {len(qa_pairs)} QA pairs for evaluation")
        logger.info(f"📋 QA data metadata: {qa_metadata}")
        
        # Step 2: Retrieve results using maximum k for efficiency
        max_k = max(k_values)
        logger.info(f"🔍 Step 2: Retrieving results with max_k={max_k}...")
        
        retrieval_results = []
        for i, qa_pair in enumerate(qa_pairs):
            query = qa_pair['question']
            expected_chunk = qa_pair['chunk_content']
            
            try:
                # Retrieve top max_k results
                filters = {
                    'database_ids': None  # Use all databases
                }
                search_results = await self.retrieval_strategy.retrieve(
                    query=query,
                    filters=filters,
                    limit=max_k
                )
                
                # Create RetrievalResults object
                retrieval_result = RetrievalResults(
                    query_id=i,
                    query=query,
                    expected_chunk=expected_chunk,
                    expected_metadata={
                        'document_id': qa_pair.get('document_id'),
                        'title': qa_pair.get('title'),
                        'author': qa_pair.get('author'),
                        'database_id': qa_pair.get('database_id')
                    },
                    retrieved_chunks=search_results
                )
                retrieval_results.append(retrieval_result)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"   Retrieved {i + 1}/{len(qa_pairs)} queries")
                
            except Exception as e:
                logger.error(f"❌ Error retrieving query {i}: {e}")
                logger.error(f"Full traceback: {traceback.format_exc()}")
                
                # Create empty result for failed queries
                retrieval_result = RetrievalResults(
                    query_id=i,
                    query=query,
                    expected_chunk=expected_chunk,
                    expected_metadata={
                        'document_id': qa_pair.get('document_id'),
                        'title': qa_pair.get('title'),
                        'author': qa_pair.get('author'),
                        'database_id': qa_pair.get('database_id')
                    },
                    retrieved_chunks=[]
                )
                retrieval_results.append(retrieval_result)
        
        # Step 3: Save retrieval results
        logger.info("💾 Step 3: Saving retrieval results...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        results_dir = Path(__file__).parent.parent / "data" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # Save detailed retrieval snapshot
        retrieval_snapshot = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'max_k': max_k,
                'total_queries': len(qa_pairs),
                'chunking_strategy': 'basic_paragraph',
                'qa_metadata': qa_metadata
            },
            'results': [
                {
                    'query_id': result.query_id,
                    'query': result.query,
                    'expected_chunk': result.expected_chunk,
                    'expected_metadata': result.expected_metadata,
                    'retrieved_chunks': result.retrieved_chunks
                }
                for result in retrieval_results
            ]
        }
        
        snapshot_filename = f"retrieval_snapshot_{timestamp}_k{max_k}.json"
        snapshot_path = results_dir / snapshot_filename
        
        with open(snapshot_path, 'w', encoding='utf-8') as f:
            json.dump(retrieval_snapshot, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"💾 Saved retrieval snapshot: {snapshot_path}")
        
        # Step 4: Analyze results with multiple metrics
        logger.info("📊 Step 4: Analyzing results with multiple metrics...")
        
        # Pass retrieval results to evaluator
        self.evaluator.set_retrieval_results(retrieval_results)
        
        # Evaluate multiple metrics using Rouge-L scoring
        evaluation_results = self.evaluator.evaluate_multiple_metrics(
            k_values=k_values,
            metrics=metrics
        )
        
        # Save individual metric results (if enabled in config)
        if self.benchmark_config['evaluation']['save_individual_results']:
            for metric_name, result in evaluation_results.items():
                self._save_metric_results(result)
        else:
            logger.info("📄 Individual metric results saving disabled by config")
        
        # Save aggregated results for cross-config comparison
        aggregated_results_path = self._save_aggregated_results(evaluation_results, k_values, metrics, qa_metadata, qa_data_path.name)
        
        # Print comprehensive results summary
        logger.info("=" * 60)
        logger.info("📈 COMPREHENSIVE EVALUATION RESULTS")
        logger.info("=" * 60)
        
        # Print results organized by metric type
        for metric_type in ['precision', 'recall', 'ndcg', 'mrr']:
            if metric_type in metrics:
                if metric_type == 'mrr':
                    if 'mrr' in evaluation_results:
                        result = evaluation_results['mrr']
                        logger.info(f"   MRR: {result.score:.3f} ({result.correct_retrievals}/{result.total_questions})")
                else:
                    logger.info(f"   {metric_type}@k:")
                    for k in sorted(k_values):
                        metric_name = f"{metric_type}_at_{k}"
                        if metric_name in evaluation_results:
                            result = evaluation_results[metric_name]
                            logger.info(f"     @{k:2d}: {result.score:.3f} ({result.correct_retrievals:2d}/{result.total_questions})")
        
        return {
            'k_values': k_values,
            'max_k_used': max_k,
            'metrics_evaluated': metrics,
            'results': evaluation_results,
            'snapshot_path': snapshot_path,
            'aggregated_results_path': aggregated_results_path,
            'total_queries': len(qa_pairs)
        }
    
    
    async def _create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for a batch of texts using decentralized OpenAI service."""
        embeddings = []
        batch_size = self.embeddings_config['batch_size']
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            logger.info(f"Processing embedding batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size} ({len(batch)} texts)")
            
            # Use decentralized OpenAI service with experiment-specific config
            batch_responses = await self.openai_service.generate_embeddings_batch(
                texts=batch,
                config=self.embeddings_config  # Pass entire config dict to API
            )
            batch_embeddings = [response.embedding for response in batch_responses]
            
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    async def _store_chunks(self, page_content: Dict[str, Any], chunks_data: List[Dict[str, Any]], 
                          embeddings: List[List[float]], database_id: str):
        """Store document and its chunks in the database."""
        client = self.database.get_client()
        
        # First, ensure database entry exists
        await self._ensure_database_exists(database_id)
        
        # Then, ensure document exists
        document_data = {
            'notion_page_id': page_content['id'],
            'notion_database_id': database_id,
            'notion_database_id_ref': database_id,
            'title': page_content['title'],
            'content': page_content['content'],
            'created_time': page_content.get('created_time'),
            'last_edited_time': page_content.get('last_edited_time'),
            'page_url': page_content.get('url'),
            'notion_properties': page_content.get('properties', {}),
            'token_count': count_tokens(page_content['content'])
        }
        
        # Upsert document
        doc_result = client.table('documents').upsert(
            document_data,
            on_conflict='notion_page_id'
        ).execute()
        
        if not doc_result.data:
            logger.error(f"Failed to upsert document: {page_content['title']}")
            return
        
        document_id = doc_result.data[0]['id']
        
        # Prepare chunks for insertion
        chunks_to_insert = []
        for i, (chunk_data, embedding) in enumerate(zip(chunks_data, embeddings)):
            chunk_record = {
                'document_id': document_id,
                'content': chunk_data['content'],
                'chunk_order': chunk_data['chunk_index'],
                'embedding': embedding,
                'token_count': chunk_data['token_count'],
                'chunk_metadata': chunk_data.get('chunk_metadata', {}),
                # Positional linking (will be updated in second pass)
                'prev_chunk_id': None,
                'next_chunk_id': None,
            }
            chunks_to_insert.append(chunk_record)
        
        # Insert chunks first
        if chunks_to_insert:
            insert_result = client.table('document_chunks').insert(chunks_to_insert).execute()
            
            # Set up prev/next relationships if we have multiple chunks
            if len(insert_result.data) > 1:
                inserted_chunks = insert_result.data
                
                # Update each chunk with prev/next relationships
                for i, chunk in enumerate(inserted_chunks):
                    updates = {}
                    
                    # Set previous chunk reference
                    if i > 0:
                        updates['prev_chunk_id'] = inserted_chunks[i - 1]['id']
                    
                    # Set next chunk reference
                    if i < len(inserted_chunks) - 1:
                        updates['next_chunk_id'] = inserted_chunks[i + 1]['id']
                    
                    # Update the chunk if there are relationships to set
                    if updates:
                        client.table('document_chunks').update(updates).eq('id', chunk['id']).execute()
    
    async def _store_chunks_offline(self, page_content: Dict[str, Any], chunks_data: List[Dict[str, Any]], database_id: str):
        """Store document and its chunks offline as JSON files."""
        page_id = page_content['id']
        
        # Create offline data structure
        offline_data = {
            'document': {
                'notion_page_id': page_content['id'],
                'notion_database_id': database_id,
                'title': page_content['title'],
                'content': page_content['content'],
                'created_time': page_content.get('created_time'),
                'last_edited_time': page_content.get('last_edited_time'),
                'page_url': page_content.get('url'),
                'notion_properties': page_content.get('properties', {}),
                'token_count': count_tokens(page_content['content'])
            },
            'chunks': chunks_data,
            'total_chunks': len(chunks_data),
            'chunking_strategy': 'basic_paragraph'
        }
        
        # Save to JSON file
        filename = f"page_{page_id.replace('-', '_')}.json"
        filepath = self.offline_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(offline_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.debug(f"📄 Saved offline data: {filepath}")
    
    async def _ensure_database_exists(self, database_id: str):
        """Ensure the database entry exists in notion_databases table."""
        client = self.database.get_client()
        
        # Check if database already exists
        existing = client.table('notion_databases').select('database_id').eq('database_id', database_id).execute()
        
        if existing.data:
            logger.debug(f"Database {database_id} already exists in notion_databases table")
            return
        
        # Find database config
        database_config = None
        for db_config in self.databases_config['databases']:
            if db_config['database_id'] == database_id:
                database_config = db_config
                break
        
        if not database_config:
            raise ValueError(f"Database configuration not found for {database_id}")
        
        # Get database schema from Notion API
        try:
            database_info = await self.notion_service.get_database(database_id)
            notion_schema = database_info
        except Exception as e:
            logger.warning(f"Failed to get database schema from Notion API: {e}. Using minimal schema.")
            notion_schema = {"properties": {}}
        
        # Insert database entry
        database_entry = {
            'database_id': database_id,
            'database_name': database_config.get('name', f'Database {database_id[:8]}'),
            'notion_access_token': os.getenv("NOTION_ACCESS_TOKEN", ""),
            'notion_schema': notion_schema,
            'field_definitions': database_config.get('field_definitions', {}),
            'queryable_fields': database_config.get('queryable_fields', {}),
            'is_active': True,
        }
        
        result = client.table('notion_databases').insert(database_entry).execute()
        
        if result.data:
            logger.info(f"✅ Created database entry for {database_config.get('name', database_id)}")
        else:
            logger.error(f"❌ Failed to create database entry for {database_id}")
            raise Exception(f"Failed to create database entry for {database_id}")
    
    def _save_metric_results(self, result):
        """Save metric evaluation results to a JSON file."""
        # Create results directory if it doesn't exist
        results_dir = Path(__file__).parent.parent / "data" / "results"
        results_dir.mkdir(exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        rouge_suffix = f"rouge{result.rouge_threshold:.1f}".replace(".", "")
        filename = f"{result.metric_name}_{rouge_suffix}_{timestamp}.json"
        results_path = results_dir / filename
        
        # Convert dataclass to dict for JSON serialization
        results_dict = {
            'metric_name': result.metric_name,
            'k_value': result.k_value,
            'score': result.score,
            'correct_retrievals': result.correct_retrievals,
            'total_questions': result.total_questions,
            'evaluation_timestamp': result.evaluation_timestamp,
            'detailed_results': result.detailed_results,
            'rouge_threshold': result.rouge_threshold,
            'metadata': result.metadata
        }
        
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 {result.metric_name} results saved to {results_path}")
    
    def _save_aggregated_results(self, evaluation_results, k_values: List[int], metrics: List[str], qa_metadata: Dict[str, Any], qa_data_filename: str):
        """Save aggregated evaluation results for cross-config comparison."""
        # Create results directory if it doesn't exist
        results_dir = Path(__file__).parent.parent / "data" / "results"
        results_dir.mkdir(exist_ok=True)
        
        # Generate filename with timestamp and config info
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        rouge_suffix = f"rouge{self.benchmark_config['evaluation']['rouge_threshold']:.1f}".replace(".", "")
        overlap_tokens = self.benchmark_config['ingestion']['overlap_tokens']
        max_tokens = self.benchmark_config['ingestion']['max_tokens']
        filename = f"aggregated_results_{rouge_suffix}_maxtkn{max_tokens}_overlap{overlap_tokens}_{timestamp}.json"
        results_path = results_dir / filename
        
        # Convert evaluation results to serializable format
        serializable_results = {}
        for metric_name, result in evaluation_results.items():
            serializable_results[metric_name] = {
                'metric_name': result.metric_name,
                'k_value': result.k_value,
                'score': result.score,
                'correct_retrievals': result.correct_retrievals,
                'total_questions': result.total_questions,
                'evaluation_timestamp': result.evaluation_timestamp,
                'rouge_threshold': result.rouge_threshold
            }
        
        # Create comprehensive aggregated results
        aggregated_data = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'k_values': k_values,
                'metrics_evaluated': metrics,
                'rouge_threshold': self.benchmark_config['evaluation']['rouge_threshold'],
                'qa_data_filename': qa_data_filename,
                'chunking_config': {
                    'max_tokens': self.benchmark_config['ingestion']['max_tokens'],
                    'overlap_tokens': self.benchmark_config['ingestion']['overlap_tokens']
                },
                'embeddings_config': self.benchmark_config['embeddings'],
                'qa_metadata': qa_metadata
            },
            'results': serializable_results,
            'summary': {
                'total_queries': len([r for r in evaluation_results.values()][0].detailed_results) if evaluation_results else 0,
                'config_fingerprint': f"maxtkn{max_tokens}_overlap{overlap_tokens}_{rouge_suffix}"
            }
        }
        
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(aggregated_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Aggregated results saved to {results_path}")
        return results_path


async def main():
    parser = argparse.ArgumentParser(description="Benchmark Basic RAG Experiment Runner")
    parser.add_argument("--clear-data", action="store_true", help="Clear existing document chunks")
    parser.add_argument("--ingest", action="store_true", help="Run basic data ingestion")
    parser.add_argument("--evaluate", action="store_true", help="Run precision@k evaluation for multiple k values")
    parser.add_argument("--full", action="store_true", help="Run full pipeline (clear + ingest + evaluate)")
    parser.add_argument("--offline", action="store_true", help="Run in offline mode (save chunks to JSON files instead of Supabase)")
    parser.add_argument("--qa-data", type=str, help="Path to the QA data file (required for evaluation)")
    
    args = parser.parse_args()
    
    if not any([args.clear_data, args.ingest, args.evaluate, args.full]):
        parser.print_help()
        return
    
    # Load benchmark configuration
    benchmark_config_path = Path(__file__).parent.parent / "config" / "benchmark.toml"
    try:
        with open(benchmark_config_path, 'rb') as f:
            benchmark_config = tomllib.load(f)
    except FileNotFoundError:
        print(f"❌ Benchmark configuration file not found: {benchmark_config_path}")
        return
    except Exception as e:
        print(f"❌ Failed to load benchmark configuration: {e}")
        return
    
    # Use default k values and metrics from config
    k_values = benchmark_config['evaluation']['k_values']
    metrics = benchmark_config['evaluation']['metrics']
    
    # Validate QA data requirement for evaluation operations
    qa_data_path = None
    if args.evaluate or args.full:
        if not args.qa_data:
            print(f"❌ --qa-data is required for evaluation operations")
            print(f"   Example: --qa-data evaluation/data/verified_qa.json")
            return
        
        qa_data_path = Path(args.qa_data)
        if not qa_data_path.is_absolute():
            qa_data_path = Path(__file__).parent.parent.parent / args.qa_data
        
        # Validate QA data file exists
        if not qa_data_path.exists():
            print(f"❌ QA data file not found: {qa_data_path}")
            return
    
    # Override rouge threshold from command line if provided
    if hasattr(args, 'rouge_threshold') and args.rouge_threshold != 0.3:
        benchmark_config['evaluation']['rouge_threshold'] = args.rouge_threshold
    
    # Initialize runner
    runner = BenchmarkBasicRAGRunner(offline_mode=args.offline, benchmark_config=benchmark_config)
    
    try:
        start_time = datetime.now()
        
        if args.full or args.clear_data:
            logger.info("=" * 60)
            logger.info("STEP 1: CLEARING DATA")
            logger.info("=" * 60)
            await runner.clear_data()
        
        if args.full or args.ingest:
            logger.info("=" * 60)
            logger.info("STEP 2: DATA INGESTION")
            logger.info("=" * 60)
            ingestion_result = await runner.run_ingestion()
        
        if args.full or args.evaluate:
            if args.offline:
                logger.info("📊 Evaluation not available in offline mode (requires Supabase)")
            else:
                logger.info("=" * 60)
                logger.info(f"STEP 3: MULTI-METRIC EVALUATION (k={k_values}, metrics={metrics})")
                logger.info("=" * 60)
                evaluation_result = await runner.run_evaluation(
                    k_values,
                    qa_data_path,
                    metrics
                )
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info("=" * 60)
        logger.info("BENCHMARK COMPLETE")
        logger.info("=" * 60)
        logger.info(f"⏱️  Total duration: {duration}")
        
        if (args.full or args.evaluate) and not args.offline and evaluation_result:
            logger.info(f"💾 Retrieval snapshot saved for offline analysis: {evaluation_result['snapshot_path']}")
            logger.info(f"💾 Aggregated results saved for cross-config comparison: {evaluation_result['aggregated_results_path']}")
    
    except Exception as e:
        logger.error(f"❌ Benchmark failed: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise


if __name__ == "__main__":
    asyncio.run(main())