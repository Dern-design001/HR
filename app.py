"""
HR Interview Simulator — Hugging Face Spaces Entry Point
PRJ-026 | Self-contained: runs backend services directly (no FastAPI server needed)
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import time
import streamlit as st
from datetime import datetime

# ── Bootstrap backend services directly ──────────────────────────────────────
from backend.models.database import create_tables
from backend.services.question_service import question_service
from backend.services.scoring_service import scoring_service
from backend.services.llm_service import llm_service

# Init DB and load questions once
create_tables()
if not question_service.questions:
    question_service.load_questions()

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HR Interview Simulator",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .main-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 2rem; border-radius: 14px; color: white;
    text-align: center; margin-bottom: 2rem;
  }
  .question-box {
    background: linear-gradient(135deg, #f8faff 0%, #eef2ff 100%);
    border-radius: 12px; padding: 1.5rem; margin: 1rem 0;
    border-left: 5px solid #6366f1;
  }
  .score-box {
    background: #f0fdf4; border-left: 4px solid #22c55e;
    border-radius: 10px; padding: 1.2rem; margin: 1rem 0;
  }
  .feedback-box {
    background: #eff6ff; border-left: 4px solid #3b82f6;
    border-radius: 10px; padding: 1.2rem; margin: 1rem 0;
  }
  .better-box {
    background: #fefce8; border-left: 4px solid #f59e0b;
    border-radius: 10px; padding: 1.2rem; margin: 1rem 0;
  }
  .hint-box {
    background: #fffbeb; border-left: 3px solid #f59e0b;
    border-radius: 8px; padding: .7rem 1rem; margin: .3rem 0; font-size: .9rem;
  }
  .badge {
    display: inline-block; padding: .2rem .7rem; border-radius: 20px;
    font-size: .78rem; font-weight: 700; margin-right: .4rem;
  }
  .badge-comp { background: #e0e7ff; color: #4f46e5; }
  .badge-diff { background: #fef3c7; color: #b45309; }
</style>
""", unsafe_allow_html=True)

