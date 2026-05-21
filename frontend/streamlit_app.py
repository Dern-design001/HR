"""
HR Interview Simulator — Streamlit Frontend
PRJ-026 | Full 3-Week Implementation
"""
import time
import requests
import streamlit as st
from datetime import datetime

API_BASE = "http://localhost:8000/api/v1"

# ─── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="HR Interview Simulator",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem; border-radius: 12px; color: white;
        text-align: center; margin-bottom: 2rem;
    }
    .score-card {
        background: white; border-radius: 10px; padding: 1.5rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center;
    }
    .question-box {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 12px; padding: 1.5rem; margin: 1rem 0;
        border-left: 5px solid #667eea;
    }
    .star-hint {
        background: #fff3cd; border-radius: 8px; padding: 1rem;
        border-left: 4px solid #ffc107; margin: 0.5rem 0;
    }
    .feedback-box {
        background: #e8f5e9; border-radius: 10px; padding: 1.5rem;
        border-left: 5px solid #4caf50; margin: 1rem 0;
    }
    .better-answer-box {
        background: #e3f2fd; border-radius: 10px; padding: 1.5rem;
        border-left: 5px solid #2196f3; margin: 1rem 0;
    }
    .timer-box {
        background: #fff; border-radius: 8px; padding: 0.8rem;
        text-align: center; font-size: 1.5rem; font-weight: bold;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .competency-badge {
        display: inline-block; background: #667eea; color: white;
        padding: 0.2rem 0.8rem; border-radius: 20px; font-size: 0.85rem;
        margin: 0.2rem;
    }
    .stProgress > div > div > div { background-color: #667eea; }
</style>
""", unsafe_allow_html=True)


# ─── Session State Init ───────────────────────────────────────────────────────

def init_state():
    defaults = {
        "page": "home",
        "session_id": None,
        "user_name": "",
        "job_role": "",
        "current_question": None,
        "question_number": 1,
        "total_questions": 5,
        "answer_scores": [],
        "session_complete": False,
        "report": None,
        "timer_start": None,
        "time_limit": 120,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ─── API Helpers ──────────────────────────────────────────────────────────────

def api_post(endpoint, data):
    try:
        r = requests.post(f"{API_BASE}{endpoint}", json=data, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to the backend. Make sure the FastAPI server is running on port 8000.")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None

def api_get(endpoint, params=None):
    try:
        r = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to the backend. Make sure the FastAPI server is running on port 8000.")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


# ─── Sidebar Navigation ───────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.markdown("## 🎯 HR Interview Simulator")
        st.markdown("---")
        pages = {
            "🏠 Home": "home",
            "🎤 Practice Interview": "interview",
            "📊 My Results": "results",
            "📈 History Dashboard": "history",
            "❓ Question Bank": "questions",
        }
        for label, page in pages.items():
            if st.button(label, use_container_width=True,
                         type="primary" if st.session_state.page == page else "secondary"):
                st.session_state.page = page
                st.rerun()

        st.markdown("---")
        st.markdown("### 📋 Quick Tips")
        st.info("Use the **STAR method**: Situation → Task → Action → Result")
        st.markdown("**Scoring Rubric:**")
        st.markdown("- 🌟 STAR Method (40%)")
        st.markdown("- 🎯 Specificity (20%)")
        st.markdown("- 🔗 Relevance (20%)")
        st.markdown("- 💬 Clarity (10%)")
        st.markdown("- 🪞 Self-Awareness (10%)")


# ─── Home Page ────────────────────────────────────────────────────────────────

def render_home():
    st.markdown("""
    <div class="main-header">
        <h1>🎯 HR Interview Simulator</h1>
        <p style="font-size:1.2rem; opacity:0.9;">
            Master behavioral interviews with AI-powered coaching and rubric-based scoring
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="score-card"><h2>30+</h2><p>Questions</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="score-card"><h2>6</h2><p>Competencies</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="score-card"><h2>5</h2><p>Rubric Criteria</p></div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="score-card"><h2>AI</h2><p>Powered Feedback</p></div>', unsafe_allow_html=True)

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### 🚀 Get Started")
        st.markdown("""
        1. Enter your name and target job role
        2. Answer behavioral questions using STAR method
        3. Get instant rubric-based scoring
        4. Review AI-generated better answers
        5. Track your progress over time
        """)
        if st.button("▶ Start Practice Interview", type="primary", use_container_width=True):
            st.session_state.page = "interview"
            st.rerun()
    with col_b:
        st.markdown("### 🏆 Competencies Covered")
        competencies = ["Leadership", "Teamwork", "Problem Solving",
                        "Communication", "Adaptability", "Conflict Resolution"]
        for c in competencies:
            st.markdown(f'<span class="competency-badge">{c}</span>', unsafe_allow_html=True)


# ─── Interview Setup ──────────────────────────────────────────────────────────

def render_interview_setup():
    st.markdown("## 🎤 Start Your Practice Interview")
    with st.form("setup_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Your Name", placeholder="e.g. Alex Johnson")
        with col2:
            role = st.text_input("Target Job Role", placeholder="e.g. Product Manager")
        q_count = st.slider("Number of Questions", min_value=1, max_value=10, value=5)
        submitted = st.form_submit_button("🚀 Start Interview", type="primary", use_container_width=True)

    if submitted:
        if not name.strip() or not role.strip():
            st.error("Please enter your name and job role.")
            return
        result = api_post("/sessions/start", {
            "user_name": name.strip(),
            "job_role": role.strip(),
            "question_count": q_count,
        })
        if result:
            st.session_state.session_id = result["id"]
            st.session_state.user_name = name.strip()
            st.session_state.job_role = role.strip()
            st.session_state.total_questions = result["question_count"]
            st.session_state.question_number = 1
            st.session_state.answer_scores = []
            st.session_state.session_complete = False
            st.session_state.report = None
            _load_next_question()
            st.rerun()


def _load_next_question():
    sid = st.session_state.session_id
    q_data = api_get(f"/sessions/{sid}/next-question")
    if q_data:
        st.session_state.current_question = q_data
        st.session_state.question_number = q_data["question_number"]
        st.session_state.time_limit = q_data.get("time_limit", 120)
        st.session_state.timer_start = time.time()


# ─── Interview Question ───────────────────────────────────────────────────────

def render_interview_question():
    q_data = st.session_state.current_question
    if not q_data:
        st.warning("No question loaded. Please start a new session.")
        return

    q = q_data["question"]
    num = st.session_state.question_number
    total = st.session_state.total_questions

    # Progress
    st.progress(num / total)
    st.markdown(f"**Question {num} of {total}** | 👤 {st.session_state.user_name} | 💼 {st.session_state.job_role}")

    # Timer
    elapsed = int(time.time() - (st.session_state.timer_start or time.time()))
    remaining = max(0, st.session_state.time_limit - elapsed)
    timer_color = "#ef4444" if remaining < 30 else "#f97316" if remaining < 60 else "#22c55e"
    st.markdown(
        f'<div class="timer-box" style="color:{timer_color}">⏱ {remaining // 60:02d}:{remaining % 60:02d} remaining</div>',
        unsafe_allow_html=True,
    )

    # Question
    st.markdown(f"""
    <div class="question-box">
        <h3>❓ {q['text']}</h3>
        <span class="competency-badge">{q['competency']}</span>
        <span class="competency-badge">{q['difficulty'].upper()}</span>
    </div>
    """, unsafe_allow_html=True)

    # STAR hints toggle
    with st.expander("💡 STAR Method Hints"):
        hints = q.get("star_hints", {})
        for part, hint in hints.items():
            st.markdown(f'<div class="star-hint"><strong>{part.upper()}:</strong> {hint}</div>',
                        unsafe_allow_html=True)

    # Answer form
    with st.form(f"answer_form_{num}"):
        answer = st.text_area(
            "Your Answer",
            height=200,
            placeholder="Use the STAR method: Situation → Task → Action → Result...",
        )
        col1, col2 = st.columns([3, 1])
        with col1:
            submitted = st.form_submit_button("✅ Submit Answer", type="primary", use_container_width=True)
        with col2:
            skipped = st.form_submit_button("⏭ Skip", use_container_width=True)

    if submitted and answer.strip():
        time_taken = int(time.time() - (st.session_state.timer_start or time.time()))
        result = api_post(f"/answers/{st.session_state.session_id}/submit", {
            "question_id": q["id"],
            "answer_text": answer.strip(),
            "time_taken": time_taken,
        })
        if result:
            st.session_state.answer_scores.append(result)
            if num >= total:
                api_post(f"/sessions/{st.session_state.session_id}/complete", {})
                st.session_state.session_complete = True
                _load_report()
            else:
                _load_next_question()
            st.rerun()
    elif submitted:
        st.warning("Please write your answer before submitting.")


def _load_report():
    sid = st.session_state.session_id
    report = api_get(f"/reports/{sid}")
    if report:
        st.session_state.report = report


# ─── Results Page ─────────────────────────────────────────────────────────────

def render_results():
    if not st.session_state.answer_scores and not st.session_state.report:
        st.info("Complete an interview session to see your results here.")
        if st.button("Start Interview"):
            st.session_state.page = "interview"
            st.rerun()
        return

    report = st.session_state.report
    if not report and st.session_state.session_id:
        _load_report()
        report = st.session_state.report

    if not report:
        st.warning("Report not available yet. Complete the session first.")
        return

    st.markdown("## 📊 Your Interview Results")

    # Score overview
    overall = report.get("overall_score", 0)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Overall Score", f"{overall:.1f}/100")
    with col2:
        st.metric("Questions Answered", report.get("total_questions", 0))
    with col3:
        st.metric("Duration", f"{report.get('duration_minutes', 0):.1f} min")
    with col4:
        band = _score_band(overall)
        st.metric("Rating", band)

    # Score gauge
    st.progress(overall / 100)

    # Competency breakdown
    st.markdown("### 🏆 Competency Scores")
    comp_scores = report.get("competency_scores", [])
    if comp_scores:
        cols = st.columns(len(comp_scores))
        for i, cs in enumerate(comp_scores):
            with cols[i]:
                st.metric(cs["competency"], f"{cs['score']:.1f}")
                st.progress(cs["score"] / 100)

    # Strengths & improvements
    col_s, col_i = st.columns(2)
    with col_s:
        st.markdown("### ✅ Strengths")
        for s in report.get("strengths", []):
            st.success(f"✓ {s}")
    with col_i:
        st.markdown("### 🔧 Areas to Improve")
        for imp in report.get("improvements", []):
            st.warning(f"→ {imp}")

    # Per-question details
    st.markdown("### 📝 Question-by-Question Breakdown")
    for i, detail in enumerate(report.get("answer_details", []), 1):
        with st.expander(f"Q{i}: {detail['question_text'][:80]}... | Score: {detail['overall_score']:.1f}/100"):
            st.markdown(f"**Your Answer:** {detail['answer_text']}")
            st.markdown(f"**Time Taken:** {detail['time_taken']}s")
            st.markdown(f"**Feedback:** {detail.get('feedback', 'N/A')}")

            # Rubric breakdown
            st.markdown("**Rubric Scores:**")
            for r in detail.get("rubric_scores", []):
                pct = (r["score"] / r["max_score"]) * 100 if r["max_score"] > 0 else 0
                st.markdown(f"- **{r['criteria']}**: {r['score']:.1f}/{r['max_score']:.0f} — {r['feedback']}")
                st.progress(pct / 100)

            # Better answer
            if detail.get("better_answer"):
                st.markdown('<div class="better-answer-box">', unsafe_allow_html=True)
                st.markdown("**💡 Suggested Better Answer:**")
                st.markdown(detail["better_answer"])
                st.markdown('</div>', unsafe_allow_html=True)


# ─── History Dashboard ────────────────────────────────────────────────────────

def render_history():
    st.markdown("## 📈 History Dashboard")

    col1, col2 = st.columns([3, 1])
    with col1:
        user_filter = st.text_input("Filter by name", placeholder="Leave blank for all sessions")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        refresh = st.button("🔄 Refresh", use_container_width=True)

    # Stats
    params = {"user_name": user_filter} if user_filter else {}
    stats = api_get("/history/stats", params=params)
    if stats:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Sessions", stats.get("total_sessions", 0))
        c2.metric("Avg Score", f"{stats.get('avg_score', 0):.1f}")
        c3.metric("Best Score", f"{stats.get('best_score', 0):.1f}")
        c4.metric("This Week", stats.get("sessions_this_week", 0))

        if stats.get("most_practiced_competency"):
            st.info(f"🏆 Most Practiced: **{stats['most_practiced_competency']}**")

        # Score trend
        trend = stats.get("score_trend", [])
        if trend:
            st.markdown("### 📉 Score Trend")
            import pandas as pd
            df = pd.DataFrame(trend)
            if not df.empty and "score" in df.columns:
                st.line_chart(df.set_index("date")["score"])

    # Session list
    st.markdown("### 📋 Session History")
    sessions_data = api_get("/history/sessions", params=params)
    if sessions_data and sessions_data.get("sessions"):
        for s in sessions_data["sessions"]:
            score_str = f"{s['overall_score']:.1f}/100" if s.get("overall_score") else "N/A"
            status_icon = "✅" if s["status"] == "completed" else "⏸" if s["status"] == "abandoned" else "🔄"
            with st.expander(
                f"{status_icon} {s['user_name']} | {s['job_role']} | Score: {score_str} | {s['start_time'][:10]}"
            ):
                col_a, col_b, col_c = st.columns(3)
                col_a.markdown(f"**Questions:** {s['question_count']}")
                col_b.markdown(f"**Duration:** {s.get('duration_minutes', 'N/A')} min")
                col_c.markdown(f"**Status:** {s['status'].upper()}")

                if s["status"] == "completed":
                    if st.button(f"View Report", key=f"report_{s['session_id']}"):
                        report = api_get(f"/reports/{s['session_id']}")
                        if report:
                            st.session_state.report = report
                            st.session_state.page = "results"
                            st.rerun()
    else:
        st.info("No sessions found. Complete an interview to see history here.")


# ─── Question Bank Page ───────────────────────────────────────────────────────

def render_questions():
    st.markdown("## ❓ Question Bank")

    col1, col2 = st.columns(2)
    with col1:
        comp_data = api_get("/questions/meta/competencies")
        competencies = ["All"] + (comp_data.get("competencies", []) if comp_data else [])
        selected_comp = st.selectbox("Filter by Competency", competencies)
    with col2:
        selected_diff = st.selectbox("Filter by Difficulty", ["All", "easy", "medium", "hard"])

    params = {}
    if selected_comp != "All":
        params["competency"] = selected_comp
    if selected_diff != "All":
        params["difficulty"] = selected_diff

    questions = api_get("/questions/", params=params)
    if questions:
        st.markdown(f"**{len(questions)} questions found**")
        for q in questions:
            diff_color = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(q["difficulty"], "⚪")
            with st.expander(f"{diff_color} [{q['competency']}] {q['text'][:90]}..."):
                st.markdown(f"**Full Question:** {q['text']}")
                st.markdown(f"**Competency:** {q['competency']} | **Difficulty:** {q['difficulty'].upper()}")
                if q.get("star_hints"):
                    st.markdown("**STAR Hints:**")
                    for part, hint in q["star_hints"].items():
                        st.markdown(f"- **{part.upper()}:** {hint}")
                if q.get("follow_up_questions"):
                    st.markdown("**Follow-up Questions:**")
                    for fq in q["follow_up_questions"]:
                        st.markdown(f"- {fq}")
    else:
        st.info("No questions found.")


# ─── Score Band Helper ────────────────────────────────────────────────────────

def _score_band(score: float) -> str:
    if score >= 85:
        return "🌟 Excellent"
    elif score >= 70:
        return "✅ Good"
    elif score >= 55:
        return "📊 Average"
    elif score >= 40:
        return "⚠ Below Avg"
    return "❌ Poor"


# ─── Main Router ──────────────────────────────────────────────────────────────

render_sidebar()

page = st.session_state.page

if page == "home":
    render_home()
elif page == "interview":
    if st.session_state.session_complete:
        render_results()
    elif st.session_state.current_question:
        render_interview_question()
    else:
        render_interview_setup()
elif page == "results":
    render_results()
elif page == "history":
    render_history()
elif page == "questions":
    render_questions()
