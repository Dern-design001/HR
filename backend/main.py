"""
HR Interview Simulator — FastAPI Application Entry Point
PRJ-026 | Week 1-3 Complete Implementation
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.models.database import create_tables
from backend.services.question_service import question_service
from backend.services.vector_store import vector_store_service
from backend.routers import sessions, answers, reports, history, questions

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    logger.info("Starting HR Interview Simulator...")

    # Create DB tables
    create_tables()
    logger.info("Database tables ready.")

    # Load question bank
    loaded = question_service.load_questions()
    logger.info(f"Loaded {len(loaded)} questions.")

    # Build vector index
    if loaded:
        vector_store_service.build_index(loaded)
        logger.info("Vector index built.")

    yield

    logger.info("Shutting down HR Interview Simulator.")


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description=(
        "Behavioral interview practice bot with rubric-based scoring, "
        "STAR method evaluation, and AI-powered better-answer suggestions."
    ),
    lifespan=lifespan,
)

# CORS — allow Streamlit and the HTML frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(sessions.router, prefix="/api/v1")
app.include_router(answers.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1")
app.include_router(questions.router, prefix="/api/v1")


# ─── Root ─────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Root"])
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health", tags=["Root"])
def health():
    return {
        "status": "healthy",
        "questions_loaded": len(question_service.questions),
        "vector_index_ready": vector_store_service.embeddings is not None,
    }
