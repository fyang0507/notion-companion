#!/usr/bin/env python3
"""
Question Generation Script for Evaluation Dataset Creation

Generates factual and explanatory questions from text chunks using LLM.
This is the "teacher" step in the evaluation pipeline.

Usage:
    python generate_questions.py --input-file chunks.json --output-file questions.json [--config config.toml]
"""

import argparse
import json
import logging
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add the evaluation directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.question_generator import QuestionGenerator
from utils.config_loader import load_config


def setup_logging(log_level: str = "INFO") -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(Path(__file__).parent.parent / "logs" / "question_generation.log")
        ]
    )


def validate_input_file(input_file: Path) -> Dict[str, Any]:
    """Validate and load the input chunks file."""
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate structure
        if "data" not in data:
            raise ValueError("Input file must contain 'data' key")
        
        if "document_chunks" not in data["data"]:
            raise ValueError("Input file must contain 'data.document_chunks' key")
        
        # Count total chunks
        total_chunks = sum(len(chunks) for chunks in data["data"]["document_chunks"].values())
        logging.info(f"Loaded {len(data['data']['document_chunks'])} documents with {total_chunks} total chunks")
        
        return data
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in input file: {e}")


def save_results(results: Dict[str, Any], output_file: Path) -> None:
    """Save the question generation results to file."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logging.info(f"Results saved to {output_file}")


def format_results(generation_result, input_metadata: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Format the generation results for output."""
    
    # Convert QuestionAnswerPair objects to dictionaries
    questions_data = []
    for qa in generation_result.questions:
        questions_data.append({
            "question": qa.question,
            "answer": qa.answer,
            "chunk_id": qa.chunk_id,
            "chunk_content": qa.chunk_content,
            "database_id": qa.database_id,
            "confidence": qa.confidence,
            "chunk_metadata": qa.chunk_metadata
        })
    
    return {
        "metadata": {
            "step_number": 6,
            "step_name": "question_generation",
            "experiment_id": datetime.now().strftime("%Y%m%d_%H%M"),
            "experiment_name": "question_generation",
            "generated_at": datetime.now().isoformat(),
            "input_file_metadata": input_metadata,
            "config_snapshot": config,
            "generation_stats": {
                "total_chunks_processed": generation_result.total_chunks_processed,
                "successful_chunks": generation_result.successful_chunks,
                "failed_chunks": generation_result.failed_chunks,
                "total_questions_generated": len(generation_result.questions),
                "generation_time_seconds": generation_result.generation_time,
                "errors": generation_result.errors
            }
        },
        "data": {
            "questions": questions_data
        }
    }


async def main():
    """Main function to orchestrate question generation."""
    parser = argparse.ArgumentParser(description="Generate questions from text chunks")
    parser.add_argument("--input-file", "-i", type=Path, required=True,
                        help="Input JSON file containing text chunks")
    parser.add_argument("--output-file", "-o", type=Path, 
                        help="Output JSON file for questions (auto-generated if not provided)")
    parser.add_argument("--config", "-c", type=Path,
                        default=Path(__file__).parent.parent / "config" / "question_generation.toml",
                        help="Configuration file (default: config/question_generation.toml)")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        default="INFO", help="Logging level")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting question generation process")
    logger.info(f"Input file: {args.input_file}")
    logger.info(f"Config file: {args.config}")
    
    try:
        # Load configuration
        config = load_config(args.config)
        logger.info("Configuration loaded successfully")
        
        # Validate OpenAI API key
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Load and validate input data
        input_data = validate_input_file(args.input_file)
        
        # Generate output filename if not provided
        if not args.output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            output_filename = f"{timestamp}_step6_question_generation.json"
            args.output_file = args.input_file.parent / output_filename
        
        logger.info(f"Output file: {args.output_file}")
        
        # Initialize question generator
        generator = QuestionGenerator(config)
        
        # Generate questions
        logger.info("Starting question generation...")
        generation_result = await generator.generate_questions(input_data)
        
        # Format results
        results = format_results(generation_result, input_data.get("metadata", {}), config)
        
        # Save results
        save_results(results, args.output_file)
        
        # Print summary
        stats = results["metadata"]["generation_stats"]
        logger.info("Question generation completed successfully!")
        logger.info(f"Processed {stats['successful_chunks']}/{stats['total_chunks_processed']} chunks")
        logger.info(f"Generated {stats['total_questions_generated']} questions")
        logger.info(f"Generation time: {stats['generation_time_seconds']:.2f} seconds")
        
        if stats['failed_chunks'] > 0:
            logger.warning(f"Failed to process {stats['failed_chunks']} chunks")
            for error in stats['errors']:
                logger.warning(f"Error: {error}")
        
        print(f"\n✅ Question generation completed!")
        print(f"📊 Results: {stats['total_questions_generated']} questions from {stats['successful_chunks']} chunks")
        print(f"💾 Output saved to: {args.output_file}")
        
    except Exception as e:
        logger.error(f"Question generation failed: {str(e)}")
        print(f"\n❌ Question generation failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())