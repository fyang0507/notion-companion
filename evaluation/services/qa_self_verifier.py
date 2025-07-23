"""
QA Self-Verification Service for Evaluation Dataset Quality Assurance

Implements self-verification step on candidate Q&A pairs to ensure quality:
1. For every ⟨q, a⟩ pair, ask the same LLM to answer q given the full doc
2. Keep only if the answer contains the exact gold span (string match or ≥ 0.9 Rouge-L)
3. Handle context window limitations with context expansion from answer chunks

This ensures noisy items are discarded automatically through LLM self-validation.
"""

import json
import logging
import asyncio
import re
import math
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from agents import AsyncOpenAI, ModelSettings, trace, ModelTracing
from rouge_score import rouge_scorer
from rouge_score.tokenizers import Tokenizer
import tiktoken
import openai

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from models.evaluation_models import QuestionAnswerPair

logger = logging.getLogger(__name__)

class MultilingualTokenizer(Tokenizer):
    """Custom tokenizer for handling Chinese and English text in Rouge scoring."""
    
    def tokenize(self, text):
        """
        Tokenize text handling both Chinese characters and English words.
        Chinese: Each character is a token
        English: Words split by whitespace and punctuation
        """
        import re
        
        tokens = []
        
        # Pattern to match:
        # - Chinese characters (CJK Unified Ideographs)
        # - English words (sequences of letters)
        # - Numbers
        # NOTE: Punctuation is not tokenized, it's acceptable because Rouge-L focuses on content similarity, not punctuation exactness
        pattern = r'[\u4e00-\u9fff]|[a-zA-Z]+|\d+'
        
        matches = re.finditer(pattern, text)
        for match in matches:
            token = match.group().lower()
            tokens.append(token)
        
        return tokens

@dataclass
class VerificationResult:
    """Result of self-verification for a single Q&A pair."""
    qa_pair: QuestionAnswerPair
    llm_extracted_text: str
    verification_score: float  # Rouge-L score against chunk_content (reference text)
    is_verified: bool  # Whether this Q&A pair passed verification
    verification_time: float
    context_used: str  # The context provided to LLM for verification
    reference_used: str  # What we compared against (chunk_content vs answer)
    document_metadata: Dict[str, Any]  # Document metadata from step5 data
    error: Optional[str] = None

@dataclass
class BatchVerificationResult:
    """Result of batch verification for multiple Q&A pairs."""
    verified_pairs: List[QuestionAnswerPair]
    verification_results: List[VerificationResult]
    total_processed: int
    total_verified: int
    total_failed: int
    verification_rate: float  # Percentage of pairs that passed verification
    processing_time: float
    metadata: Dict[str, Any]

