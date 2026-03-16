"""Job status and upload response models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Pipeline job status."""

    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    READY = "ready"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class UploadResponse(BaseModel):
    """Response after document upload."""

    job_id: str
    status: str = "uploaded"
    message: str = "Document uploaded successfully"
    subject: str = ""
    class_name: str = ""
    term: str = ""
    uploaded_by: str = ""
    uploaded_at: datetime | None = None


class ProcessResponse(BaseModel):
    """Response after triggering document processing."""

    job_id: str
    status: str = "processing"
    message: str = "Processing started"


class JobStatusResponse(BaseModel):
    """Full job status for API."""

    job_id: str
    status: JobStatus
    file_name: str = ""
    subject: str = ""
    class_name: str = ""
    term: str = ""
    uploaded_by: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    error: str | None = None
    chunks_count: int = 0
    questions_count: int = 0
