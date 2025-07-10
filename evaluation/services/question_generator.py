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
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from models.evaluation_models import QuestionAnswerPair, QuestionGenerationStats

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
            self.temperature = config["models"]["temperature"]
            self.max_tokens = config["models"]["max_tokens"]
            self.timeout = config["models"]["timeout"]
        except KeyError as e:
            raise RuntimeError(f"Missing required model configuration: {e}")

        # Generation configuration
        try:
            self.questions_per_chunk = config["generation"]["questions_per_chunk"]
            self.min_questions = config["generation"]["min_questions_per_chunk"]
            self.max_questions = config["generation"]["max_questions_per_chunk"]
        except KeyError as e:
            raise RuntimeError(f"Missing required generation configuration: {e}")

        # Content filtering
        try:
            self.min_token_count = config["generation"]["min_token_count"]
            self.max_token_count = config["generation"]["max_token_count"]
            self.exclude_headers = config["generation"]["exclude_headers"]
            self.exclude_short_questions = config["generation"]["exclude_short_questions"]
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
    
    def should_process_chunk(self, chunk: Dict[str, Any]) -> bool:
        """Determine if a chunk should be processed for question generation."""
        content = chunk.get("content", "").strip()
        token_count = chunk.get("token_count", 0)
        
        # Filter by token count
        if token_count < self.min_token_count or token_count > self.max_token_count:
            logger.debug(f"Skipping chunk due to token count: {token_count}")
            return False
        
        # Filter headers
        if self.exclude_headers and content.startswith("#"):
            logger.debug(f"Skipping header chunk: {content[:50]}...")
            return False
        
        # Filter short questions
        if self.exclude_short_questions and self._is_short_question(content):
            logger.debug(f"Skipping short question chunk: {content[:50]}...")
            return False
        
        return True
    
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
        
        try:
            # Prepare the prompt
            user_prompt = self.user_prompt_template.format(
                num_questions=self.questions_per_chunk,
                content=content
            )
            
            # Make API call
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
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
    
    async def generate_questions(self, chunks_data: Dict[str, Any]) -> GenerationResult:
        """Generate questions for all processable chunks."""
        start_time = datetime.now()
        
        # Extract chunks from data structure
        document_chunks = chunks_data.get("data", {}).get("document_chunks", {})
        
        all_questions = []
        total_chunks = 0
        successful_chunks = 0
        failed_chunks = 0
        errors = []
        
        for doc_id, chunks in document_chunks.items():
            logger.info(f"Processing document {doc_id} with {len(chunks)} chunks")
            
            # Filter chunks
            processable_chunks = []
            for i, chunk in enumerate(chunks):
                if self.should_process_chunk(chunk):
                    processable_chunks.append((i, chunk))
            
            logger.info(f"Found {len(processable_chunks)} processable chunks out of {len(chunks)} total")
            total_chunks += len(processable_chunks)
            
            # Process in batches
            for i in range(0, len(processable_chunks), self.batch_size):
                batch = processable_chunks[i:i + self.batch_size]
                logger.info(f"Processing batch {i // self.batch_size + 1} with {len(batch)} chunks")
                
                # Process each chunk in the batch
                for chunk_idx, chunk in batch:
                    chunk_id = f"{doc_id}_{chunk_idx}"
                    
                    try:
                        # Extract database_id from the step 5 data structure
                        database_id = chunks_data.get("data", {}).get("database_id", "unknown")
                        
                        questions = await self.generate_questions_for_chunk(chunk, chunk_id, database_id)
                        if questions:
                            all_questions.extend(questions)
                            successful_chunks += 1
                        else:
                            failed_chunks += 1
                            errors.append(f"No questions generated for chunk {chunk_id}")
                            
                    except Exception as e:
                        failed_chunks += 1
                        error_msg = f"Error processing chunk {chunk_id}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                
                # Delay between batches to avoid rate limits
                if i + self.batch_size < len(processable_chunks):
                    await asyncio.sleep(self.delay_between_batches)
        
        end_time = datetime.now()
        generation_time = (end_time - start_time).total_seconds()
        
        result = GenerationResult(
            questions=all_questions,
            total_chunks_processed=total_chunks,
            successful_chunks=successful_chunks,
            failed_chunks=failed_chunks,
            errors=errors,
            generation_time=generation_time,
            metadata={
                "model": self.model,
                "temperature": self.temperature,
                "questions_per_chunk": self.questions_per_chunk,
                "min_token_count": self.min_token_count,
                "max_token_count": self.max_token_count,
                "generated_at": end_time.isoformat()
            }
        )
        
        logger.info(f"Question generation completed: {successful_chunks}/{total_chunks} chunks processed successfully")
        logger.info(f"Generated {len(all_questions)} total questions in {generation_time:.2f} seconds")
        
        return result