class QASelfVerifier:
    """Self-verification service for Q&A pairs using LLM re-answering."""
    
    def __init__(self, config: Dict[str, Any], openai_client: AsyncOpenAI):
        """Initialize the self-verifier with configuration."""
        self.config = config
        self.openai_client = openai_client
        
        # Model configuration
        try:
            self.model = config["models"]["model"]
            self.openai_model = OpenAIChatCompletionsModel(
                openai_client=openai_client,
                model=self.model
            )
        except KeyError as e:
            raise RuntimeError(f"Missing required model configuration: {e}")

        # Verification configuration
        try:
            self.rouge_threshold = config["verification"]["rouge_threshold"]
            self.context_expansion_chunks = config["verification"]["context_expansion_chunks"]
            self.max_context_tokens = config["verification"]["max_context_tokens"]
            self.batch_size = config["verification"]["batch_size"]
            self.delay_between_batches = config["verification"]["delay_between_batches"]
            self.retry_rate_limit_delay = config["verification"]["retry_rate_limit_delay"]
            self.max_retries = config["verification"]["max_retries"]
        except KeyError as e:
            raise RuntimeError(f"Missing required verification configuration: {e}")
        
        # Prompts
        try:
            self.system_prompt = config["prompts"]["verification_system_prompt"]
            self.user_prompt_template = config["prompts"]["verification_user_prompt_template"]
        except KeyError as e:
            raise RuntimeError(f"Missing required prompt configuration: {e}")

        # Initialize Rouge scorer with multilingual tokenizer
        multilingual_tokenizer = MultilingualTokenizer()
        self.rouge_scorer = rouge_scorer.RougeScorer(
            ['rougeL'], 
            use_stemmer=False,  # Disable stemming for multilingual text
            tokenizer=multilingual_tokenizer
        )
        # Use standard tokenizer for token counting (independent of verification model)
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        logger.info(f"QASelfVerifier initialized with model: {self.model}")
        logger.info(f"Rouge threshold: {self.rouge_threshold}, Context expansion: {self.context_expansion_chunks} chunks")
        logger.info(f"Rate limit retry: max {self.max_retries} attempts, {self.retry_rate_limit_delay}s delay")

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using the model's tokenizer."""
        return len(self.tokenizer.encode(text))

    def _extract_chunks_from_step5_data(self, step5_data: Dict[str, Any], chunk_id: str) -> Tuple[List[Dict[str, Any]], int, str]:
        """Extract the document chunks and find the target chunk index from step 5 semantic merging data."""
        try:
            # Parse chunk_id to get document ID and chunk index
            # Example: "1519782c-4f4a-80a0-b69f-e147edbd5280_34" -> doc_id="1519782c-4f4a-80a0-b69f-e147edbd5280", chunk_idx=34
            parts = chunk_id.split("_")
            chunk_index = int(parts[-1])  # Last part is chunk index
            document_id = "_".join(parts[:-1])  # Everything except last part is document ID
            
            # Get document chunks from step 5 data
            document_chunks = step5_data.get("data", {}).get("document_chunks", {})
            
            if document_id not in document_chunks:
                raise ValueError(f"Document {document_id} not found in step 5 chunks data")
            
            chunks = document_chunks[document_id]
            
            if chunk_index >= len(chunks):
                raise ValueError(f"Chunk index {chunk_index} out of range for document {document_id} (has {len(chunks)} chunks)")
            
            logger.debug(f"Found document {document_id} with {len(chunks)} chunks, target chunk index: {chunk_index}")
            return chunks, chunk_index, document_id
            
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing chunk_id {chunk_id}: {e}")
            return [], 0, ""
        except Exception as e:
            logger.error(f"Error extracting chunks for chunk {chunk_id}: {e}")
            return [], 0, ""

    def _extract_document_metadata(self, chunks: List[Dict[str, Any]], target_chunk_index: int, document_id: str) -> Dict[str, Any]:
        """Extract document metadata from the target chunk's document_metadata."""
        try:
            if not chunks or target_chunk_index >= len(chunks):
                return {}
            
            target_chunk = chunks[target_chunk_index]
            doc_metadata = target_chunk.get("document_metadata", {})
            
            # Extract key metadata fields
            metadata = {}
            
            # Basic document info
            if "title" in doc_metadata:
                metadata["title"] = doc_metadata["title"]
            if "database_id" in doc_metadata:
                metadata["database_id"] = doc_metadata["database_id"]
            
            # Use the actual document_id from step5 data (passed as parameter)
            metadata["document_id"] = document_id
            
            # Extract properties from extracted_metadata
            extracted_metadata = doc_metadata.get("extracted_metadata", {})
            if extracted_metadata:
                # Common properties to include
                property_fields = ["Author", "Status", "Date", "Select", "Multi-select"]
                for field in property_fields:
                    if field in extracted_metadata:
                        metadata[field.lower()] = extracted_metadata[field]
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting document metadata: {e}")
            return {}

    def _build_context_with_chunk_expansion(self, chunks: List[Dict[str, Any]], target_chunk_index: int) -> str:
        """Build context using chunk expansion strategy: grow from target chunk by adding surrounding chunks."""
        if not chunks or target_chunk_index >= len(chunks):
            return ""
        
        # Start with the target chunk (the chunk containing the answer)
        target_chunk = chunks[target_chunk_index]
        context_parts = [target_chunk.get("content", "")]
        current_tokens = self._count_tokens(context_parts[0])
        
        # If target chunk alone exceeds limit, truncate it
        if current_tokens > self.max_context_tokens:
            max_chars = self.max_context_tokens * 4
            truncated_content = target_chunk.get("content", "")[:max_chars]
            logger.debug(f"Target chunk too large, truncated to {self._count_tokens(truncated_content)} tokens")
            return truncated_content
        
        # Expand by adding chunks before and after alternately
        expansion_distance = 1
        max_expansion = self.context_expansion_chunks
        
        while expansion_distance <= max_expansion and current_tokens < self.max_context_tokens:
            added_chunk = False
            
            # Try to add chunk before target
            before_idx = target_chunk_index - expansion_distance
            if before_idx >= 0:
                before_content = chunks[before_idx].get("content", "")
                before_tokens = self._count_tokens(before_content)
                
                if current_tokens + before_tokens <= self.max_context_tokens:
                    context_parts.insert(0, before_content)  # Add at beginning
                    current_tokens += before_tokens
                    added_chunk = True
                    logger.debug(f"Added chunk {before_idx} before target (now {current_tokens} tokens)")
            
            # Try to add chunk after target
            after_idx = target_chunk_index + expansion_distance
            if after_idx < len(chunks) and current_tokens < self.max_context_tokens:
                after_content = chunks[after_idx].get("content", "")
                after_tokens = self._count_tokens(after_content)
                
                if current_tokens + after_tokens <= self.max_context_tokens:
                    context_parts.append(after_content)  # Add at end
                    current_tokens += after_tokens
                    added_chunk = True
                    logger.debug(f"Added chunk {after_idx} after target (now {current_tokens} tokens)")
            
            # If we couldn't add any more chunks at this distance, stop expanding
            if not added_chunk:
                break
                
            expansion_distance += 1
        
        # Join all chunks with double newlines
        expanded_context = "\n\n".join(context_parts)
        
        final_tokens = self._count_tokens(expanded_context)
        start_idx = max(0, target_chunk_index - (expansion_distance - 1))
        end_idx = min(len(chunks) - 1, target_chunk_index + (expansion_distance - 1))
        
        logger.debug(f"Built context with chunks {start_idx}-{end_idx} around target {target_chunk_index} ({final_tokens} tokens)")
        return expanded_context

    def _calculate_rouge_l_score(self, llm_extracted_text: str, chunk_content: str) -> float:
        """Calculate Rouge-L score between reference and candidate answers."""
        try:
            scores = self.rouge_scorer.score(llm_extracted_text.lower().strip(), chunk_content.lower().strip())
            return scores['rougeL'].recall # NOTE: use recall to respect the fact that llm_extracted_text is shorter than chunk_content
        except Exception as e:
            logger.error(f"Error calculating Rouge-L score: {e}")
            return 0.0

    async def _make_openai_request_with_retry(self, system_prompt: str, user_prompt: str) -> Any:
        """Make OpenAI API request with simple rate limit retry."""
        attempt = 0
        while attempt <= self.max_retries:
            try:
                # Make API call within trace context for proper span capture
                with trace(f"qa_verification_{datetime.now().strftime('%Y%m%d_%H%M')}"):
                    response = await self.openai_model.get_response(
                        system_instructions=system_prompt,
                        input=user_prompt,
                        model_settings=ModelSettings(),
                        tools=[],
                        output_schema=None,
                        handoffs=[],
                        tracing=ModelTracing.ENABLED,
                        previous_response_id=None,
                    )
                return response
            
            except Exception as e:
                # Check if this is a rate limit error
                is_rate_limit = (
                    isinstance(e, openai.RateLimitError) or
                    "429" in str(e) or
                    "rate limit" in str(e).lower()
                )
                
                if is_rate_limit and attempt < self.max_retries:
                    attempt += 1
                    logger.warning(f"Rate limit hit. Attempt {attempt}/{self.max_retries}. Waiting {self.retry_rate_limit_delay} seconds...")
                    await asyncio.sleep(self.retry_rate_limit_delay)
                    # Continue the loop to retry
                else:
                    # Not a rate limit error or max retries exceeded
                    if is_rate_limit:
                        logger.error(f"Rate limit persisted after {self.max_retries} retries. Giving up.")
                    raise e


    async def _verify_single_qa_pair(self, qa_pair: QuestionAnswerPair, step5_data: Dict[str, Any]) -> VerificationResult:
        """Verify a single Q&A pair by re-answering with expanded chunk context."""
        start_time = datetime.now()
        
        try:
            # Extract chunks and find target chunk index
            chunks, target_chunk_index, document_id = self._extract_chunks_from_step5_data(step5_data, qa_pair.chunk_id)
            
            if not chunks:
                return VerificationResult(
                    qa_pair=qa_pair,
                    llm_extracted_text="",
                    verification_score=0.0,
                    is_verified=False,
                    verification_time=0.0,
                    context_used="",
                    reference_used="chunk_content",
                    document_metadata={},
                    error="Could not extract chunks from step 5 data"
                )
            
            # Build context using chunk expansion strategy
            context = self._build_context_with_chunk_expansion(chunks, target_chunk_index)
            
            # Extract document metadata
            doc_metadata = self._extract_document_metadata(chunks, target_chunk_index, document_id)
            
            # Prepare verification prompt
            user_prompt = self.user_prompt_template.format(
                question=qa_pair.question,
                context=context
            )
            
            # Get LLM's answer using the full document context with retry logic
            response = await self._make_openai_request_with_retry(self.system_prompt, user_prompt)
            
            # Parse response
            response_content = response.output[0].content
            if isinstance(response_content, list) and response_content:
                first_item = response_content[0]
                if hasattr(first_item, 'text'):
                    llm_extracted_text = first_item.text
                else:
                    llm_extracted_text = str(first_item)
            elif hasattr(response_content, 'text'):
                llm_extracted_text = response_content.text
            elif isinstance(response_content, str):
                llm_extracted_text = response_content
            else:
                llm_extracted_text = str(response_content)
            
            # Calculate verification scores
            # NOTE: llm_extracted_text (precise text span) is shorter than reference_text (at least a whole chunk)
            rouge_score = self._calculate_rouge_l_score(llm_extracted_text, qa_pair.chunk_content)
            
            # Determine if verification passed (Rouge-L only)
            is_verified = rouge_score >= self.rouge_threshold
            
            verification_time = (datetime.now() - start_time).total_seconds()
            
            return VerificationResult(
                qa_pair=qa_pair,
                llm_extracted_text=llm_extracted_text,
                verification_score=rouge_score,
                is_verified=is_verified,
                verification_time=verification_time,
                context_used=context[:1000] + "..." if len(context) > 1000 else context,  # Truncate for logging
                reference_used="chunk_content",  # We compared against the reference text chunk
                document_metadata=doc_metadata
            )
            
        except Exception as e:
            verification_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Error verifying Q&A pair: {str(e)}"
            logger.error(error_msg)
            
            return VerificationResult(
                qa_pair=qa_pair,
                llm_extracted_text="",
                verification_score=0.0,
                is_verified=False,
                verification_time=verification_time,
                context_used="",
                reference_used="chunk_content",
                document_metadata={},
                error=error_msg
            )

    async def verify_qa_pairs(self, qa_pairs: List[QuestionAnswerPair], step5_data: Dict[str, Any]) -> BatchVerificationResult:
        """Verify a batch of Q&A pairs using self-verification."""
        start_time = datetime.now()
        logger.info(f"🔍 Starting self-verification for {len(qa_pairs)} Q&A pairs")
        
        all_results = []
        verified_pairs = []
        
        # Process in batches to manage memory and API limits
        for i in range(0, len(qa_pairs), self.batch_size):
            batch = qa_pairs[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = math.ceil(len(qa_pairs) / self.batch_size)
            
            logger.info(f"Processing verification batch {batch_num}/{total_batches} with {len(batch)} Q&A pairs")
            
            # Create parallel tasks for this batch
            batch_tasks = [
                asyncio.create_task(self._verify_single_qa_pair(qa_pair, step5_data))
                for qa_pair in batch
            ]
            
            try:
                # Execute all tasks in parallel for this batch
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Process results
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"Batch verification error: {str(result)}")
                    elif isinstance(result, VerificationResult):
                        all_results.append(result)
                        
                        if result.is_verified:
                            verified_pairs.append(result.qa_pair)
                            logger.debug(f"✅ Verified Q&A pair (Rouge-L: {result.verification_score:.3f})")
                        else:
                            logger.debug(f"❌ Failed Q&A pair verification (Rouge-L: {result.verification_score:.3f})")
                    else:
                        logger.error(f"Unexpected result type: {type(result)}")
                
                logger.info(f"✅ Batch {batch_num} completed - {len(batch)} pairs processed")
                
            except Exception as e:
                logger.error(f"❌ Batch {batch_num} failed entirely: {str(e)}")
            
            # Delay between batches to avoid rate limits
            if i + self.batch_size < len(qa_pairs):
                logger.info(f"⏳ Waiting {self.delay_between_batches}s before next verification batch...")
                await asyncio.sleep(self.delay_between_batches)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Calculate statistics
        total_processed = len(qa_pairs)
        total_verified = len(verified_pairs)
        total_failed = total_processed - total_verified
        verification_rate = (total_verified / total_processed) * 100 if total_processed > 0 else 0
        
        # Compile metadata
        rouge_scores = [r.verification_score for r in all_results if r.verification_score > 0]
        
        metadata = {
            "model": self.model,
            "rouge_threshold": self.rouge_threshold,
            "context_expansion_chunks": self.context_expansion_chunks,
            "max_context_tokens": self.max_context_tokens,
            "average_rouge_score": sum(rouge_scores) / len(rouge_scores) if rouge_scores else 0,
            "verification_rate_percent": verification_rate,
            "processing_time_seconds": processing_time,
            "verified_at": end_time.isoformat()
        }
        
        result = BatchVerificationResult(
            verified_pairs=verified_pairs,
            verification_results=all_results,
            total_processed=total_processed,
            total_verified=total_verified,
            total_failed=total_failed,
            verification_rate=verification_rate,
            processing_time=processing_time,
            metadata=metadata
        )
        
        logger.info(f"✅ Self-verification completed: {total_verified}/{total_processed} pairs verified ({verification_rate:.1f}%)")
        logger.info(f"📊 Average Rouge-L score: {metadata['average_rouge_score']:.3f}")
        logger.info(f"⏱️  Total processing time: {processing_time:.2f} seconds")
        
        return result

    def save_verification_results(self, results: BatchVerificationResult, output_path: str):
        """Save verification results to JSON file."""
        try:
            # Prepare data for serialization
            output_data = {
                "verification_summary": {
                    "total_processed": results.total_processed,
                    "total_verified": results.total_verified,
                    "total_failed": results.total_failed,
                    "verification_rate": results.verification_rate,
                    "processing_time": results.processing_time
                },
                "metadata": results.metadata,
                "verified_pairs": [
                    {
                        "question": qa_pair.question,
                        "chunk_content": qa_pair.chunk_content,  # The verified Q&A pair: question + reference text
                        **doc_metadata  # Include document metadata (database_id, doc_id, author, status, etc.)
                    }
                    for vr in results.verification_results
                    if vr.is_verified
                    for qa_pair, doc_metadata in [(vr.qa_pair, vr.document_metadata)]
                ],
                "verification_details": [
                    {
                        "question": vr.qa_pair.question,
                        "chunk_content": vr.qa_pair.chunk_content,  # Correct context
                        "extracted_text": vr.llm_extracted_text,  # Text extracted by verification LLM
                        "rouge_l_score": vr.verification_score,
                        "failed": not vr.is_verified  # True if Rouge-L score < threshold
                    }
                    for vr in results.verification_results
                ]
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📁 Verification results saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Error saving verification results: {e}")