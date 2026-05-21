# 🎯 HR Interview Simulator — PRJ-026

> Behavioral interview practice bot with AI-powered scoring, STAR method coaching, and better-answer suggestions.

| Field | Value |
|---|---|
| **Project Code** | PRJ-026 |
| **Category** | Interview Simulators |
| **Domain** | Careers |
| **Focus** | GenAI |
| **Stack** | FastAPI · LangChain · Streamlit · FAISS · SQLite |
| **Total Marks** | 45 |

---

## 📁 Project Structure

```
hr-interview-simulator/
├── backend/
│   ├── data/
│   │   ├── question_bank.json      # 30+ behavioral questions across 6 competencies
│   │   └── rubrics.json            # 5-criteria scoring rubric
│   ├── models/
│   │   ├── database.py             # SQLAlchemy ORM models
│   │   └── schemas.py              # Pydantic request/response schemas
│   ├── routers/
│   │   ├── sessions.py             # Session start/status/next-question/complete
│   │   ├── answers.py              # Answer submission & scoring
│   │   ├── reports.py              # Feedback report generation
│   │   ├── history.py              # History dashboard & stats
│   │   └── questions.py            # Question bank & dynamic generation
│   ├── services/
│   │   ├── llm_service.py          # LangChain LLM + mock mode fallback
│   │   ├── question_service.py     # Question loading, filtering, selection
│   │   ├── scoring_service.py      # Rubric-based answer scoring
│   │   └── vector_store.py         # FAISS/TF-IDF semantic search
│   ├── config.py                   # App settings (pydantic-settings)
│   └── main.py                     # FastAPI app entry point
├── frontend/
│   ├── index.html                  # HTML/CSS/JS standalone UI
│   ├── style.css                   # Full responsive stylesheet
│   ├── app.js                      # Frontend JavaScript
│   └── streamlit_app.py            # Streamlit alternative frontend
├── tests/
│   ├── test_week1.py               # Week 1: data loading, vector store
│   ├── test_week2.py               # Week 2: scoring, LLM, edge cases
│   └── test_week3.py               # Week 3: end-to-end API tests
├── requirements.txt
├── .env.example
├── run_backend.bat
├── run_streamlit.bat
└── run_tests.bat
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
copy .env.example .env
# Edit .env — add your OpenAI API key (optional, app works without it)
```

### 3. Start the Backend
```bash
# Option A: Double-click run_backend.bat
# Option B:
python -m uvicorn backend.main:app --reload --port 8000
```

### 4. Open the UI

**HTML/CSS/JS UI** (no server needed):
```
Open frontend/index.html in your browser
```

**Streamlit UI**:
```bash
# Option A: Double-click run_streamlit.bat
# Option B:
python -m streamlit run frontend/streamlit_app.py
```

### 5. API Docs
```
http://localhost:8000/docs      ← Swagger UI
http://localhost:8000/redoc     ← ReDoc
```

---

## 🧪 Running Tests

```bash
# All tests
python -m pytest tests/ -v

# By week
python -m pytest tests/test_week1.py -v
python -m pytest tests/test_week2.py -v
python -m pytest tests/test_week3.py -v
```

---

## 📊 Scoring Rubric

| Criterion | Weight | Max Points |
|---|---|---|
| STAR Method | 40% | 40 |
| Specificity | 20% | 20 |
| Relevance | 20% | 20 |
| Communication Clarity | 10% | 10 |
| Self-Awareness | 10% | 10 |

**Score Bands:** Excellent (85+) · Good (70-84) · Average (55-69) · Below Average (40-54) · Poor (<40)

---

## 📅 3-Week Implementation Plan

### Week 1 (15 marks) — Knowledge Base & Basic Q&A
- ✅ Question bank with 30+ behavioral questions across 6 competencies
- ✅ FAISS/TF-IDF vector store for semantic question search
- ✅ Basic session creation and question delivery
- ✅ Document loading and chunking pipeline

### Week 2 (15 marks) — Retrieval, Scoring & Prompt Tuning
- ✅ Rubric-based scoring (STAR, specificity, relevance, clarity, self-awareness)
- ✅ LangChain LLM integration with mock mode fallback
- ✅ Better-answer suggestions via prompt engineering
- ✅ Follow-up question generation
- ✅ Dynamic question generation by competency

### Week 3 (15 marks) — UX, History & Final Polish
- ✅ Full HTML/CSS/JS responsive UI with timer, score visualization
- ✅ Streamlit frontend with sidebar navigation
- ✅ History dashboard with score trends and session management
- ✅ Feedback report with competency breakdown
- ✅ End-to-end test suite (Week 1 + 2 + 3)

---

## 🔑 Key Features

- **Timed Answer Flow** — Configurable countdown timer per question
- **STAR Method Hints** — Built-in coaching for every question
- **Rubric-Based Scoring** — 5-criteria evaluation with weighted scores
- **AI Feedback** — LangChain-powered feedback (mock mode without API key)
- **Better-Answer Suggestions** — Model answers showing how to improve
- **History Dashboard** — Score trends, competency analysis, session history
- **Semantic Search** — FAISS/TF-IDF vector search over question bank
- **Mock Mode** — Fully functional without an OpenAI API key

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/sessions/start` | Start a new interview session |
| GET | `/api/v1/sessions/{id}/next-question` | Get next question |
| POST | `/api/v1/answers/{session_id}/submit` | Submit and score an answer |
| GET | `/api/v1/reports/{session_id}` | Get full feedback report |
| GET | `/api/v1/history/sessions` | List session history |
| GET | `/api/v1/history/stats` | Aggregate statistics |
| GET | `/api/v1/questions/` | Browse question bank |
| POST | `/api/v1/questions/generate` | Generate dynamic question |
