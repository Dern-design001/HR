"""
History dashboard routes — session list, stats, trends.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.models.database import get_db, DBInterviewSession, DBAnswer
from backend.models.schemas import SessionHistory, SessionSummary, AggregateStats, SessionStatus

router = APIRouter(prefix="/history", tags=["History"])
logger = logging.getLogger(__name__)


# ─── Session List ─────────────────────────────────────────────────────────────

@router.get("/sessions", response_model=SessionHistory)
def list_sessions(
    user_name: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """List all sessions with optional filtering by user name."""
    query = db.query(DBInterviewSession)
    if user_name:
        query = query.filter(DBInterviewSession.user_name.ilike(f"%{user_name}%"))

    total = query.count()
    sessions = (
        query.order_by(DBInterviewSession.start_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    summaries = [
        SessionSummary(
            session_id=s.id,
            user_name=s.user_name,
            job_role=s.job_role,
            start_time=s.start_time,
            end_time=s.end_time,
            status=SessionStatus(s.status),
            overall_score=s.overall_score,
            question_count=s.question_count,
            duration_minutes=_duration(s.start_time, s.end_time),
        )
        for s in sessions
    ]

    return SessionHistory(sessions=summaries, total=total, page=page, page_size=page_size)


# ─── Aggregate Stats ──────────────────────────────────────────────────────────

@router.get("/stats", response_model=AggregateStats)
def get_stats(user_name: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Return aggregate statistics for the history dashboard."""
    query = db.query(DBInterviewSession).filter(DBInterviewSession.status == "completed")
    if user_name:
        query = query.filter(DBInterviewSession.user_name.ilike(f"%{user_name}%"))

    sessions = query.all()
    total = len(sessions)

    scores = [s.overall_score for s in sessions if s.overall_score is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    best_score = round(max(scores), 1) if scores else 0.0

    # Sessions this week
    # SQLite stores naive datetimes — compare without timezone
    week_ago = datetime.now() - timedelta(days=7)
    sessions_this_week = sum(1 for s in sessions if s.start_time and s.start_time >= week_ago)

    # Most practiced competency
    answer_query = db.query(DBAnswer)
    if user_name:
        session_ids = [s.id for s in sessions]
        answer_query = answer_query.filter(DBAnswer.session_id.in_(session_ids))

    answers = answer_query.all()
    comp_counts: dict = {}
    for a in answers:
        if a.competency:
            comp_counts[a.competency] = comp_counts.get(a.competency, 0) + 1

    most_practiced = max(comp_counts, key=comp_counts.get) if comp_counts else None

    # Score trend (last 10 sessions)
    recent = sorted(
        [s for s in sessions if s.overall_score is not None],
        key=lambda s: s.start_time,
    )[-10:]

    score_trend = [
        {
            "date": s.start_time.strftime("%Y-%m-%d"),
            "score": s.overall_score,
            "job_role": s.job_role,
        }
        for s in recent
    ]

    return AggregateStats(
        total_sessions=total,
        avg_score=avg_score,
        best_score=best_score,
        sessions_this_week=sessions_this_week,
        most_practiced_competency=most_practiced,
        score_trend=score_trend,
    )


# ─── Delete Session ───────────────────────────────────────────────────────────

@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Delete a session and its answers from history."""
    session = db.query(DBInterviewSession).filter(DBInterviewSession.id == session_id).first()
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found.")

    db.query(DBAnswer).filter(DBAnswer.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"message": "Session deleted.", "session_id": session_id}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _duration(start: Optional[datetime], end: Optional[datetime]) -> Optional[float]:
    if start and end:
        return round((end - start).total_seconds() / 60, 1)
    return None
