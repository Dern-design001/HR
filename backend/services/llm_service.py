"""
LangChain LLM service with mock mode fallback.
Works out-of-the-box without an OpenAI API key.
"""
import random
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


# ─── Mock Response Templates ──────────────────────────────────────────────────

MOCK_FEEDBACK_TEMPLATES = [
    (
        "Your answer demonstrates a solid understanding of the competency. "
        "You provided a clear situation and described your actions well. "
        "To strengthen your response, consider adding more specific metrics to quantify the impact of your actions. "
        "For example, instead of saying 'the project improved,' try 'the project delivered 20% ahead of schedule.' "
        "Your use of the STAR method was evident, though the Result component could be more detailed."
    ),
    (
        "Good effort on this response. You clearly described the context and your role. "
        "The actions you took were specific and showed initiative. "
        "However, the result section was brief — interviewers want to hear the measurable impact. "
        "Try to quantify outcomes wherever possible: team size, time saved, revenue impact, or customer satisfaction scores. "
        "Also, consider adding a brief reflection on what you learned from the experience."
    ),
    (
        "Your answer shows relevant experience and good communication skills. "
        "The situation was well-described and your task was clear. "
        "To improve, focus on making your actions more specific — use 'I' statements to show personal ownership. "
        "The result you described was positive, but adding numbers would make it much more compelling. "
        "Consider also mentioning any challenges you overcame during the process."
    ),
]

MOCK_BETTER_ANSWER_TEMPLATES = [
    """Here's an improved version of your answer using the STAR method:

**Situation:** In my previous role as [your role] at [company], we faced [specific challenge]. The team of [X] people was struggling with [specific issue], which was impacting [business metric].

**Task:** As the [your role], I was responsible for [specific responsibility]. The goal was to [measurable objective] within [timeframe].

**Action:** I took several concrete steps:
1. First, I [specific action with detail] — this involved [how you did it].
2. I then [second action], which required [skill/approach].
3. To address [specific challenge], I [third action] by [method].
4. I communicated progress weekly to [stakeholders] using [tool/format].

**Result:** As a direct result of these actions:
- [Metric 1] improved by X% within [timeframe]
- [Metric 2] was achieved, saving [time/money]
- The team [positive outcome]
- [Stakeholder] recognized the effort by [recognition]

**Reflection:** This experience taught me [key lesson], which I now apply by [how you apply it].""",

    """Here's a stronger version of your answer:

**Situation:** While working at [company] as [role], I encountered a situation where [specific challenge]. This was significant because [business impact/stakes].

**Task:** My responsibility was to [specific task]. I needed to [objective] while [constraint — time/budget/resources].

**Action:** My approach was systematic:
- I started by [first action] to understand [root cause/scope]
- I collaborated with [specific people/teams] to [what you did together]
- I implemented [specific solution] using [tools/methods]
- I monitored progress through [metrics/checkpoints] and adjusted [what you adjusted]

**Result:** The outcome exceeded expectations:
- Delivered [result] [X]% ahead of schedule/budget
- Reduced [problem] by [percentage]
- Received positive feedback from [stakeholder]
- The solution was later adopted by [broader team/company]

This experience reinforced my belief that [key principle/learning].""",
]

MOCK_FOLLOW_UP_TEMPLATES = [
    "That's a great example. Can you tell me more about how you handled the most challenging moment in that situation?",
    "Interesting. What would you do differently if you faced a similar situation today with more experience?",
    "You mentioned the outcome was positive. How did you measure success, and what metrics did you track?",
    "How did your team members respond to your approach? Was there any resistance?",
    "What was the biggest risk you took in that situation, and how did you mitigate it?",
    "Can you walk me through your decision-making process when you chose that particular course of action?",
    "How did this experience shape your approach to similar challenges going forward?",
]

MOCK_GENERATED_QUESTIONS = {
    "Leadership": [
        "Tell me about a time you had to rebuild trust with a team after a significant setback.",
        "Describe a situation where you had to make a critical decision with incomplete information.",
        "Give me an example of how you've developed a high-potential employee into a leader.",
    ],
    "Teamwork": [
        "Tell me about a time you had to integrate a new team member who was struggling to fit in.",
        "Describe a situation where you had to work with someone whose work style was very different from yours.",
        "Give me an example of a time you went above and beyond to support a teammate.",
    ],
    "Problem Solving": [
        "Tell me about a time you had to solve a problem that no one else in your team had faced before.",
        "Describe a situation where you had to make a trade-off between two equally important priorities.",
        "Give me an example of a creative solution you developed to overcome a significant obstacle.",
    ],
    "Communication": [
        "Tell me about a time you had to change your communication style to be more effective with a specific audience.",
        "Describe a situation where you had to deliver bad news to a client or stakeholder.",
        "Give me an example of a time your written communication prevented a misunderstanding.",
    ],
    "Adaptability": [
        "Tell me about a time you had to completely change your approach mid-project due to new information.",
        "Describe a situation where you had to work effectively in a completely new industry or domain.",
        "Give me an example of how you've thrived in a fast-changing environment.",
    ],
    "Conflict Resolution": [
        "Tell me about a time you had to de-escalate a heated situation between colleagues.",
        "Describe a situation where you had to find a compromise that neither party was initially happy with.",
        "Give me an example of a time you turned a conflict into a productive collaboration.",
    ],
}


# ─── LLM Service ─────────────────────────────────────────────────────────────

