"""
Session management routes — start, status, next question, complete.
"""
import json
import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.models.database import get_db, DBInterviewSession
from backend.models.schemas import (
    SessionStartRequest,
    InterviewSession,
    SessionStatusResponse,
    NextQuestionResponse,
    SessionStatus,
    Question,
)
from backend.services.question_service import question_service
from backend.config import settings

router = APIRouter(prefix="/sessions", tags=["Sessions"])
logger = logging.getLogger(__name__)


# ─── Start Session ────────────────────────────────────────────────────────────

@router.post("/start", response_model=InterviewSession)
def start_session(request: SessionStartRequest, db: Session = Depends(get_db)):
    """Create a new interview session and select questions."""
    # Load questions if not already loaded
    if not question_service.questions:
        question_service.load_questions()

    selected = question_service.get_random_session_questions(
        job_role=request.job_role,
        count=request.question_count,
    )

    if not selected:
        raise HTTPException(status_code=500, detail="No questions available in the question bank.")

    session_id = str(uuid.uuid4())
    question_ids = [q["id"] for q in selected]

    db_session = DBInterviewSession(
        id=session_id,
        user_name=request.user_name,
        job_role=request.job_role,
        question_count=len(selected),
        question_ids=json.dumps(question_ids),
        status="active",
        start_time=datetime.now(timezone.utc),
        current_question_index=0,
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    return InterviewSession(
        id=db_session.id,
        user_name=db_session.user_name,
        job_role=db_session.job_role,
        start_time=db_session.start_time,
        status=SessionStatus.active,
        question_count=db_session.question_count,
        current_question_index=0,
        question_ids=question_ids,
    )


# ─── Get Session ──────────────────────────────────────────────────────────────

@router.get("/{session_id}", response_model=InterviewSession)
def get_session(session_id: str, db: Session = Depends(get_db)):
    """Retrieve session details."""
    db_session = db.query(DBInterviewSession).filter(DBInterviewSession.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found.")

    return InterviewSession(
        id=db_session.id,
        user_name=db_session.user_name,
        job_role=db_session.job_role,
        start_time=db_session.start_time,
        end_time=db_session.end_time,
        status=SessionStatus(db_session.status),
        question_count=db_session.question_count,
        current_question_index=db_session.current_question_index,
        question_ids=json.loads(db_session.question_ids or "[]"),
    )


# ─── Session Status ───────────────────────────────────────────────────────────

@router.get("/{session_id}/status", response_model=SessionStatusResponse)
def get_session_status(session_id: str, db: Session = Depends(get_db)):
    """Get current progress of a session."""
    db_session = db.query(DBInterviewSession).filter(DBInterviewSession.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found.")

    elapsed = None
    if db_session.start_time:
        # SQLite stores naive datetimes — compare without timezone
        elapsed = (datetime.now() - db_session.start_time).total_seconds()

    return SessionStatusResponse(
        session_id=session_id,
        status=SessionStatus(db_session.status),
        current_question_index=db_session.current_question_index,
        total_questions=db_session.question_count,
        time_elapsed=elapsed,
    )


# ─── Next Question ────────────────────────────────────────────────────────────

@router.get("/{session_id}/next-question", response_model=NextQuestionResponse)
def get_next_question(session_id: str, db: Session = Depends(get_db)):
    """Return the next question for the session."""
    db_session = db.query(DBInterviewSession).filter(DBInterviewSession.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found.")

    if db_session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active.")

    question_ids: List[str] = json.loads(db_session.question_ids or "[]")
    idx = db_session.current_question_index

    if idx >= len(question_ids):
        raise HTTPException(status_code=400, detail="All questions have been answered. Complete the session.")

    q_id = question_ids[idx]
    q_data = question_service.get_question_by_id(q_id)

    if not q_data:
        raise HTTPException(status_code=404, detail=f"Question {q_id} not found.")

    question = Question(
        id=q_data["id"],
        text=q_data["text"],
        category=q_data["category"],
        difficulty=q_data["difficulty"],
        competency=q_data["competency"],
        follow_ups=q_data.get("follow_up_questions", []),
        star_hints=q_data.get("star_hints", {}),
        sample_answer_keywords=q_data.get("sample_answer_keywords", []),
    )

    return NextQuestionResponse(
        question=question,
        question_number=idx + 1,
        total_questions=db_session.question_count,
        time_limit=settings.DEFAULT_ANSWER_TIME_LIMIT,
        session_id=session_id,
    )


# ─── Complete Session ─────────────────────────────────────────────────────────

@router.post("/{session_id}/complete")
def complete_session(session_id: str, db: Session = Depends(get_db)):
    """Mark a session as completed."""
    db_session = db.query(DBInterviewSession).filter(DBInterviewSession.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found.")

    db_session.status = "completed"
    db_session.end_time = datetime.now(timezone.utc)
    db.commit()

    return {"message": "Session completed.", "session_id": session_id}


# ─── Abandon Session ──────────────────────────────────────────────────────────

@router.post("/{session_id}/abandon")
def abandon_session(session_id: str, db: Session = Depends(get_db)):
    """Mark a session as abandoned."""
    db_session = db.query(DBInterviewSession).filter(DBInterviewSession.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found.")

    db_session.status = "abandoned"
    db_session.end_time = datetime.now(timezone.utc)
    db.commit()

    return {"message": "Session abandoned.", "session_id": session_id}
