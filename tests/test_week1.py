"""
Week 1 Tests — Knowledge base, document loading, chunking, baseline Q&A flow.
Tests: document loading, question bank parsing, vector index, basic chat/Q&A.
"""
import json
import os
import pytest
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Question Bank Loading ─────────────────────────────────────────────────────

class TestQuestionBankLoading:
    """Test that the question bank loads correctly from JSON."""

    def test_question_bank_file_exists(self):
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "question_bank.json")
        assert os.path.exists(path), "question_bank.json must exist"

    def test_question_bank_valid_json(self):
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "question_bank.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "questions" in data, "JSON must have 'questions' key"
        assert len(data["questions"]) > 0, "Question bank must not be empty"

    def test_question_bank_has_required_fields(self):
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "question_bank.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        required = {"id", "text", "category", "difficulty", "competency"}
        for q in data["questions"]:
            missing = required - set(q.keys())
            assert not missing, f"Question {q.get('id')} missing fields: {missing}"

    def test_question_bank_difficulty_values(self):
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "question_bank.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        valid = {"easy", "medium", "hard"}
        for q in data["questions"]:
            assert q["difficulty"] in valid, f"Invalid difficulty: {q['difficulty']}"

    def test_question_bank_has_star_hints(self):
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "question_bank.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for q in data["questions"]:
            hints = q.get("star_hints", {})
            assert isinstance(hints, dict), f"star_hints must be a dict for {q['id']}"


# ── Rubrics Loading ───────────────────────────────────────────────────────────

class TestRubricsLoading:
    """Test that rubrics.json loads and has correct structure."""

    def test_rubrics_file_exists(self):
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "rubrics.json")
        assert os.path.exists(path)

    def test_rubrics_valid_json(self):
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "rubrics.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "rubrics" in data
        assert len(data["rubrics"]) == 5, "Should have 5 rubric criteria"

    def test_rubrics_weights_sum_to_one(self):
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "rubrics.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        total = sum(r["weight"] for r in data["rubrics"])
        assert abs(total - 1.0) < 0.01, f"Rubric weights must sum to 1.0, got {total}"

    def test_rubrics_have_score_bands(self):
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "rubrics.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "score_bands" in data
        assert "excellent" in data["score_bands"]


# ── Question Service ──────────────────────────────────────────────────────────

class TestQuestionService:
    """Test the QuestionService loads and filters correctly."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from backend.services.question_service import QuestionService
        self.svc = QuestionService()
        self.svc.load_questions()

    def test_loads_questions(self):
        assert len(self.svc.questions) > 0

    def test_get_by_id(self):
        q = self.svc.get_question_by_id("L001")
        assert q is not None
        assert q["id"] == "L001"

    def test_get_by_id_missing(self):
        q = self.svc.get_question_by_id("NONEXISTENT")
        assert q is None

    def test_get_by_competency(self):
        qs = self.svc.get_questions_by_competency("Leadership")
        assert len(qs) > 0
        assert all(q["competency"] == "Leadership" for q in qs)

    def test_get_by_difficulty(self):
        qs = self.svc.get_questions_by_difficulty("easy")
        assert len(qs) > 0
        assert all(q["difficulty"] == "easy" for q in qs)

    def test_get_competencies(self):
        comps = self.svc.get_competencies()
        assert "Leadership" in comps
        assert "Teamwork" in comps

    def test_random_session_questions_count(self):
        qs = self.svc.get_random_session_questions("Software Engineer", count=5)
        assert len(qs) == 5

    def test_random_session_questions_unique(self):
        qs = self.svc.get_random_session_questions("Manager", count=5)
        ids = [q["id"] for q in qs]
        assert len(ids) == len(set(ids)), "Session questions must be unique"

    def test_filter_by_competency_and_difficulty(self):
        qs = self.svc.filter_questions(competency="Leadership", difficulty="hard")
        assert all(q["competency"] == "Leadership" and q["difficulty"] == "hard" for q in qs)


# ── Vector Store ──────────────────────────────────────────────────────────────

class TestVectorStore:
    """Test vector index building and search."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from backend.services.question_service import QuestionService
        from backend.services.vector_store import VectorStoreService
        svc = QuestionService()
        svc.load_questions()
        self.vs = VectorStoreService()
        self.vs.build_index(svc.questions)

    def test_index_built(self):
        assert self.vs.embeddings is not None
        assert len(self.vs.questions) > 0

    def test_search_returns_results(self):
        results = self.vs.search_similar("leadership team challenge", k=3)
        assert len(results) > 0

    def test_search_result_has_required_fields(self):
        results = self.vs.search_similar("conflict resolution", k=2)
        for r in results:
            assert "id" in r
            assert "text" in r

    def test_search_k_limit(self):
        results = self.vs.search_similar("communication", k=3)
        assert len(results) <= 3