class LLMService:
    """
    LangChain-based LLM service with automatic fallback to mock mode
    when no valid OpenAI API key is provided.
    """

    def __init__(self):
        self.llm = None
        self.mock_mode = True
        self._initialize_llm()

    def _initialize_llm(self):
        """Attempt to initialize the real LLM; fall back to mock mode."""
        try:
            from backend.config import settings
            if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your-openai-api-key-here":
                from langchain_openai import ChatOpenAI
                self.llm = ChatOpenAI(
                    model=settings.LLM_MODEL,
                    openai_api_key=settings.OPENAI_API_KEY,
                    temperature=0.7,
                )
                self.mock_mode = False
                logger.info("LLM initialized with OpenAI API key.")
            else:
                logger.info("No valid OpenAI API key found. Running in mock mode.")
        except ImportError:
            logger.warning("langchain_openai not installed. Running in mock mode.")
        except Exception as e:
            logger.warning(f"Failed to initialize LLM: {e}. Running in mock mode.")

    # ─── Public Methods ───────────────────────────────────────────────────────

    def generate_feedback(
        self,
        question: str,
        answer: str,
        scores: Dict[str, Any],
    ) -> str:
        """Generate detailed feedback for a given answer."""
        if self.mock_mode:
            return self._mock_feedback(question, answer, scores)
        return self._llm_feedback(question, answer, scores)

    def generate_better_answer(
        self,
        question: str,
        user_answer: str,
        rubric_scores: List[Dict[str, Any]],
    ) -> str:
        """Generate an improved model answer."""
        if self.mock_mode:
            return random.choice(MOCK_BETTER_ANSWER_TEMPLATES)
        return self._llm_better_answer(question, user_answer, rubric_scores)

    def generate_follow_up(self, question: str, answer: str) -> str:
        """Generate a contextual follow-up question."""
        if self.mock_mode:
            return random.choice(MOCK_FOLLOW_UP_TEMPLATES)
        return self._llm_follow_up(question, answer)

    def generate_dynamic_question(
        self,
        competency: str,
        difficulty: str,
        job_role: Optional[str] = None,
    ) -> str:
        """Generate a new behavioral interview question."""
        if self.mock_mode:
            questions = MOCK_GENERATED_QUESTIONS.get(competency, MOCK_GENERATED_QUESTIONS["Leadership"])
            return random.choice(questions)
        return self._llm_generate_question(competency, difficulty, job_role)

    # ─── Mock Implementations ─────────────────────────────────────────────────

    def _mock_feedback(self, question: str, answer: str, scores: Dict[str, Any]) -> str:
        overall = scores.get("overall_score", 50)
        base = random.choice(MOCK_FEEDBACK_TEMPLATES)

        if overall >= 80:
            prefix = "Excellent response! "
        elif overall >= 60:
            prefix = "Good response with room for improvement. "
        else:
            prefix = "This response needs significant development. "

        return prefix + base

    # ─── Real LLM Implementations ─────────────────────────────────────────────

    def _llm_feedback(self, question: str, answer: str, scores: Dict[str, Any]) -> str:
        from langchain.prompts import ChatPromptTemplate
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are an expert HR interviewer and career coach. "
                "Provide specific, actionable feedback on behavioral interview answers. "
                "Be constructive, encouraging, and specific. Keep feedback to 3-4 sentences."
            )),
            ("human", (
                "Question: {question}\n\n"
                "Candidate's Answer: {answer}\n\n"
                "Scores: {scores}\n\n"
                "Provide detailed feedback on this answer."
            )),
        ])
        chain = prompt | self.llm
        result = chain.invoke({"question": question, "answer": answer, "scores": str(scores)})
        return result.content

    def _llm_better_answer(self, question: str, user_answer: str, rubric_scores: List[Dict]) -> str:
        from langchain.prompts import ChatPromptTemplate
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are an expert HR interviewer. Generate an improved model answer "
                "using the STAR method (Situation, Task, Action, Result). "
                "The answer should be specific, compelling, and demonstrate the target competency clearly."
            )),
            ("human", (
                "Question: {question}\n\n"
                "Original Answer: {answer}\n\n"
                "Generate a significantly improved version of this answer using the STAR method."
            )),
        ])
        chain = prompt | self.llm
        result = chain.invoke({"question": question, "answer": user_answer})
        return result.content

    def _llm_follow_up(self, question: str, answer: str) -> str:
        from langchain.prompts import ChatPromptTemplate
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert HR interviewer. Generate one insightful follow-up question."),
            ("human", "Original question: {question}\nCandidate's answer: {answer}\nGenerate a follow-up question."),
        ])
        chain = prompt | self.llm
        result = chain.invoke({"question": question, "answer": answer})
        return result.content

    def _llm_generate_question(self, competency: str, difficulty: str, job_role: Optional[str]) -> str:
        from langchain.prompts import ChatPromptTemplate
        role_context = f" for a {job_role} role" if job_role else ""
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert HR interviewer. Generate behavioral interview questions."),
            ("human", (
                f"Generate one {difficulty} behavioral interview question{role_context} "
                f"that assesses the '{competency}' competency. "
                "Start with 'Tell me about a time...' or 'Describe a situation...' or 'Give me an example...'"
            )),
        ])
        chain = prompt | self.llm
        result = chain.invoke({})
        return result.content.strip()


# Singleton instance
llm_service = LLMService()
