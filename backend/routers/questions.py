"""
Question bank management routes.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.models.schemas import Question, GenerateQuestionRequest, DifficultyLevel
from backend.services.question_service import question_service

router = APIRouter(prefix="/questions", tags=["Questions"])
logger = logging.getLogger(__name__)


# ─── List Questions ───────────────────────────────────────────────────────────

@router.get("/", response_model=list)
def list_questions(
    competency: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
):
    """List all questions with optional filters."""
    if not question_service.questions:
        question_service.load_questions()

    questions = question_service.filter_questions(competency=competency, difficulty=difficulty)
    return questions


# ─── Get Question ─────────────────────────────────────────────────────────────

@router.get("/{question_id}")
def get_question(question_id: str):
    """Get a single question by ID."""
    if not question_service.questions:
        question_service.load_questions()

    q = question_service.get_question_by_id(question_id)
    if not q:
        raise HTTPException(status_code=404, detail=f"Question {question_id} not found.")
    return q


# ─── Competencies ─────────────────────────────────────────────────────────────

@router.get("/meta/competencies")
def get_competencies():
    """Return all available competency categories."""
    if not question_service.questions:
        question_service.load_questions()
    return {"competencies": question_service.get_competencies()}


# ─── Generate Dynamic Question ────────────────────────────────────────────────

@router.post("/generate")
def generate_question(request: GenerateQuestionRequest):
    """Generate a new behavioral question using the LLM."""
    if not question_service.questions:
        question_service.load_questions()

    question = question_service.generate_dynamic_question(
        competency=request.competency,
        difficulty=request.difficulty.value,
        job_role=request.job_role,
    )
    return question


# ─── Search Questions ─────────────────────────────────────────────────────────

@router.get("/search/similar")
def search_similar(query: str = Query(..., min_length=3), k: int = Query(5, ge=1, le=20)):
    """Find questions semantically similar to a query string."""
    from backend.services.vector_store import vector_store_service

    if not vector_store_service.questions:
        if not question_service.questions:
            question_service.load_questions()
        vector_store_service.build_index(question_service.questions)

    results = vector_store_service.search_similar(query, k=k)
    return results
