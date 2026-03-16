"""Exam-Architect AI — FastAPI application entry point."""
from contextlib import asynccontextmanager
from pathlib import Path
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.upload_api import router as upload_router
from app.api.question_api import router as question_router
from app.db.session import init_db
from app.config.settings import get_settings, clear_settings_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress noisy third-party logs
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)
logging.getLogger("chromadb.telemetry").setLevel(logging.WARNING)

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Clear settings cache on startup to pick up .env changes
    clear_settings_cache()
    settings = get_settings()
    
    logger.info("=" * 50)
    logger.info("Exam-Architect AI - RAG Pipeline Configuration")
    logger.info("=" * 50)
    logger.info("Pipeline: Document → Chunk → Gemini Embedding → Chroma → RAG → Gemini MCQ")
    logger.info(f"  Embedding Model: {settings.gemini_embedding_model}")
    logger.info(f"  Chat Model: {settings.gemini_chat_model}")
    logger.info(f"  API Key configured: {'Yes' if settings.get_gemini_api_key() else 'No'}")
    logger.info(f"  Chroma persist dir: {settings.chroma_persist_dir}")
    logger.info("=" * 50)
    
    await init_db()
    yield


app = FastAPI(
    title="Exam-Architect AI",
    description="Convert educational documents into bilingual MCQ questions for TNPSC, UPSC, SSC, Banking exams.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(upload_router)
app.include_router(question_router)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root():
    """Serve the user-friendly UI."""
    index_path = STATIC_DIR / "index.html"
    if index_path.is_file():
        return FileResponse(index_path)
    return {
        "service": "Exam-Architect AI",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Exam-Architect AI"}
