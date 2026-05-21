"""
Rubric-based scoring service.
Evaluates answers on STAR method, specificity, relevance, clarity, and self-awareness.
"""
import json
import logging
import os
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

RUBRICS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "rubrics.json")


class ScoringService:
    def __init__(self):
        self.rubrics: List[Dict[str, Any]] = []
        self._load_rubrics()

    # ─── Setup ────────────────────────────────────────────────────────────────

    def _load_rubrics(self):
        try:
            path = os.path.abspath(RUBRICS_PATH)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.rubrics = data.get("rubrics", [])
            logger.info(f"Loaded {len(self.rubrics)} rubrics.")
        except Exception as e:
            logger.error(f"Failed to load rubrics: {e}")
            self.rubrics = []

    # ─── Main Scoring Entry Point ─────────────────────────────────────────────

    def score_answer(
        self,
        question: Dict[str, Any],
        answer_text: str,
        time_taken: int,
    ) -> Dict[str, Any]:
        """
        Score an answer against all rubric criteria.
        Returns a dict with per-criterion scores and an overall score.
        """
        answer_lower = answer_text.lower()
        question_text = question.get("text", "")

        star_score = self.evaluate_star_method(answer_lower)
        specificity_score = self.evaluate_specificity(answer_lower)
        relevance_score = self.evaluate_relevance(question_text, answer_lower)
        clarity_score = self.evaluate_clarity(answer_text)
        self_awareness_score = self.evaluate_self_awareness(answer_lower)

        rubric_scores = [
            {
                "criteria": "STAR Method",
                "weight": 0.40,
                "score": star_score,
                "max_score": 40.0,
                "feedback": self._star_feedback(star_score),
            },
            {
                "criteria": "Specificity",
                "weight": 0.20,
                "score": specificity_score,
                "max_score": 20.0,
                "feedback": self._specificity_feedback(specificity_score),
            },
            {
                "criteria": "Relevance",
                "weight": 0.20,
                "score": relevance_score,
                "max_score": 20.0,
                "feedback": self._relevance_feedback(relevance_score),
            },
            {
                "criteria": "Communication Clarity",
                "weight": 0.10,
                "score": clarity_score,
                "max_score": 10.0,
                "feedback": self._clarity_feedback(clarity_score),
            },
            {
                "criteria": "Self-Awareness",
                "weight": 0.10,
                "score": self_awareness_score,
                "max_score": 10.0,
                "feedback": self._self_awareness_feedback(self_awareness_score),
            },
        ]

        overall = self.calculate_overall_score(rubric_scores)

        # Time bonus/penalty (small adjustment)
        time_adjustment = self._time_adjustment(time_taken)
        overall = max(0.0, min(100.0, overall + time_adjustment))

        # Try to enhance with LLM scoring
        try:
            from backend.services.llm_service import llm_service
            feedback = llm_service.generate_feedback(
                question_text,
                answer_text,
                {"overall_score": overall},
            )
        except Exception:
            feedback = self._generate_text_feedback(overall, rubric_scores)

        return {
            "rubric_scores": rubric_scores,
            "overall_score": round(overall, 1),
            "star_score": star_score,
            "specificity_score": specificity_score,
            "relevance_score": relevance_score,
            "clarity_score": clarity_score,
            "self_awareness_score": self_awareness_score,
            "feedback": feedback,
            "time_taken": time_taken,
        }

    # ─── Individual Criteria Evaluators ──────────────────────────────────────

    def evaluate_star_method(self, answer: str) -> float:
        """
        Score 0-40 based on presence of S/T/A/R components.
        Each component is worth up to 10 points.
        """
        rubric = next((r for r in self.rubrics if r["id"] == "star_method"), None)
        if not rubric:
            return 20.0  # default mid-score

        components = rubric.get("components", {})
        component_scores = {}

        for component, config in components.items():
            keywords = config.get("keywords", [])
            hits = sum(1 for kw in keywords if kw.lower() in answer)
            # Score 0-10 per component based on keyword density
            component_scores[component] = min(10.0, hits * 2.5)

        total = sum(component_scores.values())
        # Bonus for having all 4 components
        if all(s > 0 for s in component_scores.values()):
            total = min(40.0, total + 5.0)

        return round(min(40.0, total), 1)

    def evaluate_specificity(self, answer: str) -> float:
        """Score 0-20 based on concrete details vs. vague language."""
        # Positive signals: numbers, percentages, proper nouns, timeframes
        specific_patterns = [
            r"\d+%",                          # percentages
            r"\$[\d,]+",                      # dollar amounts
            r"\d+ (people|team members|employees|weeks|months|days|hours)",
            r"(january|february|march|april|may|june|july|august|september|october|november|december)",
            r"(q[1-4]|quarter|fiscal year)",
            r"\d{4}",                         # years
            r"(increased|decreased|reduced|improved|grew|saved) by \d+",
        ]
        vague_patterns = [
            r"\b(usually|sometimes|often|generally|typically|kind of|sort of|basically|pretty much)\b",
            r"\b(we always|i tend to|in general|most of the time)\b",
        ]

        specific_hits = sum(1 for p in specific_patterns if re.search(p, answer))
        vague_hits = sum(1 for p in vague_patterns if re.search(p, answer))

        # Word count bonus (longer answers tend to be more specific)
        word_count = len(answer.split())
        length_bonus = min(5.0, word_count / 40)

        score = (specific_hits * 4.0) - (vague_hits * 2.0) + length_bonus
        return round(max(2.0, min(20.0, score)), 1)

    def evaluate_relevance(self, question: str, answer: str) -> float:
        """Score 0-20 based on keyword overlap between question and answer."""
        # Extract meaningful words from question
        stop_words = {"a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
                      "for", "of", "with", "by", "from", "is", "was", "were", "are",
                      "have", "had", "has", "do", "did", "does", "me", "you", "we",
                      "tell", "describe", "give", "example", "time", "when", "how"}

        q_words = set(re.findall(r"\b[a-z]{3,}\b", question.lower())) - stop_words
        a_words = set(re.findall(r"\b[a-z]{3,}\b", answer.lower())) - stop_words

        if not q_words:
            return 15.0  # default

        overlap = len(q_words & a_words) / len(q_words)
        score = overlap * 20.0

        # Minimum floor — assume some relevance if answer is substantial
        if len(answer.split()) > 50:
            score = max(score, 8.0)

        return round(min(20.0, score), 1)

    def evaluate_clarity(self, answer: str) -> float:
        """Score 0-10 based on structure, sentence length, and coherence."""
        sentences = re.split(r"[.!?]+", answer)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return 2.0

        # Average sentence length (ideal: 15-25 words)
        avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
        if 10 <= avg_len <= 30:
            length_score = 4.0
        elif avg_len < 5 or avg_len > 50:
            length_score = 1.0
        else:
            length_score = 2.5

        # Sentence count (ideal: 5-15 sentences for a behavioral answer)
        n = len(sentences)
        if 4 <= n <= 20:
            count_score = 3.0
        elif n < 2:
            count_score = 0.5
        else:
            count_score = 1.5

        # Filler word penalty
        filler_words = ["um", "uh", "like", "you know", "basically", "literally"]
        filler_hits = sum(answer.lower().count(fw) for fw in filler_words)
        filler_penalty = min(2.0, filler_hits * 0.5)

        score = length_score + count_score + 3.0 - filler_penalty
        return round(max(1.0, min(10.0, score)), 1)

    def evaluate_self_awareness(self, answer: str) -> float:
        """Score 0-10 based on reflection and growth mindset indicators."""
        reflection_keywords = [
            "i learned", "i realized", "looking back", "in hindsight",
            "i would do differently", "i grew", "i improved", "i recognized",
            "i reflected", "taught me", "lesson", "mistake", "challenge",
            "difficult", "struggled", "overcame", "growth",
        ]
        hits = sum(1 for kw in reflection_keywords if kw in answer)
        score = min(10.0, hits * 2.5 + 2.0)  # base of 2 for attempting the question
        return round(score, 1)

    # ─── Overall Score ────────────────────────────────────────────────────────

    def calculate_overall_score(self, rubric_scores: List[Dict[str, Any]]) -> float:
        """Weighted sum of all rubric scores, normalized to 0-100."""
        total = sum(r["score"] for r in rubric_scores)
        max_total = sum(r["max_score"] for r in rubric_scores)
        if max_total == 0:
            return 0.0
        return round((total / max_total) * 100, 1)

    # ─── Time Adjustment ──────────────────────────────────────────────────────

    def _time_adjustment(self, time_taken: int) -> float:
        """
        Small score adjustment based on time taken.
        Ideal range: 60-180 seconds.
        Too fast (<30s) or too slow (>240s) gets a small penalty.
        """
        if time_taken < 30:
            return -5.0  # too brief
        if time_taken > 300:
            return -3.0  # too long / rambling
        if 60 <= time_taken <= 180:
            return 2.0   # ideal range bonus
        return 0.0

    # ─── Feedback Text Generators ─────────────────────────────────────────────

    def _star_feedback(self, score: float) -> str:
        if score >= 32:
            return "Excellent use of the STAR method. All four components are clearly present."
        if score >= 24:
            return "Good STAR structure. Consider strengthening the Result component with specific metrics."
        if score >= 16:
            return "Partial STAR structure. Make sure to include all four components: Situation, Task, Action, Result."
        return "STAR method is largely missing. Structure your answer with a clear Situation, Task, Action, and Result."

    def _specificity_feedback(self, score: float) -> str:
        if score >= 16:
            return "Great use of specific details, numbers, and concrete examples."
        if score >= 10:
            return "Some specifics present. Add more numbers, percentages, and concrete details."
        return "Answer is too vague. Include specific metrics, team sizes, timeframes, and measurable outcomes."

    def _relevance_feedback(self, score: float) -> str:
        if score >= 16:
            return "Answer is highly relevant and directly addresses the question."
        if score >= 10:
            return "Mostly relevant but drifts slightly. Stay focused on the specific competency being assessed."
        return "Answer doesn't fully address the question. Re-read the question and ensure your example is directly relevant."

    def _clarity_feedback(self, score: float) -> str:
        if score >= 8:
            return "Clear, well-structured, and easy to follow."
        if score >= 5:
            return "Reasonably clear. Work on sentence structure and avoid filler words."
        return "Clarity needs improvement. Use shorter sentences and organize your thoughts before speaking."

    def _self_awareness_feedback(self, score: float) -> str:
        if score >= 8:
            return "Strong self-reflection. You clearly articulate lessons learned and personal growth."
        if score >= 5:
            return "Some self-awareness shown. Add more reflection on what you learned or would do differently."
        return "Add a reflection component — what did you learn from this experience? What would you do differently?"

    def _generate_text_feedback(self, overall: float, rubric_scores: List[Dict]) -> str:
        weak = [r for r in rubric_scores if r["score"] / r["max_score"] < 0.6]
        strong = [r for r in rubric_scores if r["score"] / r["max_score"] >= 0.8]

        parts = []
        if overall >= 80:
            parts.append("Strong answer overall.")
        elif overall >= 60:
            parts.append("Solid answer with room for improvement.")
        else:
            parts.append("This answer needs significant development.")

        if strong:
            parts.append(f"Strengths: {', '.join(r['criteria'] for r in strong)}.")
        if weak:
            parts.append(f"Focus on improving: {', '.join(r['criteria'] for r in weak)}.")

        return " ".join(parts)


# Singleton instance
scoring_service = ScoringService()