# ── Session State ─────────────────────────────────────────────────────────────
def init():
    defaults = {
        "page": "home",
        "session_id": None,
        "user_name": "",
        "job_role": "",
        "questions": [],
        "q_index": 0,
        "answers": [],
        "timer_start": None,
        "time_limit": 120,
        "last_score": None,
        "report": None,
        "done": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎯 HR Interview Simulator")
    st.markdown("**PRJ-026 · GenAI · Careers**")
    st.markdown("---")
    for label, page in [("🏠 Home", "home"), ("🎤 Practice", "practice"), ("📈 History", "history")]:
        if st.button(label, use_container_width=True,
                     type="primary" if st.session_state.page == page else "secondary"):
            st.session_state.page = page
            st.rerun()
    st.markdown("---")
    st.markdown("### 📋 STAR Method")
    st.info("**S**ituation → **T**ask → **A**ction → **R**esult")
    st.markdown("### 🏆 Scoring")
    st.markdown("- STAR Method **40%**\n- Specificity **20%**\n- Relevance **20%**\n- Clarity **10%**\n- Self-Awareness **10%**")

# ── Score band helper ─────────────────────────────────────────────────────────
def band(s):
    if s >= 85: return "🌟 Excellent"
    if s >= 70: return "✅ Good"
    if s >= 55: return "📊 Average"
    if s >= 40: return "⚠ Below Average"
    return "❌ Poor"

# ── HOME PAGE ─────────────────────────────────────────────────────────────────
if st.session_state.page == "home":
    st.markdown("""
    <div class="main-header">
      <h1>🎯 HR Interview Simulator</h1>
      <p style="font-size:1.1rem;opacity:.9">Master behavioral interviews with AI-powered coaching and rubric-based scoring</p>
    </div>""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Questions", "30+")
    c2.metric("Competencies", "6")
    c3.metric("Rubric Criteria", "5")
    c4.metric("Mode", "AI Powered")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🚀 How It Works")
        st.markdown("""
1. Enter your name and target job role
2. Answer behavioral questions using STAR method
3. Get instant rubric-based scoring
4. Review AI-generated better answers
5. Track your progress over time
        """)
        if st.button("▶ Start Practice Interview", type="primary", use_container_width=True):
            st.session_state.page = "practice"
            st.rerun()
    with col2:
        st.markdown("### 🏆 Competencies")
        for c in ["Leadership","Teamwork","Problem Solving","Communication","Adaptability","Conflict Resolution"]:
            st.markdown(f"✦ **{c}**")

# ── PRACTICE PAGE ─────────────────────────────────────────────────────────────
elif st.session_state.page == "practice":

    # ── Setup ──────────────────────────────────────────────────────────────────
    if not st.session_state.session_id:
        st.markdown("## 🎤 Start Your Practice Interview")
        with st.form("setup"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Your Name", placeholder="e.g. Alex Johnson")
            role = c2.text_input("Target Job Role", placeholder="e.g. Product Manager")
            count = st.slider("Number of Questions", 1, 10, 5)
            go = st.form_submit_button("🚀 Start Interview", type="primary", use_container_width=True)
        if go:
            if not name.strip() or not role.strip():
                st.error("Please enter your name and job role.")
            else:
                import uuid
                qs = question_service.get_random_session_questions(role.strip(), count=count)
                st.session_state.session_id = str(uuid.uuid4())
                st.session_state.user_name = name.strip()
                st.session_state.job_role = role.strip()
                st.session_state.questions = qs
                st.session_state.q_index = 0
                st.session_state.answers = []
                st.session_state.last_score = None
                st.session_state.done = False
                st.session_state.timer_start = time.time()
                st.session_state.time_limit = 120
                st.rerun()

    # ── Show score from last answer ────────────────────────────────────────────
    elif st.session_state.last_score is not None and not st.session_state.done:
        sc = st.session_state.last_score
        st.markdown("## 📊 Answer Scored")
        col1, col2 = st.columns([1, 2])
        with col1:
            score = sc["overall_score"]
            st.metric("Overall Score", f"{score:.1f}/100")
            st.markdown(f"**{band(score)}**")
            st.progress(score / 100)
        with col2:
            st.markdown("**Rubric Breakdown:**")
            for r in sc.get("rubric_scores", []):
                pct = r["score"] / r["max_score"] if r["max_score"] > 0 else 0
                st.markdown(f"**{r['criteria']}** — {r['score']:.1f}/{r['max_score']:.0f}")
                st.progress(pct)
                st.caption(r["feedback"])

        st.markdown('<div class="score-box">', unsafe_allow_html=True)
        st.markdown(f"**💬 Feedback:** {sc.get('feedback','')}")
        st.markdown('</div>', unsafe_allow_html=True)

        if sc.get("better_answer"):
            with st.expander("💡 See Suggested Better Answer"):
                st.markdown('<div class="better-box">', unsafe_allow_html=True)
                st.markdown(sc["better_answer"])
                st.markdown('</div>', unsafe_allow_html=True)

        idx = st.session_state.q_index
        total = len(st.session_state.questions)
        if idx >= total:
            if st.button("🏁 View Final Report", type="primary", use_container_width=True):
                st.session_state.done = True
                st.session_state.last_score = None
                st.rerun()
        else:
            if st.button(f"Next Question ({idx+1}/{total}) →", type="primary", use_container_width=True):
                st.session_state.last_score = None
                st.session_state.timer_start = time.time()
                st.rerun()

    # ── Final Report ───────────────────────────────────────────────────────────
    elif st.session_state.done:
        st.markdown("## 🏆 Interview Complete!")
        answers = st.session_state.answers
        if answers:
            scores = [a["score"] for a in answers]
            overall = sum(scores) / len(scores)
            st.metric("Overall Score", f"{overall:.1f}/100")
            st.progress(overall / 100)
            st.markdown(f"### {band(overall)}")

            c1, c2, c3 = st.columns(3)
            c1.metric("Questions", len(answers))
            c2.metric("Avg Score", f"{overall:.1f}")
            c3.metric("Best Score", f"{max(scores):.1f}")

            # Competency breakdown
            comp_map = {}
            for a in answers:
                c = a.get("competency", "General")
                comp_map.setdefault(c, []).append(a["score"])
            st.markdown("### 🏆 Competency Scores")
            cols = st.columns(len(comp_map))
            for i, (comp, sc_list) in enumerate(comp_map.items()):
                avg = sum(sc_list) / len(sc_list)
                cols[i].metric(comp, f"{avg:.1f}")

            # Per-question details
            st.markdown("### 📝 Question Details")
            for i, a in enumerate(answers, 1):
                with st.expander(f"Q{i}: {a['question'][:70]}... | Score: {a['score']:.1f}/100"):
                    st.markdown(f"**Your Answer:** {a['answer'][:300]}...")
                    st.markdown(f"**Feedback:** {a.get('feedback','')}")
                    if a.get("better_answer"):
                        st.markdown("**💡 Better Answer:**")
                        st.markdown(a["better_answer"][:500] + "...")

        col1, col2 = st.columns(2)
        if col1.button("🔄 Practice Again", type="primary", use_container_width=True):
            for k in ["session_id","questions","q_index","answers","last_score","done","report"]:
                st.session_state[k] = None if k == "session_id" else ([] if k == "answers" else (0 if k == "q_index" else False))
            st.rerun()
        if col2.button("📈 View History", use_container_width=True):
            st.session_state.page = "history"
            st.rerun()

    # ── Active Question ────────────────────────────────────────────────────────
    else:
        idx = st.session_state.q_index
        questions = st.session_state.questions
        if idx >= len(questions):
            st.session_state.done = True
            st.rerun()

        q = questions[idx]
        total = len(questions)

        # Progress
        st.progress((idx) / total)
        st.markdown(f"**Question {idx+1} of {total}** | 👤 {st.session_state.user_name} | 💼 {st.session_state.job_role}")

        # Timer
        elapsed = int(time.time() - (st.session_state.timer_start or time.time()))
        remaining = max(0, st.session_state.time_limit - elapsed)
        color = "🔴" if remaining < 30 else "🟡" if remaining < 60 else "🟢"
        st.markdown(f"### {color} ⏱ {remaining // 60:02d}:{remaining % 60:02d} remaining")

        # Question
        st.markdown(f"""
        <div class="question-box">
          <span class="badge badge-comp">{q['competency']}</span>
          <span class="badge badge-diff">{q['difficulty'].upper()}</span>
          <h3 style="margin-top:.8rem">{q['text']}</h3>
        </div>""", unsafe_allow_html=True)

        # STAR hints
        with st.expander("💡 Show STAR Method Hints"):
            hints = q.get("star_hints", {})
            for part, hint in hints.items():
                st.markdown(f'<div class="hint-box"><strong>{part.upper()}:</strong> {hint}</div>', unsafe_allow_html=True)

        # Answer form
        with st.form(f"answer_{idx}"):
            answer = st.text_area("Your Answer", height=220,
                placeholder="Use the STAR method: Situation → Task → Action → Result...\n\nBe specific — include numbers, timeframes, and measurable outcomes.")
            c1, c2 = st.columns([3, 1])
            submitted = c1.form_submit_button("✅ Submit Answer", type="primary", use_container_width=True)
            skipped = c2.form_submit_button("⏭ Skip", use_container_width=True)

        if submitted and answer.strip():
            time_taken = int(time.time() - (st.session_state.timer_start or time.time()))
            with st.spinner("Scoring your answer..."):
                result = scoring_service.score_answer(q, answer.strip(), time_taken)
                better = llm_service.generate_better_answer(q["text"], answer.strip(), result["rubric_scores"])

            st.session_state.answers.append({
                "question": q["text"],
                "answer": answer.strip(),
                "score": result["overall_score"],
                "feedback": result.get("feedback", ""),
                "better_answer": better,
                "competency": q.get("competency", "General"),
            })
            result["better_answer"] = better
            st.session_state.last_score = result
            st.session_state.q_index = idx + 1
            st.rerun()
        elif submitted:
            st.warning("Please write your answer before submitting.")
        elif skipped:
            st.session_state.q_index = idx + 1
            st.session_state.timer_start = time.time()
            st.rerun()

# ── HISTORY PAGE ──────────────────────────────────────────────────────────────
elif st.session_state.page == "history":
    st.markdown("## 📈 History Dashboard")
    answers = st.session_state.get("answers", [])
    if not answers:
        st.info("No sessions yet. Complete a practice interview to see your history here.")
        if st.button("▶ Start Practice", type="primary"):
            st.session_state.page = "practice"
            st.rerun()
    else:
        scores = [a["score"] for a in answers]
        c1, c2, c3 = st.columns(3)
        c1.metric("Questions Answered", len(answers))
        c2.metric("Average Score", f"{sum(scores)/len(scores):.1f}")
        c3.metric("Best Score", f"{max(scores):.1f}")

        st.markdown("### 📉 Score Trend")
        import pandas as pd
        df = pd.DataFrame({"Question": [f"Q{i+1}" for i in range(len(scores))], "Score": scores})
        st.line_chart(df.set_index("Question"))

        st.markdown("### 📋 Answer History")
        for i, a in enumerate(answers, 1):
            with st.expander(f"Q{i}: {a['question'][:60]}... | {a['score']:.1f}/100"):
                st.markdown(f"**Score:** {a['score']:.1f}/100 — {band(a['score'])}")
                st.markdown(f"**Competency:** {a.get('competency','')}")
                st.markdown(f"**Feedback:** {a.get('feedback','')}")
