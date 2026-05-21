"""
Feedback report generation routes.
"""
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.models.database import get_db, DBInterviewSession, DBAnswer
from backend.models.schemas import FeedbackReport, AnswerScore, ScoreRubric, CompetencyScore
from backend.services.question_service import question_service

router = APIRouter(prefix="/reports", tags=["Reports"])
logger = logging.getLogger(__name__)


# ─── Generate Report ──────────────────────────────────────────────────────────

@router.get("/{session_id}", response_model=FeedbackReport)
def get_feedback_report(session_id: str, db: Session = Depends(get_db)):
    """Generate a full feedback report for a completed session."""
    db_session = db.query(DBInterviewSession).filter(DBInterviewSession.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found.")

    answers = db.query(DBAnswer).filter(DBAnswer.session_id == session_id).all()

    if not answers:
        raise HTTPException(status_code=404, detail="No answers found for this session.")

    # Calculate overall score
    scores = [a.score for a in answers if a.score is not None]
    overall_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    # Update session overall score
    db_session.overall_score = overall_score
    db.commit()

    # Duration
    duration_minutes = 0.0
    if db_session.start_time and db_session.end_time:
        duration_minutes = round(
            (db_session.end_time - db_session.start_time).total_seconds() / 60, 1
        )

    # Competency scores
    comp_map: Dict[str, List[float]] = {}
    for a in answers:
        comp = a.competency or "General"
        comp_map.setdefault(comp, []).append(a.score or 0.0)

    competency_scores = [
        CompetencyScore(
            competency=comp,
            score=round(sum(s) / len(s), 1),
            question_count=len(s),
        )
        for comp, s in comp_map.items()
    ]

    # Strengths and improvements
    strengths, improvements = _analyze_performance(answers)

    # Better answers list
    better_answers = []
    for a in answers:
        if a.better_answer:
            q = question_service.get_question_by_id(a.question_id)
            better_answers.append({
                "question_id": a.question_id,
                "question_text": q["text"] if q else a.question_id,
                "your_score": a.score,
                "better_answer": a.better_answer,
            })

    # Answer details
    answer_details = []
    for a in answers:
        q = question_service.get_question_by_id(a.question_id)
        rubric_data = json.loads(a.rubric_scores or "{}")
        rubric_list = rubric_data if isinstance(rubric_data, list) else []

        rubric_scores = [
            ScoreRubric(
                criteria=r.get("criteria", ""),
                weight=r.get("weight", 0),
                score=r.get("score", 0),
                max_score=r.get("max_score", 0),
                feedback=r.get("feedback", ""),
            )
            for r in rubric_list
        ]

        answer_details.append(
            AnswerScore(
                question_id=a.question_id,
                question_text=q["text"] if q else a.question_id,
                answer_text=a.answer_text,
                time_taken=a.time_taken,
                rubric_scores=rubric_scores,
                overall_score=a.score or 0.0,
                feedback=a.feedback,
                better_answer=a.better_answer,
            )
        )

    return FeedbackReport(
        session_id=session_id,
        user_name=db_session.user_name,
        job_role=db_session.job_role,
        overall_score=overall_score,
        total_questions=len(answers),
        duration_minutes=duration_minutes,
        strengths=strengths,
        improvements=improvements,
        better_answers=better_answers,
        competency_scores=competency_scores,
        answer_details=answer_details,
        generated_at=datetime.now(timezone.utc),
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _analyze_performance(answers: List[DBAnswer]):
    """Derive strengths and improvement areas from rubric scores."""
    criteria_totals: Dict[str, List[float]] = {}

    for a in answers:
        rubric_data = json.loads(a.rubric_scores or "[]")
        if isinstance(rubric_data, list):
            for r in rubric_data:
                crit = r.get("criteria", "")
                pct = (r.get("score", 0) / r.get("max_score", 1)) * 100
                criteria_totals.setdefault(crit, []).append(pct)

    avg_by_criteria = {
        crit: sum(vals) / len(vals)
        for crit, vals in criteria_totals.items()
    }

    strengths = [c for c, v in avg_by_criteria.items() if v >= 70]
    improvements = [c for c, v in avg_by_criteria.items() if v < 60]

    if not strengths:
        strengths = ["Keep practicing — you're building your interview skills!"]
    if not improvements:
        improvements = ["Continue refining your answers with more specific metrics."]

    return strengths, improvements
