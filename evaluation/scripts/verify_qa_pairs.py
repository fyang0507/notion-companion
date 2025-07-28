#!/usr/bin/env python3
"""
QA Self-Verification Script

CLI script to run self-verification on candidate Q&A pairs to ensure quality.
For every ⟨q, a⟩ pair, asks the same LLM to answer q given the full doc.
Keeps only if the answer contains the exact gold span (string match or ≥ 0.9 Rouge-L).

Usage:
    python verify_qa_pairs.py --qa-pairs qa_pairs.json --step5-data step5_chunks.json --output verified_qa_pairs.json
    python verify_qa_pairs.py --qa-pairs qa_pairs.json --step5-data step5_chunks.json --config custom_config.toml
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import tomllib
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents import AsyncOpenAI, set_default_openai_client, set_default_openai_api, enable_verbose_stdout_logging
from models.evaluation_models import QuestionAnswerPair
from services.qa_self_verifier import QASelfVerifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Path(__file__).parent.parent / "logs" / "qa_self_verification.log")
    ]
)
logger = logging.getLogger(__name__)

def load_config(config_path: str) -> Dict[str, Any]:
    """Load verification configuration from TOML file."""
    try:
        with open(config_path, 'rb') as f:
            config = tomllib.load(f)
        logger.info(f"📝 Loaded configuration from {config_path}")
        return config
    except Exception as e:
        logger.error(f"❌ Error loading config from {config_path}: {e}")
        raise

def load_qa_pairs(qa_pairs_path: str) -> List[QuestionAnswerPair]:
    """Load Q&A pairs from JSON file."""
    try:
        with open(qa_pairs_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle different JSON structures
        qa_data = []
        if isinstance(data, dict):
            if "questions" in data:
                qa_data = data["questions"]
            elif "qa_pairs" in data:
                qa_data = data["qa_pairs"]
            elif "data" in data and "questions" in data["data"]:
                qa_data = data["data"]["questions"]
            else:
                # Assume the dict contains the QA pairs directly
                qa_data = data
        elif isinstance(data, list):
            qa_data = data
        else:
            raise ValueError(f"Unsupported JSON structure: {type(data)}")
        
        # Convert to QuestionAnswerPair objects
        qa_pairs = []
        for item in qa_data:
            if isinstance(item, dict):
                qa_pair = QuestionAnswerPair(**item)
                qa_pairs.append(qa_pair)
            else:
                logger.warning(f"Skipping invalid QA item: {item}")
        
        logger.info(f"📥 Loaded {len(qa_pairs)} Q&A pairs from {qa_pairs_path}")
        return qa_pairs
        
    except Exception as e:
        logger.error(f"❌ Error loading Q&A pairs from {qa_pairs_path}: {e}")
        raise

def load_step5_data(step5_path: str) -> Dict[str, Any]:
    """Load step 5 semantic merging data from JSON file."""
    try:
        with open(step5_path, 'r', encoding='utf-8') as f:
            step5_data = json.load(f)
        
        logger.info(f"📥 Loaded step 5 data from {step5_path}")
        
        # Log basic statistics about the step 5 data
        if isinstance(step5_data, dict) and "data" in step5_data:
            document_chunks = step5_data["data"].get("document_chunks", {})
            total_docs = len(document_chunks)
            total_chunks = sum(len(chunks) for chunks in document_chunks.values())
            logger.info(f"📊 Step 5 data contains {total_docs} documents with {total_chunks} total chunks")
            
            # Log metadata if available
            metadata = step5_data.get("metadata", {})
            if metadata:
                step_name = metadata.get("step_name", "unknown")
                experiment_id = metadata.get("experiment_id", "unknown")
                logger.info(f"📋 Step: {step_name}, Experiment ID: {experiment_id}")
        
        return step5_data
        
    except Exception as e:
        logger.error(f"❌ Error loading step 5 data from {step5_path}: {e}")
        raise

async def main():
    """Main verification process."""
    parser = argparse.ArgumentParser(description="Self-verification for Q&A pairs using full document context")
    parser.add_argument("--qa-pairs", required=True, help="Path to Q&A pairs JSON file")
    parser.add_argument("--step5-data", required=True, help="Path to step 5 semantic merging JSON file")
    parser.add_argument("--output", required=True, help="Path for verified Q&A pairs output file")
    parser.add_argument("--config", default=None, help="Path to custom verification config file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        enable_verbose_stdout_logging()
    
    logger.info("🚀 Starting QA Self-Verification Process")
    
    # Load environment variables
    load_dotenv()
    
    # Set up OpenAI client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("❌ OPENAI_API_KEY environment variable not set")
        return 1
    
    set_default_openai_api("chat_completions")
    openai_client = AsyncOpenAI(api_key=api_key)
    set_default_openai_client(openai_client)
    
    try:
        # Load configuration
        config_path = args.config or str(Path(__file__).parent.parent / "config" / "qa_verification.toml")
        config = load_config(config_path)
        
        # Load Q&A pairs
        qa_pairs = load_qa_pairs(args.qa_pairs)
        if not qa_pairs:
            logger.error("❌ No Q&A pairs loaded")
            return 1
        
        # Load step 5 data
        step5_data = load_step5_data(args.step5_data)
        
        # Initialize verifier
        verifier = QASelfVerifier(config, openai_client)
        
        # Run verification
        logger.info(f"🔍 Starting verification for {len(qa_pairs)} Q&A pairs...")
        results = await verifier.verify_qa_pairs(qa_pairs, step5_data)
        
        # Save results
        verifier.save_verification_results(results, args.output)
        
        # Print summary
        logger.info("="*60)
        logger.info("📊 VERIFICATION SUMMARY")
        logger.info("="*60)
        logger.info(f"Total Q&A pairs processed: {results.total_processed}")
        logger.info(f"Successfully verified: {results.total_verified}")
        logger.info(f"Failed verification: {results.total_failed}")
        logger.info(f"Verification rate: {results.verification_rate:.1f}%")
        logger.info(f"Processing time: {results.processing_time:.2f} seconds")
        logger.info(f"Average Rouge-L score: {results.metadata.get('average_rouge_score', 0):.3f}")
        logger.info("="*60)
        logger.info(f"✅ Verified Q&A pairs saved to: {args.output}")
        
        # Return non-zero exit code if verification rate is too low
        min_verification_rate = 50.0  # Minimum acceptable verification rate
        if results.verification_rate < min_verification_rate:
            logger.warning(f"⚠️  Low verification rate ({results.verification_rate:.1f}%) - consider reviewing Q&A generation process")
            return 2
        
        logger.info("✅ QA Self-Verification completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        logger.info("⏹️  Verification interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"❌ Verification failed: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)