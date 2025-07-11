"""
Question Generation Service for Evaluation Dataset Creation

Generates factual and explanatory questions from text chunks using LLM.
Part of the evaluation pipeline for RAG system testing.
"""

import json
import logging
import asyncio
import os
import sys
import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from models.evaluation_models import QuestionAnswerPair, QuestionGenerationStats, ChunkQualificationStats

logger = logging.getLogger(__name__)

load_dotenv()


@dataclass
class GenerationResult:
    """Result of question generation for a set of chunks."""
    questions: List[QuestionAnswerPair]
    total_chunks_processed: int
    successful_chunks: int
    failed_chunks: int
    errors: List[str]
    generation_time: float
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class QuestionGenerator:
    """Generates questions from text chunks using OpenAI LLM."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the question generator with configuration."""
        self.config = config
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Model configuration (fail hard if required config is missing)
        try:
            self.model = config["models"]["model"]
            self.timeout = config["models"]["timeout"]
            
            # Handle temperature (reasoning models don't support custom temperature)
            if "temperature" in config["models"]:
                self.temperature = config["models"]["temperature"]
                self.use_temperature = True
                logger.info(f"Using temperature: {self.temperature}")
            else:
                self.temperature = None
                self.use_temperature = False
                logger.info("No temperature specified, using model default")
            
            # Handle both max_tokens (regular models) and max_completion_tokens (reasoning models)
            if "max_completion_tokens" in config["models"]:
                self.max_completion_tokens = config["models"]["max_completion_tokens"]
                self.max_tokens = None
                self.use_temperature = False  # Reasoning models don't support temperature
                logger.info(f"Using max_completion_tokens: {self.max_completion_tokens} (reasoning model - temperature disabled)")
            elif "max_tokens" in config["models"]:
                self.max_tokens = config["models"]["max_tokens"]
                self.max_completion_tokens = None
                logger.info(f"Using max_tokens: {self.max_tokens} (regular model)")
            else:
                raise RuntimeError("Either 'max_tokens' or 'max_completion_tokens' must be specified in models config")
                
        except KeyError as e:
            raise RuntimeError(f"Missing required model configuration: {e}")

        # Generation configuration
        try:
            self.total_questions_to_generate = config["generation"]["total_questions_to_generate"]
            self.question_heuristics = config["generation"]["question_heuristics"]
        except KeyError as e:
            raise RuntimeError(f"Missing required generation configuration: {e}")
        
        # Parse and validate heuristics configuration
        self.parsed_heuristics = self._parse_heuristics_config(self.question_heuristics)

        # Content filtering
        try:
            self.min_token_count = config["generation"]["min_token_count"]
            self.max_token_count = config["generation"]["max_token_count"]
            self.exclude_headers = config["generation"]["exclude_headers"]
            self.exclude_short_questions = config["generation"]["exclude_short_questions"]
            self.enable_qualification_stats = config["generation"]["enable_qualification_stats"]
        except KeyError as e:
            raise RuntimeError(f"Missing required content filtering configuration: {e}")

        # Batch processing
        try:
            self.batch_size = config["generation"]["batch_size"]
            self.delay_between_batches = config["generation"]["delay_between_batches"]
        except KeyError as e:
            raise RuntimeError(f"Missing required batch processing configuration: {e}")

        # Prompts
        try:
            self.system_prompt = config["prompts"]["system_prompt"]
            self.user_prompt_template = config["prompts"]["user_prompt_template"]
        except KeyError as e:
            raise RuntimeError(f"Missing required prompt configuration: {e}")
        
        logger.info(f"QuestionGenerator initialized with model: {self.model}")
        logger.info(f"Question heuristics: {self.question_heuristics}")
    
    def _parse_heuristics_config(self, heuristics: Dict[str, int]) -> List[Tuple[int, int, int]]:
        """Parse heuristics configuration from dictionary format to list of (min, max, questions) tuples."""
        parsed_ranges = []
        
        for range_str, question_count in heuristics.items():
            try:
                # Parse range string like "0-200", "201-500", "501-1000"
                if '-' not in range_str:
                    raise ValueError(f"Invalid range format: {range_str}. Expected format: 'min-max'")
                
                parts = range_str.split('-')
                if len(parts) != 2:
                    raise ValueError(f"Invalid range format: {range_str}. Expected format: 'min-max'")
                
                min_tokens = int(parts[0])
                max_tokens = int(parts[1])
                
                if min_tokens > max_tokens:
                    raise ValueError(f"Invalid range: {range_str}. Min ({min_tokens}) > Max ({max_tokens})")
                
                if question_count <= 0:
                    raise ValueError(f"Question count must be positive: {question_count} for range {range_str}")
                
                parsed_ranges.append((min_tokens, max_tokens, question_count))
                
            except ValueError as e:
                raise RuntimeError(f"Error parsing heuristics range '{range_str}': {e}")
        
        # Sort by min_tokens to ensure proper lookup order
        parsed_ranges.sort(key=lambda x: x[0])
        
        # Validate no overlaps and no gaps
        for i in range(len(parsed_ranges) - 1):
            current_max = parsed_ranges[i][1]
            next_min = parsed_ranges[i + 1][0]
            if current_max >= next_min:
                raise RuntimeError(f"Overlapping ranges: {parsed_ranges[i]} and {parsed_ranges[i + 1]}")
            if current_max + 1 != next_min:
                logger.warning(f"Gap between ranges: {current_max} and {next_min}")
        
        logger.info(f"Parsed heuristics: {parsed_ranges}")
        return parsed_ranges
    
    def get_questions_count_for_chunk(self, token_count: int) -> int:
        """Determine number of questions to generate based on token count heuristics."""
        # Find the appropriate range for this token count
        for min_tokens, max_tokens, question_count in self.parsed_heuristics:
            if min_tokens <= token_count <= max_tokens:
                return question_count
        
        # If no range matches (token count exceeds all ranges), use the highest range's question count
        if self.parsed_heuristics:
            return self.parsed_heuristics[-1][2]  # Last range's question count
        
        # Fallback if no heuristics configured
        logger.warning(f"No heuristics configured for token count {token_count}, defaulting to 2 questions")
        return 2
    
    def should_process_chunk(self, chunk: Dict[str, Any], stats: ChunkQualificationStats = None) -> Tuple[bool, str]:
        """Determine if a chunk should be processed for question generation."""
        content = chunk.get("content", "").strip()
        token_count = chunk.get("token_count", 0)
        
        # Update stats if provided
        if stats:
            stats.total_chunks_analyzed += 1
        
        # Filter by token count
        if token_count < self.min_token_count:
            if stats:
                stats.skipped_too_short += 1
            logger.debug(f"Skipping chunk due to low token count: {token_count}")
            return False, f"too_short_{token_count}"
        
        if token_count > self.max_token_count:
            if stats:
                stats.skipped_too_long += 1
            logger.debug(f"Skipping chunk due to high token count: {token_count}")
            return False, f"too_long_{token_count}"
        
        # Filter headers
        if self.exclude_headers and content.startswith("#"):
            if stats:
                stats.skipped_headers += 1
            logger.debug(f"Skipping header chunk: {content[:50]}...")
            return False, "header"
        
        # Filter short questions
        if self.exclude_short_questions and self._is_short_question(content):
            if stats:
                stats.skipped_short_questions += 1
            logger.debug(f"Skipping short question chunk: {content[:50]}...")
            return False, "short_question"
        
        # Qualified chunk
        if stats:
            stats.qualified_chunks += 1
        
        return True, "qualified"
    
    def _is_short_question(self, content: str) -> bool:
        """Check if content is just a short question or phrase."""
        # Simple heuristic: if it's very short and ends with ? or is very brief
        if content.endswith("？") or content.endswith("?"):
            # If it ends with a question mark, check if it's too short to be meaningful
            return len(content) < 20  # Short questions
        
        # For non-questions, check if it's just a brief phrase
        # Use character count instead of word count to handle Chinese text
        return len(content) < 30  # Very short phrases
    
    async def generate_questions_for_chunk(self, chunk: Dict[str, Any], chunk_id: str, database_id: str) -> List[QuestionAnswerPair]:
        """Generate questions for a single chunk."""
        content = chunk.get("content", "").strip()
        token_count = chunk.get("token_count", 0)
        
        # Determine number of questions to generate based on heuristics
        num_questions = self.get_questions_count_for_chunk(token_count)
        
        try:
            # Prepare the prompt
            user_prompt = self.user_prompt_template.format(
                num_questions=num_questions,
                content=content
            )
            
            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "timeout": self.timeout,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            }
            
            # Add temperature if supported by model
            if self.use_temperature and self.temperature is not None:
                api_params["temperature"] = self.temperature
            
            # Add the appropriate token limit parameter based on model type
            if self.max_completion_tokens is not None:
                api_params["max_completion_tokens"] = self.max_completion_tokens
            elif self.max_tokens is not None:
                api_params["max_tokens"] = self.max_tokens
            
            # Make API call
            response = self.client.chat.completions.create(**api_params)
            
            # Parse response
            response_content = response.choices[0].message.content
            logger.debug(f"Raw LLM response: {response_content}")
            
            # Extract JSON from response
            qa_pairs = self._parse_questions_response(response_content)
            
            # Convert to QuestionAnswerPair objects
            questions = []
            for qa in qa_pairs:
                question_obj = QuestionAnswerPair(
                    question=qa["question"],
                    answer=qa["answer"],
                    chunk_id=chunk_id,
                    chunk_content=content,
                    database_id=database_id,
                    chunk_metadata={
                        "token_count": chunk.get("token_count", 0),
                        "text_unit_count": chunk.get("text_unit_count", 0),
                        "start_sentence": chunk.get("start_sentence", 0),
                        "end_sentence": chunk.get("end_sentence", 0),
                        "generated_at": datetime.now().isoformat()
                    }
                )
                questions.append(question_obj)
            
            logger.info(f"Generated {len(questions)} questions for chunk {chunk_id}")
            return questions
            
        except Exception as e:
            logger.error(f"Error generating questions for chunk {chunk_id}: {str(e)}")
            return []
    
    def _parse_questions_response(self, response_content: str) -> List[Dict[str, str]]:
        """Parse the LLM response to extract questions and answers."""
        try:
            # Try to parse as JSON directly
            parsed = json.loads(response_content)
            if "questions" in parsed:
                return parsed["questions"]
            else:
                return parsed
                
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```json\n(.*?)\n```', response_content, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group(1))
                    if "questions" in parsed:
                        return parsed["questions"]
                    else:
                        return parsed
                except json.JSONDecodeError:
                    pass
            
            # If all else fails, try to parse the entire response
            try:
                parsed = json.loads(response_content)
                if "questions" in parsed:
                    return parsed["questions"]
                else:
                    return parsed
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM response: {response_content}")
                return []
    
    def _analyze_all_chunks(self, chunks_data: Dict[str, Any]) -> Tuple[List[Tuple[str, int, Dict[str, Any]]], ChunkQualificationStats]:
        """First pass: Analyze all chunks for qualification and build statistics."""
        qualification_stats = ChunkQualificationStats()
        qualified_chunks = []
        
        # Extract chunks from data structure
        document_chunks = chunks_data.get("data", {}).get("document_chunks", {})
        all_token_counts = []
        
        for doc_id, chunks in document_chunks.items():
            logger.info(f"Analyzing document {doc_id} with {len(chunks)} chunks")
            
            for i, chunk in enumerate(chunks):
                token_count = chunk.get("token_count", 0)
                all_token_counts.append(token_count)
                
                # Check if chunk qualifies
                is_qualified, reason = self.should_process_chunk(chunk, qualification_stats)
                
                if is_qualified:
                    chunk_id = f"{doc_id}_{i}"
                    qualified_chunks.append((chunk_id, i, chunk, doc_id))
        
        # Calculate additional statistics
        if all_token_counts:
            qualification_stats.average_token_count = sum(all_token_counts) / len(all_token_counts)
            
            # Token distribution
            for token_count in all_token_counts:
                if token_count <= 200:
                    bucket = "0-200"
                elif token_count <= 500:
                    bucket = "200-500"
                elif token_count <= 1000:
                    bucket = "500-1000"
                else:
                    bucket = "1000+"
                
                qualification_stats.token_distribution[bucket] = qualification_stats.token_distribution.get(bucket, 0) + 1
        
        logger.info(f"Qualification complete: {qualification_stats.qualified_chunks}/{qualification_stats.total_chunks_analyzed} chunks qualified")
        
        return qualified_chunks, qualification_stats
    
    def _random_sample_chunks(self, qualified_chunks: List[Tuple[str, int, Dict[str, Any], str]]) -> Tuple[List[Tuple[str, int, Dict[str, Any], str]], Dict[str, Any]]:
        """Second pass: Random sampling to limit total questions generated."""
        if len(qualified_chunks) <= self.total_questions_to_generate:
            # If we have fewer qualified chunks than desired questions, use all of them
            sampled_chunks = qualified_chunks
            sampling_stats = {
                "total_qualified": len(qualified_chunks),
                "sample_size": len(qualified_chunks),
                "sampling_rate": 1.0,
                "sampling_method": "all_chunks"
            }
        else:
            # Random sampling
            sampled_chunks = random.sample(qualified_chunks, self.total_questions_to_generate)
            sampling_stats = {
                "total_qualified": len(qualified_chunks),
                "sample_size": len(sampled_chunks),
                "sampling_rate": len(sampled_chunks) / len(qualified_chunks),
                "sampling_method": "random"
            }
        
        logger.info(f"Sampling complete: {len(sampled_chunks)} chunks selected from {len(qualified_chunks)} qualified")
        
        return sampled_chunks, sampling_stats
    
    async def generate_questions(self, chunks_data: Dict[str, Any]) -> GenerationResult:
        """Generate questions with two-pass approach: qualification then random sampling."""
        start_time = datetime.now()
        
        # Phase 1: Analyze all chunks for qualification
        logger.info("🔍 Phase 1: Analyzing chunk qualification...")
        qualified_chunks, qualification_stats = self._analyze_all_chunks(chunks_data)
        
        if qualification_stats.qualified_chunks == 0:
            logger.warning("No qualified chunks found!")
            return GenerationResult(
                questions=[],
                total_chunks_processed=0,
                successful_chunks=0,
                failed_chunks=0,
                errors=["No qualified chunks found"],
                generation_time=0.0,
                metadata={"qualification_stats": qualification_stats.model_dump()}
            )
        
        # Phase 2: Random sampling to control total question count
        logger.info("🎲 Phase 2: Random sampling for question generation...")
        sampled_chunks, sampling_stats = self._random_sample_chunks(qualified_chunks)
        
        # Phase 3: Generate questions for sampled chunks
        logger.info(f"🤖 Phase 3: Generating questions for {len(sampled_chunks)} sampled chunks...")
        
        all_questions = []
        successful_chunks = 0
        failed_chunks = 0
        errors = []
        heuristic_breakdown = {}
        
        # Extract database_id from the step 5 data structure
        database_id = chunks_data.get("data", {}).get("database_id", "unknown")
        
        # Process in batches
        for i in range(0, len(sampled_chunks), self.batch_size):
            batch = sampled_chunks[i:i + self.batch_size]
            logger.info(f"Processing batch {i // self.batch_size + 1} with {len(batch)} chunks")
            
            # Process each chunk in the batch
            for chunk_id, chunk_idx, chunk, doc_id in batch:
                try:
                    # Track heuristic breakdown
                    token_count = chunk.get("token_count", 0)
                    num_questions = self.get_questions_count_for_chunk(token_count)
                    heuristic_key = f"{num_questions}_questions"
                    heuristic_breakdown[heuristic_key] = heuristic_breakdown.get(heuristic_key, 0) + 1
                    
                    questions = await self.generate_questions_for_chunk(chunk, chunk_id, database_id)
                    if questions:
                        all_questions.extend(questions)
                        successful_chunks += 1
                        logger.debug(f"✅ Generated {len(questions)} questions for chunk {chunk_id}")
                    else:
                        failed_chunks += 1
                        errors.append(f"No questions generated for chunk {chunk_id}")
                        
                except Exception as e:
                    failed_chunks += 1
                    error_msg = f"Error processing chunk {chunk_id}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # Delay between batches to avoid rate limits
            if i + self.batch_size < len(sampled_chunks):
                await asyncio.sleep(self.delay_between_batches)
        
        end_time = datetime.now()
        generation_time = (end_time - start_time).total_seconds()
        
        # Create comprehensive stats
        generation_stats = QuestionGenerationStats(
            total_chunks_processed=len(sampled_chunks),
            successful_chunks=successful_chunks,
            failed_chunks=failed_chunks,
            total_questions_generated=len(all_questions),
            generation_time_seconds=generation_time,
            qualification_stats=qualification_stats,
            heuristic_breakdown=heuristic_breakdown,
            sampling_stats=sampling_stats,
            errors=errors
        )
        
        result = GenerationResult(
            questions=all_questions,
            total_chunks_processed=len(sampled_chunks),
            successful_chunks=successful_chunks,
            failed_chunks=failed_chunks,
            errors=errors,
            generation_time=generation_time,
            metadata={
                "model": self.model,
                "temperature": self.temperature,
                "question_heuristics": self.question_heuristics,
                "parsed_heuristics": [f"{min_t}-{max_t}: {q}q" for min_t, max_t, q in self.parsed_heuristics],
                "min_token_count": self.min_token_count,
                "max_token_count": self.max_token_count,
                "total_questions_target": self.total_questions_to_generate,
                "generation_stats": generation_stats.model_dump(),
                "generated_at": end_time.isoformat()
            }
        )
        
        logger.info(f"✅ Question generation completed: {successful_chunks}/{len(sampled_chunks)} chunks processed successfully")
        logger.info(f"🎯 Generated {len(all_questions)} total questions in {generation_time:.2f} seconds")
        logger.info(f"📊 Qualification stats: {qualification_stats.qualified_chunks} qualified from {qualification_stats.total_chunks_analyzed} analyzed")
        logger.info(f"🎲 Sampling stats: {sampling_stats['sample_size']} selected from {sampling_stats['total_qualified']} qualified")
        
        return result