"""
Embedding Agent: Creates vector embeddings from chunks using Gemini.

Pipeline step: Chunk → **Gemini Embedding** → Chroma Vector DB
"""
from __future__ import annotations

from app.models.document_chunk import DocumentChunk
from app.services.rag_pipeline import RAGPipeline


class EmbeddingAgent:
    """
    Generates Gemini embeddings and stores them in ChromaDB.
    
    This agent handles the embedding step of the RAG pipeline:
    - Takes document chunks as input
    - Generates embeddings using Gemini
    - Stores embeddings in ChromaDB for later retrieval
    """

    def __init__(self) -> None:
        self._pipeline = RAGPipeline()

    async def embed_and_store(
        self,
        job_id: str,
        chunks: list[DocumentChunk],
    ) -> int:
        """
        Compute Gemini embeddings for chunks and persist to vector store.
        
        Pipeline: Chunks → Gemini Embedding → ChromaDB
        
        Returns: number of chunks embedded and stored
        """
        return await self._pipeline.embed_and_store_chunks(job_id, chunks)
