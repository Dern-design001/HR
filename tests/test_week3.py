"""
Week 3 Tests — End-to-end API flow, history/logging, UX, final demo readiness.
Tests: FastAPI endpoints, session lifecycle, report generation, history dashboard.

Root cause note: vector_store_service.build_index() tries to download a
sentence-transformers model on first use. We patch it out at the service
singleton level BEFORE importing backend.main so the lifespan never blocks.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Force SQLite test DB before any backend import ────────────────────────────
os.environ["DATABASE_URL"] = "sqlite:///./test_hr_simulator.db"


def _make_client():
    """
    Build a TestClient with the vector store fully mocked so no model
    download happens during the FastAPI lifespan startup.
    """
    import numpy as np
    from unittest.mock import MagicMock

    # Patch the singleton BEFORE importing main
    import backend.services.vector_store as vs_mod
    mock_vs = MagicMock()
    mock_vs.questions = []
    mock_vs.embeddings = np.zeros((1, 10), dtype="float32")
    mock_vs.build_index = MagicMock(return_value=None)
    mock_vs.search_similar = MagicMock(return_value=[])
    vs_mod.vector_store_service = mock_vs

    # Also patch the reference inside main
    import backend.main as main_mod
    main_mod.vector_store_service = mock_vs

    from fastapi.testclient import TestClient
    return TestClient(main_mod.app)


@pytest.fixture(scope="module")
def client():
    c = _make_client()
    with c:
        yield c
    # Close all SQLAlchemy connections before deleting the file (Windows file-lock fix)
    try:
        from backend.models.database import engine
        engine.dispose()
    except Exception:
        pass
    import time
    time.sleep(0.3)
    try:
        if os.path.exists("test_hr_simulator.db"):
            os.remove("test_hr_simulator.db")
    except PermissionError:
        pass  # File still locked — leave it, it's just a test artifact


# ── Health & Root ─────────────────────────────────────────────────────────────

class TestHealthEndpoints:
    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["status"] == "running"

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"
        assert data["questions_loaded"] > 0


# ── Questions API ─────────────────────────────────────────────────────────────

class TestQuestionsAPI:
    def test_list_questions(self, client):
        r = client.get("/api/v1/questions/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) > 0

    def test_list_questions_filter_competency(self, client):
        r = client.get("/api/v1/questions/?competency=Leadership")
        assert r.status_code == 200
        assert all(q["competency"] == "Leadership" for q in r.json())

    def test_list_questions_filter_difficulty(self, client):
        r = client.get("/api/v1/questions/?difficulty=easy")
        assert r.status_code == 200
        assert all(q["difficulty"] == "easy" for q in r.json())

    def test_get_question_by_id(self, client):
        r = client.get("/api/v1/questions/L001")
        assert r.status_code == 200
        assert r.json()["id"] == "L001"

    def test_get_question_not_found(self, client):
        r = client.get("/api/v1/questions/NONEXISTENT")
        assert r.status_code == 404

    def test_get_competencies(self, client):
        r = client.get("/api/v1/questions/meta/competencies")
        assert r.status_code == 200
        assert "Leadership" in r.json()["competencies"]

    def test_generate_question(self, client):
        r = client.post("/api/v1/questions/generate", json={
            "competency": "Leadership",
            "difficulty": "medium",
            "job_role": "Manager",
        })
        assert r.status_code == 200
        data = r.json()
        assert "text" in data
        assert "id" in data


# ── Session Lifecycle ─────────────────────────────────────────────────────────

class TestSessionLifecycle:
    @pytest.fixture
    def session(self, client):
        r = client.post("/api/v1/sessions/start", json={
            "user_name": "Test User",
            "job_role": "Software Engineer",
            "question_count": 3,
        })
        assert r.status_code == 200
        return r.json()

    def test_start_session(self, client):
        r = client.post("/api/v1/sessions/start", json={
            "user_name": "Alice",
            "job_role": "Product Manager",
            "question_count": 5,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["user_name"] == "Alice"
        assert data["status"] == "active"
        assert data["question_count"] == 5
        assert "id" in data

    def test_start_session_missing_name(self, client):
        r = client.post("/api/v1/sessions/start", json={
            "user_name": "",
            "job_role": "Engineer",
            "question_count": 3,
        })
        assert r.status_code == 422

    def test_get_session(self, client, session):
        r = client.get(f"/api/v1/sessions/{session['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == session["id"]

    def test_get_session_not_found(self, client):
        r = client.get("/api/v1/sessions/nonexistent-id")
        assert r.status_code == 404

    def test_get_next_question(self, client, session):
        r = client.get(f"/api/v1/sessions/{session['id']}/next-question")
        assert r.status_code == 200
        data = r.json()
        assert "question" in data
        assert data["question_number"] == 1
        assert data["total_questions"] == 3

    def test_session_status(self, client, session):
        r = client.get(f"/api/v1/sessions/{session['id']}/status")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "active"
        assert data["total_questions"] == 3

    def test_complete_session(self, client, session):
        r = client.post(f"/api/v1/sessions/{session['id']}/complete")
        assert r.status_code == 200

    def test_abandon_session(self, client):
        r = client.post("/api/v1/sessions/start", json={
            "user_name": "Bob",
            "job_role": "Designer",
            "question_count": 2,
        })
        sid = r.json()["id"]
        r2 = client.post(f"/api/v1/sessions/{sid}/abandon")
        assert r2.status_code == 200


# ── Answer Submission ─────────────────────────────────────────────────────────

class TestAnswerSubmission:
    @pytest.fixture
    def active_session(self, client):
        r = client.post("/api/v1/sessions/start", json={
            "user_name": "Carol",
            "job_role": "Team Lead",
            "question_count": 2,
        })
        return r.json()

    def test_submit_answer(self, client, active_session):
        sid = active_session["id"]
        q_r = client.get(f"/api/v1/sessions/{sid}/next-question")
        q_id = q_r.json()["question"]["id"]

        r = client.post(f"/api/v1/answers/{sid}/submit", json={
            "question_id": q_id,
            "answer_text": (
                "In my previous role, I was tasked with leading a team of 8 engineers. "
                "I implemented daily standups and a Kanban board. As a result, we delivered "
                "the project 3 weeks ahead of schedule, saving $20,000. I learned that "
                "clear communication prevents most blockers."
            ),
            "time_taken": 90,
        })
        assert r.status_code == 200
        data = r.json()
        assert "overall_score" in data
        assert 0 <= data["overall_score"] <= 100
        assert len(data["rubric_scores"]) == 5
        assert "feedback" in data

    def test_submit_answer_invalid_session(self, client):
        r = client.post("/api/v1/answers/bad-session-id/submit", json={
            "question_id": "L001",
            "answer_text": "Some answer",
            "time_taken": 60,
        })
        assert r.status_code == 404

    def test_get_session_answers(self, client, active_session):
        sid = active_session["id"]
        q_r = client.get(f"/api/v1/sessions/{sid}/next-question")
        q_id = q_r.json()["question"]["id"]
        client.post(f"/api/v1/answers/{sid}/submit", json={
            "question_id": q_id,
            "answer_text": "I worked on a team project and delivered results on time.",
            "time_taken": 60,
        })
        r = client.get(f"/api/v1/answers/{sid}/all")
        assert r.status_code == 200
        assert len(r.json()) >= 1


# ── Report Generation ─────────────────────────────────────────────────────────

class TestReportGeneration:
    @pytest.fixture
    def completed_session(self, client):
        r = client.post("/api/v1/sessions/start", json={
            "user_name": "Dave",
            "job_role": "Analyst",
            "question_count": 2,
        })
        sid = r.json()["id"]
        for _ in range(2):
            q_r = client.get(f"/api/v1/sessions/{sid}/next-question")
            if q_r.status_code != 200:
                break
            q_id = q_r.json()["question"]["id"]
            client.post(f"/api/v1/answers/{sid}/submit", json={
                "question_id": q_id,
                "answer_text": (
                    "During my time at XYZ Corp, I was responsible for leading a cross-functional "
                    "team of 6. I organised weekly syncs and tracked milestones on a shared board. "
                    "As a result, we launched on time and increased user satisfaction by 25%. "
                    "I learned to delegate more effectively and communicate blockers early."
                ),
                "time_taken": 100,
            })
        client.post(f"/api/v1/sessions/{sid}/complete")
        return sid

    def test_get_report(self, client, completed_session):
        r = client.get(f"/api/v1/reports/{completed_session}")
        assert r.status_code == 200
        data = r.json()
        assert "overall_score" in data
        assert "strengths" in data
        assert "improvements" in data
        assert "competency_scores" in data
        assert "answer_details" in data

    def test_report_not_found(self, client):
        r = client.get("/api/v1/reports/nonexistent-session")
        assert r.status_code == 404


# ── History Dashboard ─────────────────────────────────────────────────────────

class TestHistoryDashboard:
    def test_list_sessions(self, client):
        r = client.get("/api/v1/history/sessions")
        assert r.status_code == 200
        data = r.json()
        assert "sessions" in data
        assert "total" in data

    def test_list_sessions_filter(self, client):
        r = client.get("/api/v1/history/sessions?user_name=Alice")
        assert r.status_code == 200

    def test_get_stats(self, client):
        r = client.get("/api/v1/history/stats")
        assert r.status_code == 200
        data = r.json()
        assert "total_sessions" in data
        assert "avg_score" in data
        assert "best_score" in data
        assert "score_trend" in data

    def test_pagination(self, client):
        r = client.get("/api/v1/history/sessions?page=1&page_size=5")
        assert r.status_code == 200
        data = r.json()
        assert data["page"] == 1
        assert data["page_size"] == 5
