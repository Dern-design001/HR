from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class DifficultyLevel(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class SessionStatus(str, Enum):
    active = "active"
    completed = "completed"
    abandoned = "abandoned"


# ─── Question Schemas ────────────────────────────────────────────────────────

class QuestionBase(BaseModel):
    text: str
    category: str
    difficulty: DifficultyLevel
    competency: str
    follow_ups: Optional[List[str]] = []


class QuestionCreate(QuestionBase):
    pass


class Question(QuestionBase):
    id: str
    star_hints: Optional[Dict[str, str]] = {}
    sample_answer_keywords: Optional[List[str]] = []
    model_config = ConfigDict(from_attributes=True)


# ─── Interview Session Schemas ────────────────────────────────────────────────

class SessionStartRequest(BaseModel):
    user_name: str = Field(..., min_length=1, max_length=100)
    job_role: str = Field(..., min_length=1, max_length=100)
    question_count: int = Field(default=5, ge=1, le=10)


class InterviewSessionBase(BaseModel):
    user_name: str
    job_role: str


class InterviewSessionCreate(InterviewSessionBase):
    question_count: int = 5


class InterviewSession(InterviewSessionBase):
    id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: SessionStatus = SessionStatus.active
    question_count: int = 5
    current_question_index: int = 0
    question_ids: Optional[List[str]] = []
    model_config = ConfigDict(from_attributes=True)


class SessionStatusResponse(BaseModel):
    session_id: str
    status: SessionStatus
    current_question_index: int
    total_questions: int
    time_elapsed: Optional[float] = None


# ─── Answer Schemas ───────────────────────────────────────────────────────────

class AnswerSubmit(BaseModel):
    question_id: str
    answer_text: str = Field(..., min_length=1)
    time_taken: int = Field(..., ge=0, description="Time taken in seconds")


class AnswerBase(BaseModel):
    session_id: str
    question_id: str
    answer_text: str
    time_taken: int


class AnswerCreate(AnswerBase):
    pass


class Answer(AnswerBase):
    id: str
    score: Optional[float] = None
    feedback: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ─── Scoring Schemas ──────────────────────────────────────────────────────────

class ScoreRubric(BaseModel):
    criteria: str
    weight: float
    score: float
    max_score: float
    feedback: str


class AnswerScore(BaseModel):
    question_id: str
    question_text: str
    answer_text: str
    time_taken: int
    rubric_scores: List[ScoreRubric]
    overall_score: float
    star_score: Optional[float] = None
    specificity_score: Optional[float] = None
    relevance_score: Optional[float] = None
    clarity_score: Optional[float] = None
    self_awareness_score: Optional[float] = None
    feedback: Optional[str] = None
    better_answer: Optional[str] = None


# ─── Feedback Report Schemas ──────────────────────────────────────────────────

class CompetencyScore(BaseModel):
    competency: str
    score: float
    question_count: int


class FeedbackReport(BaseModel):
    session_id: str
    user_name: str
    job_role: str
    overall_score: float
    total_questions: int
    duration_minutes: float
    strengths: List[str]
    improvements: List[str]
    better_answers: List[Dict[str, Any]]
    competency_scores: List[CompetencyScore]
    answer_details: List[AnswerScore]
    generated_at: datetime


# ─── History Schemas ──────────────────────────────────────────────────────────

class SessionSummary(BaseModel):
    session_id: str
    user_name: str
    job_role: str
    start_time: datetime
    end_time: Optional[datetime]
    status: SessionStatus
    overall_score: Optional[float]
    question_count: int
    duration_minutes: Optional[float]


class SessionHistory(BaseModel):
    sessions: List[SessionSummary]
    total: int
    page: int
    page_size: int


class AggregateStats(BaseModel):
    total_sessions: int
    avg_score: float
    best_score: float
    sessions_this_week: int
    most_practiced_competency: Optional[str]
    score_trend: List[Dict[str, Any]]


# ─── Next Question Response ───────────────────────────────────────────────────

class NextQuestionResponse(BaseModel):
    question: Question
    question_number: int
    total_questions: int
    time_limit: int
    session_id: str


# ─── Generate Question Request ────────────────────────────────────────────────

class GenerateQuestionRequest(BaseModel):
    competency: str
    difficulty: DifficultyLevel = DifficultyLevel.medium
    job_role: Optional[str] = None
