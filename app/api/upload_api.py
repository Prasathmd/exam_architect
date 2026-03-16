"""
Upload and Process Document APIs.

Pipeline:
  1. Upload: Document → Save to disk
  2. Process: Document → Chunk → Gemini Embedding → Chroma Vector DB
"""
from __future__ import annotations

import logging
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.upload_agent import UploadAgent
from app.agents.chunking_agent import ChunkingAgent
from app.agents.embedding_agent import EmbeddingAgent
from app.db.session import get_db
from app.db.repositories import JobRepository
from app.models.job_status import UploadResponse, ProcessResponse, JobStatusResponse, JobStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["upload"])

ALLOWED_SUBJECTS = {
    "Tamil",
    "English",
    "Maths",
    "Social",
    "Science",
    "Geography",
    "Biology",
    "Zoology",
    "Botany",
    "Psychology",
    "Other",
}
ALLOWED_CLASS_NAMES = {
    "6th",
    "7th",
    "8th",
    "9th",
    "10th",
    "11th",
    "12th",
    "UG",
    "PG",
    "B.Ed",
    "General",
}
ALLOWED_TERMS = {"Term-I", "Term-II", "Term-III"}


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    subject: str = Form(...),
    class_name: str = Form(...),
    term: str = Form(...),
    uploaded_by: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    """Accept document upload; create job and save file."""
    if subject not in ALLOWED_SUBJECTS:
        raise HTTPException(status_code=400, detail="Invalid subject")
    if class_name not in ALLOWED_CLASS_NAMES:
        raise HTTPException(status_code=400, detail="Invalid class name")
    if term not in ALLOWED_TERMS:
        raise HTTPException(status_code=400, detail="Invalid term")
    if not uploaded_by.strip():
        raise HTTPException(status_code=400, detail="Uploaded by is required")

    agent = UploadAgent()
    ok, err = agent.validate_upload(file)
    if not ok:
        raise HTTPException(status_code=400, detail=err)
    job_id = agent.create_job_id()
    try:
        path = await agent.save_upload(job_id, file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    repo = JobRepository(db)
    job = await repo.create(
        job_id,
        file_name=file.filename or "document",
        file_path=str(path),
        subject=subject,
        class_name=class_name,
        term=term,
        uploaded_by=uploaded_by.strip(),
    )
    await db.commit()
    response = agent.build_upload_response(
        job_id,
        subject=subject,
        class_name=class_name,
        term=term,
        uploaded_by=uploaded_by.strip(),
    )
    response.uploaded_at = job.created_at or datetime.now(timezone.utc)
    return response


@router.post("/process/{job_id}", response_model=ProcessResponse)
async def process_document(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProcessResponse:
    """Trigger document processing: chunk, embed, store. Runs synchronously for simplicity."""
    job_repo = JobRepository(db)
    job = await job_repo.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    path = Path(job.file_path)
    if not path.exists():
        await job_repo.update_status(job_id, JobStatus.FAILED.value, error="File not found")
        await db.commit()
        raise HTTPException(status_code=404, detail="Uploaded file not found")
    await job_repo.update_status(job_id, JobStatus.CHUNKING.value)
    chunk_agent = ChunkingAgent()
    embed_agent = EmbeddingAgent()
    try:
        # Step 1: Document → Chunk
        logger.info(f"[{job_id}] Chunking document...")
        chunks = await chunk_agent.chunk_file(path, job_id)
        logger.info(f"[{job_id}] Created {len(chunks)} chunks")
        
        await job_repo.update_status(job_id, JobStatus.EMBEDDING.value, chunks_count=len(chunks))
        
        # Step 2: Chunk → Gemini Embedding → Chroma Vector DB
        logger.info(f"[{job_id}] Generating Gemini embeddings...")
        stored_count = await embed_agent.embed_and_store(job_id, chunks)
        logger.info(f"[{job_id}] Stored {stored_count} embeddings in ChromaDB")
        
        await job_repo.update_status(job_id, JobStatus.READY.value, chunks_count=stored_count)
        await db.commit()
        logger.info(f"[{job_id}] Processing complete!")
    except Exception as e:
        err_msg = str(e)
        await job_repo.update_status(job_id, JobStatus.FAILED.value, error=err_msg)
        await db.commit()
        if "429" in err_msg or "quota" in err_msg.lower() or "insufficient_quota" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
            raise HTTPException(
                status_code=503,
                detail=(
                    "AI service quota exceeded. For Gemini: enable billing at https://console.cloud.google.com/billing for your project, "
                    "or wait a few minutes and retry. For OpenAI: check https://platform.openai.com/account/billing"
                ),
            )
        if "api_key" in err_msg.lower() or "invalid" in err_msg.lower() or "401" in err_msg or "key missing" in err_msg.lower():
            raise HTTPException(
                status_code=503,
                detail="AI API key missing or invalid. For Gemini: set GOOGLE_API_KEY=your_key or GEMINI_API_KEY=your_key in .env (get key from aistudio.google.com/app/api-keys). Restart the app after editing .env.",
            )
        raise HTTPException(status_code=500, detail=err_msg)
    return ProcessResponse(job_id=job_id, status=JobStatus.READY.value)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    """Return current job status and counts."""
    repo = JobRepository(db)
    job = await repo.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(
        job_id=job.id,
        status=JobStatus(job.status) if job.status in [s.value for s in JobStatus] else JobStatus.UPLOADED,
        file_name=job.file_name,
        subject=job.subject,
        class_name=job.class_name,
        term=job.term,
        uploaded_by=job.uploaded_by,
        created_at=job.created_at,
        updated_at=job.updated_at,
        error=job.error,
        chunks_count=job.chunks_count,
        questions_count=job.questions_count,
    )
