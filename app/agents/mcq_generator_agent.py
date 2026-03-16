"""
MCQ Generator Agent: Uses Gemini to generate bilingual exam questions.

Pipeline step: Retrieved Chunks → **Gemini Question Generator** → MCQ Output
"""
from __future__ import annotations

from app.services.rag_pipeline import RAGPipeline


class MCQGeneratorAgent:
    """
    Generates bilingual exam-format MCQs using Gemini.
    
    This agent handles the generation step of the RAG pipeline:
    - Takes text content or retrieved chunks
    - Uses Gemini to generate MCQs in exam format
    - Outputs bilingual (English + Tamil) questions
    """

    def __init__(self) -> None:
        self._pipeline = RAGPipeline()

    async def generate_from_text(
        self,
        text_chunk: str,
        num_questions: int = 5,
    ) -> str:
        """
        Generate exam-format MCQ text from content.
        
        Pipeline: Text → Gemini Question Generator → MCQ Output
        
        Returns: Formatted MCQ text (English + Tamil, no JSON)
        """
        return await self._pipeline.generate_mcq_from_text(
            text_content=text_chunk,
            num_questions=num_questions,
        )

    async def generate_from_job(
        self,
        job_id: str,
        topic_hint: str = "",
        num_chunks: int = 3,
        questions_per_chunk: int = 3,
    ) -> str:
        """
        Generate MCQs from a processed document using RAG.
        
        Full Pipeline:
          1. Retrieve relevant chunks from ChromaDB
          2. Generate MCQs using Gemini
          3. Return formatted output
        
        Returns: Formatted MCQ text for all chunks
        """
        return await self._pipeline.generate_mcqs_for_job(
            job_id=job_id,
            topic_hint=topic_hint,
            num_chunks=num_chunks,
            questions_per_chunk=questions_per_chunk,
        )
