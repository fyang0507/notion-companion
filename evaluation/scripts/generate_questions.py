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
                "errors": generation_result.errors,
                # Include heuristics configuration for display
                "question_heuristics": generation_result.metadata.get("question_heuristics", {}),
                # Include comprehensive stats from new implementation
                **generation_result.metadata.get("generation_stats", {})
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
        
        # Print comprehensive summary
        stats = results["metadata"]["generation_stats"]
        logger.info("Question generation completed successfully!")
        
        # Print detailed statistics
        print_comprehensive_stats(stats)
        
        if stats['failed_chunks'] > 0:
            logger.warning(f"Failed to process {stats['failed_chunks']} chunks")
            for error in stats['errors']:
                logger.warning(f"Error: {error}")
        
        print(f"\n✅ Question generation completed!")
        print(f"💾 Output saved to: {args.output_file}")
        
    except Exception as e:
        logger.error(f"Question generation failed: {str(e)}")
        print(f"\n❌ Question generation failed: {str(e)}")
        sys.exit(1)


def print_comprehensive_stats(stats: Dict[str, Any]):
    """Print comprehensive statistics about the question generation process."""
    print("\n" + "="*80)
    print("📊 COMPREHENSIVE QUESTION GENERATION STATISTICS")
    print("="*80)
    
    # Basic stats
    print(f"\n🎯 GENERATION RESULTS:")
    print(f"  • Total questions generated: {stats['total_questions_generated']}")
    print(f"  • Chunks processed: {stats['successful_chunks']}/{stats['total_chunks_processed']}")
    print(f"  • Success rate: {stats['successful_chunks']/stats['total_chunks_processed']*100:.1f}%")
    print(f"  • Generation time: {stats['generation_time_seconds']:.2f} seconds")
    
    # Qualification stats
    if 'qualification_stats' in stats:
        qual_stats = stats['qualification_stats']
        print(f"\n🔍 CHUNK QUALIFICATION ANALYSIS:")
        print(f"  • Total chunks analyzed: {qual_stats['total_chunks_analyzed']}")
        print(f"  • Qualified chunks: {qual_stats['qualified_chunks']}")
        print(f"  • Qualification rate: {qual_stats['qualified_chunks']/qual_stats['total_chunks_analyzed']*100:.1f}%")
        print(f"  • Average token count: {qual_stats['average_token_count']:.1f}")
        
        print(f"\n  📈 Skipping Breakdown:")
        print(f"    - Too short: {qual_stats['skipped_too_short']}")
        print(f"    - Too long: {qual_stats['skipped_too_long']}")
        print(f"    - Headers: {qual_stats['skipped_headers']}")
        print(f"    - Short questions: {qual_stats['skipped_short_questions']}")
        
        if qual_stats['token_distribution']:
            print(f"\n  📊 Token Distribution:")
            for bucket, count in qual_stats['token_distribution'].items():
                print(f"    - {bucket} tokens: {count} chunks")
    
    # Sampling stats
    if 'sampling_stats' in stats:
        sampling = stats['sampling_stats']
        print(f"\n🎲 RANDOM SAMPLING:")
        print(f"  • Total qualified: {sampling['total_qualified']}")
        print(f"  • Sample size: {sampling['sample_size']}")
        print(f"  • Sampling rate: {sampling['sampling_rate']*100:.1f}%")
        print(f"  • Method: {sampling['sampling_method']}")
    
    # Show configured heuristics
    if 'question_heuristics' in stats:
        heuristics = stats['question_heuristics']
        print(f"\n⚙️  CONFIGURED HEURISTICS:")
        for token_range, question_count in sorted(heuristics.items()):
            print(f"  • {token_range} tokens → {question_count} questions")
    
    # Heuristic breakdown (actual results)
    if 'heuristic_breakdown' in stats:
        heuristic = stats['heuristic_breakdown']
        print(f"\n🤖 APPLIED HEURISTIC RESULTS:")
        total_processed = sum(heuristic.values())
        for question_count, chunk_count in sorted(heuristic.items()):
            percentage = chunk_count / total_processed * 100 if total_processed > 0 else 0
            print(f"  • {question_count}: {chunk_count} chunks ({percentage:.1f}%)")
    
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())