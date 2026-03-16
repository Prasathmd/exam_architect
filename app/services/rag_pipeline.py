"""
RAG Pipeline: Retrieval-Augmented Generation for MCQ creation.

Complete Pipeline:
  Document → Chunk → Gemini Embedding → Chroma Vector DB → RAG Retrieval → Gemini Question Generator
"""
from __future__ import annotations

from app.config.llm_config import MCQ_SYSTEM_PROMPT, get_mcq_prompt_template
from app.models.document_chunk import DocumentChunk, RetrievalResult
from app.services.ai_client import AIClient
from app.services.vector_store import VectorStore


class RAGPipeline:
    """
    Orchestrates the complete RAG pipeline:
    
    1. Embed query using Gemini
    2. Retrieve relevant chunks from ChromaDB
    3. Generate MCQs using Gemini with retrieved context
    """

    def __init__(self) -> None:
        self._ai_client = AIClient()
        self._vector_store = VectorStore()

    # ==================== RETRIEVAL ====================

    async def retrieve(
        self,
        job_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        """
        Retrieve relevant chunks for a query.
        
        Pipeline: Query → Gemini Query Embedding → Chroma Search → Results
        """
        if not query.strip():
            return []
        
        # Step 1: Embed the query using Gemini
        query_embedding = await self._ai_client.embed_query(query)
        
        # Step 2: Search ChromaDB for similar chunks
        results = await self._vector_store.search_similar(
            job_id=job_id,
            query_embedding=query_embedding,
            top_k=top_k,
        )
        
        return results

    async def retrieve_chunks_for_mcq(
        self,
        job_id: str,
        topic_hint: str = "",
        top_k: int = 5,
    ) -> list[DocumentChunk]:
        """
        Retrieve chunks suitable for MCQ generation.
        
        If topic_hint is provided, searches for relevant chunks.
        Otherwise, returns diverse chunks from the document.
        """
        if topic_hint.strip():
            # Search for topic-relevant chunks
            results = await self.retrieve(job_id, topic_hint, top_k=top_k)
            return [r.chunk for r in results]
        else:
            # Get chunks directly (for general MCQ generation)
            all_chunks = self._vector_store.get_all_chunks(job_id)
            # Return evenly distributed chunks
            if len(all_chunks) <= top_k:
                return all_chunks
            step = len(all_chunks) // top_k
            return [all_chunks[i * step] for i in range(top_k)]

    # ==================== GENERATION ====================

    async def generate_mcq_from_text(
        self,
        text_content: str,
        num_questions: int = 5,
    ) -> str:
        """
        Generate MCQs directly from text content.
        
        Pipeline: Text → **Gemini Question Generator** → MCQ Output
        
        Returns: Formatted MCQ text (not JSON)
        """
        template = get_mcq_prompt_template()
        user_prompt = template.replace("{{content}}", text_content)
        user_prompt = user_prompt.replace("{{num_questions}}", str(num_questions))
        
        mcq_text = await self._ai_client.chat_completion(
            system_prompt=MCQ_SYSTEM_PROMPT,
            user_content=user_prompt,
            max_tokens=4096,
        )
        
        return mcq_text

    async def generate_mcq_from_chunks(
        self,
        chunks: list[DocumentChunk],
        num_questions_per_chunk: int = 3,
    ) -> str:
        """
        Generate MCQs from multiple chunks.
        
        Pipeline: Retrieved Chunks → **Gemini Question Generator** → MCQ Output
        """
        if not chunks:
            return ""
        
        all_mcqs: list[str] = []
        
        for chunk in chunks:
            mcq_text = await self.generate_mcq_from_text(
                text_content=chunk.content,
                num_questions=num_questions_per_chunk,
            )
            if mcq_text.strip():
                all_mcqs.append(mcq_text)
        
        return "\n\n".join(all_mcqs)

    # ==================== FULL RAG FLOW ====================

    async def generate_mcqs_for_job(
        self,
        job_id: str,
        topic_hint: str = "",
        num_chunks: int = 3,
        questions_per_chunk: int = 3,
    ) -> str:
        """
        Complete RAG pipeline for MCQ generation.
        
        Full Pipeline:
          1. Retrieve relevant chunks from ChromaDB
          2. Generate MCQs using Gemini
          3. Return formatted output
        
        Returns: Formatted MCQ text for all chunks
        """
        # Step 1: RAG Retrieval
        chunks = await self.retrieve_chunks_for_mcq(
            job_id=job_id,
            topic_hint=topic_hint,
            top_k=num_chunks,
        )
        
        if not chunks:
            return "No content found for this document."
        
        # Step 2: Gemini Question Generator
        mcq_text = await self.generate_mcq_from_chunks(
            chunks=chunks,
            num_questions_per_chunk=questions_per_chunk,
        )
        
        return mcq_text if mcq_text else "No questions could be generated."

    # ==================== EMBEDDING PIPELINE ====================

    async def embed_and_store_chunks(
        self,
        job_id: str,
        chunks: list[DocumentChunk],
    ) -> int:
        """
        Embed chunks and store in vector database.
        
        Pipeline: Chunks → **Gemini Embedding** → **Chroma Vector DB**
        
        Returns: number of chunks stored
        """
        if not chunks:
            return 0
        
        # Step 1: Generate embeddings using Gemini
        texts = [chunk.content for chunk in chunks]
        embeddings = await self._ai_client.embed_texts(texts)
        
        # Step 2: Store in ChromaDB
        count = await self._vector_store.add_chunks_with_embeddings(
            job_id=job_id,
            chunks=chunks,
            embeddings=embeddings,
        )
        
        return count
