"""
Retrieval Agent: Searches relevant chunks using vector similarity.

Pipeline step: Query → Gemini Query Embedding → **Chroma Search** → Results
"""
from __future__ import annotations

from app.models.document_chunk import DocumentChunk, RetrievalResult
from app.services.rag_pipeline import RAGPipeline


class RetrievalAgent:
    """
    Retrieves relevant chunks for queries or MCQ generation.
    
    This agent handles the retrieval step of the RAG pipeline:
    - Embeds the query using Gemini
    - Searches ChromaDB for similar chunks
    - Returns ranked results
    """

    def __init__(self) -> None:
        self._pipeline = RAGPipeline()

    async def search(
        self,
        job_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        """
        Return top_k relevant chunks for query.
        
        Pipeline: Query → Gemini Embedding → ChromaDB Search → Results
        """
        return await self._pipeline.retrieve(job_id, query, top_k=top_k)

    async def get_chunks_for_mcq(
        self,
        job_id: str,
        topic_hint: str = "",
        top_k: int = 5,
    ) -> list[DocumentChunk]:
        """
        Get chunks suitable for generating MCQs.
        
        If topic_hint is provided, retrieves topic-relevant chunks.
        Otherwise, returns diverse chunks from the document.
        """
        return await self._pipeline.retrieve_chunks_for_mcq(
            job_id=job_id,
            topic_hint=topic_hint,
            top_k=top_k,
        )
