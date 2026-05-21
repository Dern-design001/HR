"""
Week 2 Tests — Retrieval, scoring, prompt tuning, citations, edge queries, fallback handling.
Tests: rubric scoring, answer evaluation, LLM service mock mode, edge cases.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Scoring Service ───────────────────────────────────────────────────────────

class TestScoringService:
    """Test rubric-based scoring logic."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from backend.services.scoring_service import ScoringService
        self.svc = ScoringService()
        self.sample_question = {
            "id": "L001",
            "text": "Tell me about a time when you had to lead a team through a difficult project.",
            "competency": "Leadership",
            "difficulty": "medium",
        }

    def test_score_answer_returns_dict(self):
        result = self.svc.score_answer(self.sample_question, "I led a team.", 60)
        assert isinstance(result, dict)

    def test_score_answer_has_overall_score(self):
        result = self.svc.score_answer(self.sample_question, "I led a team.", 60)
        assert "overall_score" in result
        assert 0 <= result["overall_score"] <= 100

    def test_score_answer_has_rubric_scores(self):
        result = self.svc.score_answer(self.sample_question, "I led a team.", 60)
        assert "rubric_scores" in result
        assert len(result["rubric_scores"]) == 5

    def test_strong_star_answer_scores_higher(self):
        weak = "I did some work on a project."
        strong = (
            "In my role at Acme Corp, I was tasked with leading a 10-person team through a critical "
            "product launch. My responsibility was to coordinate all workstreams and ensure delivery "
            "by Q3. I implemented daily standups, created a risk register, and delegated tasks based "
            "on individual strengths. As a result, we delivered the project 2 weeks ahead of schedule, "
            "increasing revenue by 15%. I learned that clear communication is key to team success."
        )
        weak_result = self.svc.score_answer(self.sample_question, weak, 30)
        strong_result = self.svc.score_answer(self.sample_question, strong, 120)
        assert strong_result["overall_score"] > weak_result["overall_score"]

    def test_star_method_evaluation(self):
        answer = (
            "When I was at my previous company, I was tasked with leading a migration. "
            "I implemented a phased rollout and communicated progress weekly. "
            "As a result, we achieved 99.9% uptime and delivered on time."
        )
        score = self.svc.evaluate_star_method(answer.lower())
        assert score > 0
        assert score <= 40

    def test_specificity_with_numbers(self):
        answer_with_numbers = "We reduced costs by 30% and saved $50,000 in Q3 2023."
        answer_vague = "We usually improve things generally and typically do better."
        score_specific = self.svc.evaluate_specificity(answer_with_numbers.lower())
        score_vague = self.svc.evaluate_specificity(answer_vague.lower())
        assert score_specific > score_vague

    def test_relevance_on_topic(self):
        on_topic = "I led the team through a difficult project by delegating tasks and communicating clearly."
        off_topic = "I enjoy cooking pasta and hiking on weekends."
        score_on = self.svc.evaluate_relevance(self.sample_question["text"], on_topic.lower())
        score_off = self.svc.evaluate_relevance(self.sample_question["text"], off_topic.lower())
        assert score_on > score_off

    def test_self_awareness_with_reflection(self):
        reflective = "I learned from this experience that I should communicate earlier. Looking back, I would do differently."
        no_reflection = "Everything went perfectly and there were no issues at all."
        score_r = self.svc.evaluate_self_awareness(reflective.lower())
        score_n = self.svc.evaluate_self_awareness(no_reflection.lower())
        assert score_r > score_n

    def test_time_adjustment_ideal_range(self):
        adj = self.svc._time_adjustment(120)
        assert adj == 2.0

    def test_time_adjustment_too_fast(self):
        adj = self.svc._time_adjustment(10)
        assert adj < 0

    def test_time_adjustment_too_slow(self):
        adj = self.svc._time_adjustment(400)
        assert adj < 0

    def test_overall_score_calculation(self):
        rubric_scores = [
            {"score": 32, "max_score": 40},
            {"score": 16, "max_score": 20},
            {"score": 16, "max_score": 20},
            {"score": 8, "max_score": 10},
            {"score": 8, "max_score": 10},
        ]
        overall = self.svc.calculate_overall_score(rubric_scores)
        assert overall == 80.0

    def test_score_empty_answer(self):
        result = self.svc.score_answer(self.sample_question, "I don't know.", 5)
        assert result["overall_score"] < 50

    def test_score_answer_has_feedback(self):
        result = self.svc.score_answer(self.sample_question, "I led a team project.", 60)
        assert "feedback" in result
        assert isinstance(result["feedback"], str)


# ── LLM Service Mock Mode ─────────────────────────────────────────────────────

class TestLLMServiceMockMode:
    """Test LLM service operates correctly in mock mode."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from backend.services.llm_service import LLMService
        self.svc = LLMService()

    def test_mock_mode_active(self):
        # Without a real API key, mock mode should be active
        assert self.svc.mock_mode is True

    def test_generate_feedback_returns_string(self):
        feedback = self.svc.generate_feedback("Question?", "My answer.", {"overall_score": 70})
        assert isinstance(feedback, str)
        assert len(feedback) > 10

    def test_generate_better_answer_returns_string(self):
        better = self.svc.generate_better_answer("Question?", "My answer.", [])
        assert isinstance(better, str)
        assert len(better) > 50

    def test_generate_follow_up_returns_string(self):
        follow_up = self.svc.generate_follow_up("Question?", "My answer.")
        assert isinstance(follow_up, str)
        assert "?" in follow_up

    def test_generate_dynamic_question_returns_string(self):
        q = self.svc.generate_dynamic_question("Leadership", "medium", "Manager")
        assert isinstance(q, str)
        assert len(q) > 10

    def test_generate_dynamic_question_all_competencies(self):
        competencies = ["Leadership", "Teamwork", "Problem Solving",
                        "Communication", "Adaptability", "Conflict Resolution"]
        for comp in competencies:
            q = self.svc.generate_dynamic_question(comp, "medium")
            assert isinstance(q, str)


# ── Edge Cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Test edge cases and fallback handling."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from backend.services.scoring_service import ScoringService
        from backend.services.question_service import QuestionService
        self.scoring = ScoringService()
        self.questions = QuestionService()
        self.questions.load_questions()
        self.q = {"id": "T001", "text": "Tell me about teamwork.", "competency": "Teamwork", "difficulty": "easy"}

    def test_very_long_answer(self):
        long_answer = "I led the team. " * 200
        result = self.scoring.score_answer(self.q, long_answer, 300)
        assert 0 <= result["overall_score"] <= 100

    def test_single_word_answer(self):
        result = self.scoring.score_answer(self.q, "Yes.", 5)
        assert result["overall_score"] < 40

    def test_answer_with_special_characters(self):
        answer = "We achieved 100% success! The team's effort was #1. Cost: $50k."
        result = self.scoring.score_answer(self.q, answer, 60)
        assert isinstance(result["overall_score"], float)

    def test_question_service_missing_id(self):
        q = self.questions.get_question_by_id("DOES_NOT_EXIST_999")
        assert q is None

    def test_filter_returns_empty_for_unknown_competency(self):
        qs = self.questions.filter_questions(competency="Underwater Basket Weaving")
        assert qs == []

    def test_session_questions_with_count_exceeding_bank(self):
        # Should not crash even if count > available questions
        qs = self.questions.get_random_session_questions("Any Role", count=10)
        assert len(qs) <= 10
        assert len(qs) > 0
