from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timezone
import uuid

from backend.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}  # needed for SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ─── ORM Models ───────────────────────────────────────────────────────────────

class DBInterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_name = Column(String(100), nullable=False)
    job_role = Column(String(100), nullable=False)
    start_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    end_time = Column(DateTime, nullable=True)
    status = Column(String(20), default="active")
    question_count = Column(Integer, default=5)
    current_question_index = Column(Integer, default=0)
    question_ids = Column(Text, default="[]")  # JSON-encoded list
    overall_score = Column(Float, nullable=True)


class DBQuestion(Base):
    __tablename__ = "questions"

    id = Column(String, primary_key=True)
    text = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    difficulty = Column(String(20), nullable=False)
    competency = Column(String(100), nullable=False)
    follow_ups = Column(Text, default="[]")
    star_hints = Column(Text, default="{}")
    sample_answer_keywords = Column(Text, default="[]")
    is_custom = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class DBAnswer(Base):
    __tablename__ = "answers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, nullable=False)
    question_id = Column(String, nullable=False)
    answer_text = Column(Text, nullable=False)
    time_taken = Column(Integer, default=0)
    score = Column(Float, nullable=True)
    rubric_scores = Column(Text, default="{}")
    feedback = Column(Text, nullable=True)
    better_answer = Column(Text, nullable=True)
    competency = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ─── DB Helpers ───────────────────────────────────────────────────────────────

def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency that provides a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
