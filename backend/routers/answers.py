"""
Answer submission and scoring routes.
"""
import json
import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.models.database import get_db, DBAnswer, DBInterviewSession
from backend.models.schemas import AnswerSubmit, AnswerScore, ScoreRubric
from backend.services.scoring_service import scoring_service
from backend.services.question_service import question_service
from backend.services.llm_service import llm_service

router = APIRouter(prefix="/answers", tags=["Answers"])
logger = logging.getLogger(__name__)


# ─── Submit Answer ────────────────────────────────────────────────────────────

@router.post("/{session_id}/submit", response_model=AnswerScore)
def submit_answer(session_id: str, payload: AnswerSubmit, db: Session = Depends(get_db)):
    """Submit an answer, score it, and advance the session."""
    # Validate session
    db_session = db.query(DBInterviewSession).filter(DBInterviewSession.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if db_session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active.")

    # Validate question
    question = question_service.get_question_by_id(payload.question_id)
    if not question:
        raise HTTPException(status_code=404, detail=f"Question {payload.question_id} not found.")

    # Score the answer
    score_result = scoring_service.score_answer(
        question=question,
        answer_text=payload.answer_text,
        time_taken=payload.time_taken,
    )

    # Generate better answer suggestion
    try:
        better_answer = llm_service.generate_better_answer(
            question=question["text"],
            user_answer=payload.answer_text,
            rubric_scores=score_result["rubric_scores"],
        )
    except Exception as e:
        logger.warning(f"Better answer generation failed: {e}")
        better_answer = None

    # Persist answer
    answer_id = str(uuid.uuid4())
    db_answer = DBAnswer(
        id=answer_id,
        session_id=session_id,
        question_id=payload.question_id,
        answer_text=payload.answer_text,
        time_taken=payload.time_taken,
        score=score_result["overall_score"],
        rubric_scores=json.dumps(score_result["rubric_scores"]),
        feedback=score_result.get("feedback"),
        better_answer=better_answer,
        competency=question.get("competency"),
        created_at=datetime.now(timezone.utc),
    )
    db.add(db_answer)

    # Advance session question index
    db_session.current_question_index += 1
    db.commit()

    # Build response
    rubric_scores = [
        ScoreRubric(
            criteria=r["criteria"],
            weight=r["weight"],
            score=r["score"],
            max_score=r["max_score"],
            feedback=r["feedback"],
        )
        for r in score_result["rubric_scores"]
    ]

    return AnswerScore(
        question_id=payload.question_id,
        question_text=question["text"],
        answer_text=payload.answer_text,
        time_taken=payload.time_taken,
        rubric_scores=rubric_scores,
        overall_score=score_result["overall_score"],
        star_score=score_result.get("star_score"),
        specificity_score=score_result.get("specificity_score"),
        relevance_score=score_result.get("relevance_score"),
        clarity_score=score_result.get("clarity_score"),
        self_awareness_score=score_result.get("self_awareness_score"),
        feedback=score_result.get("feedback"),
        better_answer=better_answer,
    )


# ─── Get Answer ───────────────────────────────────────────────────────────────

@router.get("/{session_id}/all")
def get_session_answers(session_id: str, db: Session = Depends(get_db)):
    """Retrieve all answers for a session."""
    answers = db.query(DBAnswer).filter(DBAnswer.session_id == session_id).all()
    result = []
    for a in answers:
        result.append({
            "id": a.id,
            "question_id": a.question_id,
            "answer_text": a.answer_text,
            "time_taken": a.time_taken,
            "score": a.score,
            "feedback": a.feedback,
            "better_answer": a.better_answer,
            "competency": a.competency,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return result


# ─── Follow-up Question ───────────────────────────────────────────────────────

@router.get("/{session_id}/follow-up/{question_id}")
def get_follow_up(session_id: str, question_id: str, answer_text: str = "", db: Session = Depends(get_db)):
    """Get a follow-up question for a given answer."""
    follow_up = question_service.get_follow_up(question_id, answer_text)
    if not follow_up:
        raise HTTPException(status_code=404, detail="No follow-up available.")
    return {"follow_up_question": follow_up}
