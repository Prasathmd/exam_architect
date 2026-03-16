"""SQLAlchemy ORM models for jobs and questions."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def gen_uuid() -> str:
    return str(uuid4())


class JobModel(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default="uploaded")
    file_name: Mapped[str] = mapped_column(String(512), default="")
    file_path: Mapped[str] = mapped_column(String(1024), default="")
    subject: Mapped[str] = mapped_column(String(64), default="")
    class_name: Mapped[str] = mapped_column(String(32), default="")
    term: Mapped[str] = mapped_column(String(32), default="")
    uploaded_by: Mapped[str] = mapped_column(String(128), default="")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunks_count: Mapped[int] = mapped_column(Integer, default=0)
    questions_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class QuestionModel(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    job_id: Mapped[str] = mapped_column(String(32), ForeignKey("jobs.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
