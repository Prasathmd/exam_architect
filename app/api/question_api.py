"""
Question Generation and Export APIs.

Pipeline:
  3. Generate: RAG Retrieval → Gemini Question Generator → MCQ Output
  4. Export: MCQs → DOCX/PDF
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.mcq_generator_agent import MCQGeneratorAgent
from app.agents.validation_agent import ValidationAgent
from app.agents.export_agent import ExportAgent
from app.db.session import get_db
from app.db.repositories import JobRepository, QuestionRepository
from app.models.mcq_question import MCQGenerateRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["questions"])


def _ai_error_detail(e: Exception) -> str | None:
    """Return user-friendly message for AI API errors."""
    msg = str(e).lower()
    if "429" in str(e) or "quota" in msg or "insufficient_quota" in msg or "resource_exhausted" in msg:
        return (
            "AI service quota exceeded. Enable billing at https://console.cloud.google.com/billing "
            "or wait a few minutes and retry."
        )
    if "api_key" in msg or "401" in str(e) or "key missing" in msg:
        return "AI API key missing or invalid. Set GOOGLE_API_KEY in .env and restart the app."
    return None


@router.post("/generate")
async def generate_questions(body: MCQGenerateRequest) -> dict:
    """
    Generate MCQs from provided text chunk.
    
    Pipeline: Text → Gemini Question Generator → MCQ Output
    
    Returns: Plain exam-format text (not JSON/markdown)
    """
    generator = MCQGeneratorAgent()
    validator = ValidationAgent()
    
    try:
        logger.info("Generating MCQs from text...")
        raw = await generator.generate_from_text(body.text_chunk, body.num_questions)
    except Exception as e:
        detail = _ai_error_detail(e) or str(e)
        raise HTTPException(status_code=503, detail=detail)
    
    processed = validator.process(raw)
    num_generated = processed.count("Answer:")
    logger.info(f"Generated {num_generated} questions")
    
    return {
        "questions_text": processed,
        "num_generated": num_generated,
    }


@router.get("/questions/{job_id}")
async def get_questions(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retrieve all generated questions for a job (stored in DB)."""
    job_repo = JobRepository(db)
    job = await job_repo.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    q_repo = QuestionRepository(db)
    contents = await q_repo.get_all_text(job_id)
    full_text = "\n\n".join(contents) if contents else ""
    
    return {
        "job_id": job_id,
        "questions_text": full_text,
        "count": await q_repo.count(job_id),
    }


@router.post("/questions/{job_id}/generate")
async def generate_questions_for_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    RAG-based MCQ generation from processed document.
    
    Full Pipeline:
      1. RAG Retrieval: Query → Gemini Embedding → ChromaDB Search
      2. Gemini Question Generator: Chunks → MCQs
      3. Store results in database
    """
    job_repo = JobRepository(db)
    job = await job_repo.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.chunks_count == 0:
        raise HTTPException(
            status_code=400,
            detail="Job not processed yet. Call POST /api/process/{job_id} first."
        )
    
    generator = MCQGeneratorAgent()
    validator = ValidationAgent()
    
    try:
        logger.info(f"[{job_id}] Starting RAG-based MCQ generation...")
        
        # RAG Retrieval → Gemini Question Generator
        raw = await generator.generate_from_job(
            job_id=job_id,
            topic_hint="",
            num_chunks=3,
            questions_per_chunk=3,
        )
        
    except Exception as e:
        logger.error(f"[{job_id}] Generation failed: {e}")
        detail = _ai_error_detail(e) or str(e)
        raise HTTPException(status_code=503, detail=detail)
    
    # Validate and clean output
    full_text = validator.process(raw)
    num_generated = full_text.count("Answer:")
    logger.info(f"[{job_id}] Generated {num_generated} questions")
    
    # Store in database
    q_repo = QuestionRepository(db)
    await q_repo.add(job_id, full_text)
    count = await q_repo.count(job_id)
    await job_repo.update_status(job_id, "completed", questions_count=count)
    await db.commit()
    
    return {
        "job_id": job_id,
        "questions_text": full_text,
        "num_generated": num_generated,
    }


@router.get("/export/{job_id}")
async def export_questions(
    job_id: str,
    format: str = "docx",
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Export stored questions for job as DOCX or PDF."""
    if format not in ("docx", "pdf"):
        raise HTTPException(status_code=400, detail="format must be 'docx' or 'pdf'")
    
    q_repo = QuestionRepository(db)
    contents = await q_repo.get_all_text(job_id)
    if not contents:
        raise HTTPException(status_code=404, detail="No questions found for this job")
    
    full_text = "\n\n".join(contents)
    export_agent = ExportAgent()
    path = export_agent.export(full_text, job_id, format=format)
    
    if not path.exists():
        raise HTTPException(status_code=500, detail="Export failed")
    
    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if path.suffix.lower() == ".pdf":
        media_type = "application/pdf"
    return FileResponse(path, filename=path.name, media_type=media_type)
