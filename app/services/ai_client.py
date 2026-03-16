"""
Unified AI client for Gemini (embeddings + chat).

Pipeline:
  Document → Chunk → Gemini Embedding → Chroma Vector DB → RAG Retrieval → Gemini Question Generator
"""
from __future__ import annotations

import asyncio
import time
import logging
import warnings

from app.config.settings import get_settings

# Suppress deprecation warning
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*generativeai.*")

logger = logging.getLogger(__name__)


class AIClient:
    """
    Single interface for Gemini AI services with rate limiting.
    
    Free tier limits (15 requests per minute):
    - Enforces 4-second delay between requests
    - Retries with exponential backoff on 429 errors
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._genai = None
        self._configured = False
        self._last_request_time = 0
        self._request_interval = 4.0  # 15 RPM = 4 seconds between requests

    def _configure(self):
        """Configure Gemini API."""
        if self._configured:
            return
        
        try:
            import google.generativeai as genai
        except ImportError:
            raise RuntimeError("google-generativeai required: pip install google-generativeai")
        
        key = self._settings.get_gemini_api_key()
        if not key:
            raise ValueError(
                "Gemini API key missing. Set GOOGLE_API_KEY in .env "
                "(get key from https://aistudio.google.com/app/api-keys)"
            )
        
        genai.configure(api_key=key)
        self._genai = genai
        self._configured = True

    async def _rate_limit(self):
        """Enforce rate limiting for free tier."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._request_interval:
            wait = self._request_interval - elapsed
            logger.debug(f"Rate limit: waiting {wait:.1f}s")
            await asyncio.sleep(wait)
        self._last_request_time = time.time()

    async def _retry(self, func, max_retries: int = 5):
        """Execute with exponential backoff on rate limit errors."""
        for attempt in range(max_retries):
            try:
                await self._rate_limit()
                return await func()
            except Exception as e:
                err = str(e).lower()
                is_rate_error = any(x in err for x in ["429", "quota", "resource_exhausted"])
                
                if is_rate_error and attempt < max_retries - 1:
                    # Parse retry delay from error if available
                    wait = (2 ** attempt) * 15  # 15s, 30s, 60s, 120s
                    if "retry in" in err:
                        try:
                            import re
                            match = re.search(r"retry in (\d+)", err)
                            if match:
                                wait = int(match.group(1)) + 5
                        except:
                            pass
                    logger.warning(f"Rate limited, retry {attempt + 1}/{max_retries} in {wait}s")
                    await asyncio.sleep(wait)
                    continue
                raise
        raise RuntimeError("Max retries exceeded")

    # ==================== EMBEDDING ====================

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        embeddings = await self.embed_texts([text])
        return embeddings[0]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts with rate limiting.
        
        Pipeline: Chunk → **Gemini Embedding** → Chroma Vector DB
        """
        if not texts:
            return []
        
        self._configure()
        model = self._settings.gemini_embedding_model
        results: list[list[float]] = []
        
        for i, text in enumerate(texts):
            logger.info(f"Embedding chunk {i + 1}/{len(texts)}...")
            
            async def _embed(content=text):
                loop = asyncio.get_event_loop()
                def _sync():
                    result = self._genai.embed_content(
                        model=model,
                        content=content,
                        task_type="retrieval_document",
                    )
                    if isinstance(result, dict) and "embedding" in result:
                        return result["embedding"]
                    if hasattr(result, "embedding"):
                        return list(result.embedding)
                    raise ValueError("Unexpected embedding response")
                return await loop.run_in_executor(None, _sync)
            
            embedding = await self._retry(_embed)
            results.append(embedding)
        
        return results

    async def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a search query."""
        self._configure()
        model = self._settings.gemini_embedding_model
        
        async def _embed():
            loop = asyncio.get_event_loop()
            def _sync():
                result = self._genai.embed_content(
                    model=model,
                    content=query,
                    task_type="retrieval_query",
                )
                if isinstance(result, dict) and "embedding" in result:
                    return result["embedding"]
                return list(result.embedding)
            return await loop.run_in_executor(None, _sync)
        
        return await self._retry(_embed)

    # ==================== GENERATION ====================

    def _is_gemma_model(self, model_name: str) -> bool:
        """Check if model is Gemma (doesn't support system_instruction)."""
        return "gemma" in model_name.lower()

    async def generate_content(
        self,
        prompt: str,
        system_instruction: str | None = None,
        max_tokens: int = 4096,
    ) -> str:
        """
        Generate content using Gemini/Gemma.
        
        Note: Gemma models don't support system_instruction,
        so we embed it into the prompt instead.
        """
        self._configure()
        model_name = self._settings.gemini_chat_model
        is_gemma = self._is_gemma_model(model_name)
        
        # For Gemma: embed system instruction into prompt
        if is_gemma and system_instruction:
            full_prompt = f"""<start_of_turn>system
{system_instruction}
<end_of_turn>
<start_of_turn>user
{prompt}
<end_of_turn>
<start_of_turn>model
"""
            sys_inst = None
        else:
            full_prompt = prompt
            sys_inst = system_instruction
        
        async def _generate():
            loop = asyncio.get_event_loop()
            def _sync():
                if is_gemma:
                    model = self._genai.GenerativeModel(model_name)
                else:
                    model = self._genai.GenerativeModel(model_name, system_instruction=sys_inst)
                
                config = self._genai.types.GenerationConfig(max_output_tokens=max_tokens)
                response = model.generate_content(full_prompt, generation_config=config)
                return (response.text or "").strip() if response else ""
            return await loop.run_in_executor(None, _sync)
        
        logger.info(f"Generating with model: {model_name}")
        return await self._retry(_generate)

    async def chat_completion(
        self,
        system_prompt: str,
        user_content: str,
        max_tokens: int = 4096,
    ) -> str:
        """Chat completion for MCQ generation."""
        return await self.generate_content(
            prompt=user_content,
            system_instruction=system_prompt,
            max_tokens=max_tokens,
        )
