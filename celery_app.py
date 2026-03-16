"""Celery application for async document processing and MCQ generation."""
from celery import Celery
from app.config.settings import get_settings

settings = get_settings()
celery_app = Celery(
    "exam_architect",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.document_tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)
