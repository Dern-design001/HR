"""
Question service — loads the question bank, selects session questions,
and generates dynamic questions via the LLM service.
"""
import json
import logging
import os
import random
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

QUESTION_BANK_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "question_bank.json")


class QuestionService:
    def __init__(self):
        self.questions: List[Dict[str, Any]] = []
        self.questions_by_id: Dict[str, Dict[str, Any]] = {}
        self.competencies: List[str] = []

    # ─── Loading ──────────────────────────────────────────────────────────────

    def load_questions(self) -> List[Dict[str, Any]]:
        """Load questions from the JSON question bank."""
        try:
            path = os.path.abspath(QUESTION_BANK_PATH)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.questions = data.get("questions", [])
            self.questions_by_id = {q["id"]: q for q in self.questions}
            self.competencies = sorted(set(q["competency"] for q in self.questions))
            logger.info(f"Loaded {len(self.questions)} questions from question bank.")
            return self.questions
        except FileNotFoundError:
            logger.error(f"Question bank not found at {QUESTION_BANK_PATH}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse question bank: {e}")
            return []

    # ─── Retrieval ────────────────────────────────────────────────────────────

    def get_all_questions(self) -> List[Dict[str, Any]]:
        return self.questions

    def get_question_by_id(self, question_id: str) -> Optional[Dict[str, Any]]:
        return self.questions_by_id.get(question_id)

    def get_questions_by_competency(self, competency: str) -> List[Dict[str, Any]]:
        return [q for q in self.questions if q["competency"].lower() == competency.lower()]

    def get_questions_by_difficulty(self, difficulty: str) -> List[Dict[str, Any]]:
        return [q for q in self.questions if q["difficulty"].lower() == difficulty.lower()]

    def get_competencies(self) -> List[str]:
        return self.competencies

    def filter_questions(
        self,
        competency: Optional[str] = None,
        difficulty: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        result = self.questions
        if competency:
            result = [q for q in result if q["competency"].lower() == competency.lower()]
        if difficulty:
            result = [q for q in result if q["difficulty"].lower() == difficulty.lower()]
        return result

    # ─── Session Question Selection ───────────────────────────────────────────

    def get_random_session_questions(
        self,
        job_role: str,
        count: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Select a diverse set of questions for an interview session.
        Ensures coverage across multiple competencies and difficulty levels.
        """
        if not self.questions:
            self.load_questions()

        # Group by competency
        by_competency: Dict[str, List[Dict]] = {}
        for q in self.questions:
            comp = q["competency"]
            by_competency.setdefault(comp, []).append(q)

        selected: List[Dict[str, Any]] = []
        competencies = list(by_competency.keys())
        random.shuffle(competencies)

        # Round-robin across competencies
        comp_cycle = competencies * (count // len(competencies) + 1)
        for comp in comp_cycle:
            if len(selected) >= count:
                break
            pool = by_competency.get(comp, [])
            available = [q for q in pool if q not in selected]
            if available:
                selected.append(random.choice(available))

        # Shuffle final selection
        random.shuffle(selected)
        return selected[:count]

    # ─── Follow-up Generation ─────────────────────────────────────────────────

    def get_follow_up(self, question_id: str, answer_text: str) -> Optional[str]:
        """Return a follow-up question — from the bank or LLM-generated."""
        question = self.get_question_by_id(question_id)
        if not question:
            return None

        # Use pre-defined follow-ups if available
        follow_ups = question.get("follow_up_questions", [])
        if follow_ups:
            return random.choice(follow_ups)

        # Fall back to LLM
        try:
            from backend.services.llm_service import llm_service
            return llm_service.generate_follow_up(question["text"], answer_text)
        except Exception as e:
            logger.warning(f"LLM follow-up generation failed: {e}")
            return "Can you elaborate on the outcome and what you learned from that experience?"

    # ─── Dynamic Question Generation ─────────────────────────────────────────

    def generate_dynamic_question(
        self,
        competency: str,
        difficulty: str = "medium",
        job_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a new question using the LLM service."""
        try:
            from backend.services.llm_service import llm_service
            text = llm_service.generate_dynamic_question(competency, difficulty, job_role)
        except Exception as e:
            logger.warning(f"LLM question generation failed: {e}")
            # Fall back to a random existing question from the competency
            existing = self.get_questions_by_competency(competency)
            if existing:
                q = random.choice(existing)
                text = q["text"]
            else:
                text = f"Tell me about a time you demonstrated {competency} skills."

        import uuid
        return {
            "id": f"DYN-{str(uuid.uuid4())[:8].upper()}",
            "text": text,
            "category": "Behavioral",
            "difficulty": difficulty,
            "competency": competency,
            "follow_up_questions": [],
            "star_hints": {
                "situation": "Describe the context and background.",
                "task": "Explain your specific responsibility.",
                "action": "Detail the concrete steps you took.",
                "result": "Share the measurable outcome.",
            },
            "sample_answer_keywords": [],
            "is_dynamic": True,
        }


# Singleton instance
question_service = QuestionService()
