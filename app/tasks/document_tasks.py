"""Celery tasks for document processing and MCQ generation."""
from pathlib import Path

from celery_app import celery_app
from app.agents.chunking_agent import ChunkingAgent
from app.agents.embedding_agent import EmbeddingAgent
from app.agents.mcq_generator_agent import MCQGeneratorAgent
from app.agents.validation_agent import ValidationAgent
from app.services.rag_pipeline import RAGPipeline


@celery_app.task(bind=True, name="app.tasks.document_tasks.process_document")
def process_document_task(self, job_id: str, file_path: str) -> dict:
    """Chunk document and store embeddings. Run in Celery worker."""
    import asyncio
    path = Path(file_path)
    if not path.exists():
        return {"job_id": job_id, "status": "failed", "error": "File not found"}
    try:
        chunk_agent = ChunkingAgent()
        embed_agent = EmbeddingAgent()

        async def _run():
            chunks = await chunk_agent.chunk_file(path, job_id)
            await embed_agent.embed_and_store(job_id, chunks)
            return len(chunks)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            n = loop.run_until_complete(_run())
            return {"job_id": job_id, "status": "ready", "chunks_count": n}
        finally:
            loop.close()
    except Exception as e:
        return {"job_id": job_id, "status": "failed", "error": str(e)}


@celery_app.task(bind=True, name="app.tasks.document_tasks.generate_mcqs_for_job")
def generate_mcqs_for_job_task(self, job_id: str, top_k: int = 3) -> dict:
    """Retrieve chunks, generate MCQs, return formatted text. Run in Celery worker."""
    import asyncio
    pipeline = RAGPipeline()
    generator = MCQGeneratorAgent()
    validator = ValidationAgent()

    async def _run():
        chunks = await pipeline.retrieve_for_mcq(job_id, "", top_k=top_k)
        if not chunks:
            return ""
        parts = []
        for c in chunks:
            raw = await generator.generate_from_text(c.content, num_questions=3)
            parts.append(validator.process(raw))
        return "\n\n".join(parts)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        text = loop.run_until_complete(_run())
        return {"job_id": job_id, "questions_text": text, "num_generated": text.count("Answer:")}
    finally:
        loop.close()
