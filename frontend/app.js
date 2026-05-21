/**
 * HR Interview Simulator — Frontend JS
 * PRJ-026 | Connects to FastAPI backend at localhost:8000
 */

const API = 'http://localhost:8000/api/v1';

// ── State ─────────────────────────────────────────────────────────────────────
const state = {
  sessionId: null,
  userName: '',
  jobRole: '',
  currentQuestion: null,
  questionNumber: 1,
  totalQuestions: 5,
  timerInterval: null,
  timerSeconds: 120,
  timerMax: 120,
  answerScores: [],
};

// ── API Helpers ───────────────────────────────────────────────────────────────
async function apiPost(endpoint, data) {
  try {
    const res = await fetch(`${API}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return await res.json();
  } catch (e) {
    if (e.message.includes('Failed to fetch')) {
      showToast('Cannot connect to backend. Start the FastAPI server first.', 'error');
    } else {
      showToast(`Error: ${e.message}`, 'error');
    }
    return null;
  }
}

async function apiGet(endpoint, params = {}) {
  try {
    const url = new URL(`${API}${endpoint}`);
    Object.entries(params).forEach(([k, v]) => v && url.searchParams.set(k, v));
    const res = await fetch(url.toString());
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return await res.json();
  } catch (e) {
    if (e.message.includes('Failed to fetch')) {
      showToast('Cannot connect to backend. Start the FastAPI server first.', 'error');
    } else {
      showToast(`Error: ${e.message}`, 'error');
    }
    return null;
  }
}

// ── Navigation ────────────────────────────────────────────────────────────────
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  const page = document.getElementById(`page-${name}`);
  if (page) page.classList.add('active');
  const link = document.querySelector(`[data-page="${name}"]`);
  if (link) link.classList.add('active');
  window.scrollTo({ top: 0, behavior: 'smooth' });

  if (name === 'history') loadHistory();
}

// Nav link clicks
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    showPage(link.dataset.page);
    document.querySelector('.nav-links').classList.remove('open');
  });
});

// Hamburger
document.getElementById('hamburger').addEventListener('click', () => {
  document.querySelector('.nav-links').classList.toggle('open');
});

// ── Toast ─────────────────────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `toast ${type}`;
  t.classList.remove('hidden');
  clearTimeout(t._timeout);
  t._timeout = setTimeout(() => t.classList.add('hidden'), 3500);
}

// ── Timer ─────────────────────────────────────────────────────────────────────
function startTimer(seconds) {
  clearInterval(state.timerInterval);
  state.timerSeconds = seconds;
  state.timerMax = seconds;
  updateTimerUI();
  state.timerInterval = setInterval(() => {
    state.timerSeconds--;
    updateTimerUI();
    if (state.timerSeconds <= 0) {
      clearInterval(state.timerInterval);
      showToast('Time is up! Submit your answer.', 'error');
    }
  }, 1000);
}

function stopTimer() {
  clearInterval(state.timerInterval);
}

function getElapsed() {
  return state.timerMax - state.timerSeconds;
}

function updateTimerUI() {
  const s = state.timerSeconds;
  const m = Math.floor(s / 60);
  const sec = s % 60;
  document.getElementById('timer-display').textContent =
    `${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`;

  const pct = s / state.timerMax;
  const circumference = 2 * Math.PI * 45;
  const offset = circumference * (1 - pct);
  const circle = document.getElementById('timer-circle');
  circle.style.strokeDashoffset = offset;
  circle.style.stroke = s < 30 ? '#ef4444' : s < 60 ? '#f59e0b' : '#22c55e';
}

// ── Session Start ─────────────────────────────────────────────────────────────
document.getElementById('btn-start-session').addEventListener('click', async () => {
  const name = document.getElementById('input-name').value.trim();
  const role = document.getElementById('input-role').value.trim();
  const count = parseInt(document.getElementById('q-count').value);
  const errEl = document.getElementById('setup-error');

  if (!name || !role) {
    errEl.textContent = 'Please enter your name and target job role.';
    errEl.classList.remove('hidden');
    return;
  }
  errEl.classList.add('hidden');

  const btn = document.getElementById('btn-start-session');
  btn.textContent = '⏳ Starting...';
  btn.disabled = true;

  const result = await apiPost('/sessions/start', {
    user_name: name, job_role: role, question_count: count,
  });

  btn.textContent = '🚀 Start Interview';
  btn.disabled = false;

  if (!result) return;

  state.sessionId = result.id;
  state.userName = name;
  state.jobRole = role;
  state.totalQuestions = result.question_count;
  state.questionNumber = 1;
  state.answerScores = [];

  document.getElementById('session-user').textContent = `${name} · ${role}`;
  await loadNextQuestion();
  document.getElementById('setup-panel').classList.add('hidden');
  document.getElementById('interview-panel').classList.remove('hidden');
  document.getElementById('score-panel').classList.add('hidden');
  document.getElementById('report-panel').classList.add('hidden');
});

// ── Load Next Question ────────────────────────────────────────────────────────
async function loadNextQuestion() {
  const data = await apiGet(`/sessions/${state.sessionId}/next-question`);
  if (!data) return;

  state.currentQuestion = data.question;
  state.questionNumber = data.question_number;

  // Progress
  const pct = ((state.questionNumber - 1) / state.totalQuestions) * 100;
  document.getElementById('progress-bar').style.width = `${pct}%`;
  document.getElementById('q-progress').textContent =
    `Question ${state.questionNumber} of ${state.totalQuestions}`;

  // Question content
  document.getElementById('question-text').textContent = data.question.text;
  document.getElementById('q-competency').textContent = data.question.competency;
  document.getElementById('q-difficulty').textContent = data.question.difficulty.toUpperCase();

  // STAR hints
  const hints = data.question.star_hints || {};
  document.getElementById('hint-s').textContent = hints.situation || '';
  document.getElementById('hint-t').textContent = hints.task || '';
  document.getElementById('hint-a').textContent = hints.action || '';
  document.getElementById('hint-r').textContent = hints.result || '';
  document.getElementById('star-hints').classList.add('hidden');

  // Reset answer
  document.getElementById('answer-input').value = '';
  document.getElementById('word-count').textContent = '0 words';

  // Timer
  startTimer(data.time_limit || 120);
}

// Word count
document.getElementById('answer-input').addEventListener('input', function () {
  const words = this.value.trim().split(/\s+/).filter(Boolean).length;
  document.getElementById('word-count').textContent = `${words} word${words !== 1 ? 's' : ''}`;
});

// STAR hints toggle
function toggleHints() {
  const el = document.getElementById('star-hints');
  el.classList.toggle('hidden');
}

// ── Submit Answer ─────────────────────────────────────────────────────────────
document.getElementById('btn-submit').addEventListener('click', async () => {
  const answer = document.getElementById('answer-input').value.trim();
  if (!answer) { showToast('Please write your answer first.', 'error'); return; }

  stopTimer();
  const timeTaken = getElapsed();

  const btn = document.getElementById('btn-submit');
  btn.textContent = '⏳ Scoring...';
  btn.disabled = true;

  const result = await apiPost(`/answers/${state.sessionId}/submit`, {
    question_id: state.currentQuestion.id,
    answer_text: answer,
    time_taken: timeTaken,
  });

  btn.textContent = '✅ Submit Answer';
  btn.disabled = false;

  if (!result) return;

  state.answerScores.push(result);
  renderScorePanel(result);

  document.getElementById('interview-panel').classList.add('hidden');
  document.getElementById('score-panel').classList.remove('hidden');
});

// Skip
document.getElementById('btn-skip').addEventListener('click', async () => {
  stopTimer();
  if (state.questionNumber >= state.totalQuestions) {
    await finishSession();
  } else {
    await loadNextQuestion();
  }
});

// Next question button
document.getElementById('btn-next-question').addEventListener('click', async () => {
  document.getElementById('score-panel').classList.add('hidden');
  if (state.questionNumber >= state.totalQuestions) {
    await finishSession();
  } else {
    await loadNextQuestion();
    document.getElementById('interview-panel').classList.remove('hidden');
  }
});

// ── Score Panel Render ────────────────────────────────────────────────────────
function renderScorePanel(result) {
  const score = result.overall_score || 0;

  // Circle
  const circumference = 2 * Math.PI * 54;
  const offset = circumference * (1 - score / 100);
  const fill = document.getElementById('score-circle-fill');
  fill.style.strokeDashoffset = offset;
  fill.style.stroke = scoreColor(score);

  document.getElementById('score-number').childNodes[0].textContent = score.toFixed(1);
  document.getElementById('score-band').textContent = scoreBand(score);

  // Rubric bars
  const container = document.getElementById('rubric-breakdown');
  container.innerHTML = '';
  (result.rubric_scores || []).forEach(r => {
    const pct = r.max_score > 0 ? (r.score / r.max_score) * 100 : 0;
    container.innerHTML += `
      <div class="rubric-row">
        <div class="rubric-label">
          <span>${r.criteria}</span>
          <span>${r.score.toFixed(1)}/${r.max_score}</span>
        </div>
        <div class="rubric-bar-wrap">
          <div class="rubric-bar" style="width:${pct}%;background:${scoreColor(pct)}"></div>
        </div>
        <div class="rubric-feedback">${r.feedback}</div>
      </div>`;
  });

  // Feedback
  document.getElementById('feedback-text').textContent = result.feedback || 'No feedback available.';

  // Better answer
  const baSection = document.getElementById('better-answer-section');
  const baText = document.getElementById('better-answer-text');
  if (result.better_answer) {
    baText.textContent = result.better_answer;
    baSection.classList.remove('hidden');
  } else {
    baSection.classList.add('hidden');
  }

  // Next button label
  const nextBtn = document.getElementById('btn-next-question');
  nextBtn.textContent = state.questionNumber >= state.totalQuestions
    ? '🏁 View Final Report' : 'Next Question →';
}

function scoreColor(pct) {
  if (pct >= 85) return '#22c55e';
  if (pct >= 70) return '#84cc16';
  if (pct >= 55) return '#eab308';
  if (pct >= 40) return '#f97316';
  return '#ef4444';
}

function scoreBand(score) {
  if (score >= 85) return '🌟 Excellent';
  if (score >= 70) return '✅ Good';
  if (score >= 55) return '📊 Average';
  if (score >= 40) return '⚠ Below Average';
  return '❌ Poor';
}

// ── Finish Session & Report ───────────────────────────────────────────────────
async function finishSession() {
  await apiPost(`/sessions/${state.sessionId}/complete`, {});
  const report = await apiGet(`/reports/${state.sessionId}`);
  if (!report) return;

  renderReport(report);
  document.getElementById('score-panel').classList.add('hidden');
  document.getElementById('interview-panel').classList.add('hidden');
  document.getElementById('report-panel').classList.remove('hidden');
}

function renderReport(report) {
  const overall = report.overall_score || 0;
  const compScores = (report.competency_scores || [])
    .map(c => `<div class="comp-score-card"><div class="comp-score-val">${c.score.toFixed(1)}</div><div class="comp-score-lbl">${c.competency}</div></div>`)
    .join('');

  const strengths = (report.strengths || [])
    .map(s => `<div class="si-item">✓ ${s}</div>`).join('');
  const improvements = (report.improvements || [])
    .map(i => `<div class="si-item">→ ${i}</div>`).join('');

  const details = (report.answer_details || []).map((d, i) => `
    <div class="question-item" style="margin-bottom:.8rem">
      <div class="question-item-header" onclick="toggleDetail(this)">
        <span class="question-item-text">Q${i+1}: ${d.question_text.substring(0,80)}...</span>
        <span class="badge badge-competency">${d.overall_score.toFixed(1)}/100</span>
      </div>
      <div class="question-item-body">
        <p style="font-size:.88rem;color:var(--text-muted);margin-bottom:.5rem"><strong>Your answer:</strong> ${d.answer_text.substring(0,200)}...</p>
        <p style="font-size:.88rem;margin-bottom:.5rem"><strong>Feedback:</strong> ${d.feedback || 'N/A'}</p>
        ${d.better_answer ? `<div class="better-answer-box" style="margin-top:.5rem;font-size:.83rem">${d.better_answer.substring(0,400)}...</div>` : ''}
      </div>
    </div>`).join('');

  document.getElementById('report-content').innerHTML = `
    <div class="report-overall">
      <div class="report-score-big" style="color:${scoreColor(overall)}">${overall.toFixed(1)}</div>
      <div class="report-band-big">${scoreBand(overall)}</div>
    </div>
    <div class="report-grid">
      <div class="report-metric"><div class="report-metric-val">${report.total_questions}</div><div class="report-metric-lbl">Questions</div></div>
      <div class="report-metric"><div class="report-metric-val">${report.duration_minutes} min</div><div class="report-metric-lbl">Duration</div></div>
      <div class="report-metric"><div class="report-metric-val">${report.job_role}</div><div class="report-metric-lbl">Role</div></div>
    </div>
    <h3 style="margin-bottom:.8rem">Competency Scores</h3>
    <div class="comp-scores-grid">${compScores}</div>
    <div class="strengths-improvements">
      <div class="si-card strengths"><h4>✅ Strengths</h4>${strengths}</div>
      <div class="si-card improvements"><h4>🔧 Improve</h4>${improvements}</div>
    </div>
    <h3 style="margin-bottom:.8rem">Question Details</h3>
    ${details}`;
}

function toggleDetail(header) {
  const body = header.nextElementSibling;
  body.classList.toggle('open');
}

function restartInterview() {
  state.sessionId = null;
  state.answerScores = [];
  document.getElementById('report-panel').classList.add('hidden');
  document.getElementById('setup-panel').classList.remove('hidden');
  document.getElementById('input-name').value = '';
  document.getElementById('input-role').value = '';
}

// ── History Page ──────────────────────────────────────────────────────────────
async function loadHistory() {
  const filter = document.getElementById('history-filter')?.value || '';
  const params = filter ? { user_name: filter } : {};

  const stats = await apiGet('/history/stats', params);
  if (stats) {
    document.getElementById('stats-grid').innerHTML = `
      <div class="stat-grid-card"><div class="stat-grid-val">${stats.total_sessions}</div><div class="stat-grid-lbl">Total Sessions</div></div>
      <div class="stat-grid-card"><div class="stat-grid-val">${stats.avg_score.toFixed(1)}</div><div class="stat-grid-lbl">Avg Score</div></div>
      <div class="stat-grid-card"><div class="stat-grid-val">${stats.best_score.toFixed(1)}</div><div class="stat-grid-lbl">Best Score</div></div>
      <div class="stat-grid-card"><div class="stat-grid-val">${stats.sessions_this_week}</div><div class="stat-grid-lbl">This Week</div></div>`;

    // Trend chart
    const trend = stats.score_trend || [];
    if (trend.length > 0) renderTrendChart(trend);
  }

  const sessions = await apiGet('/history/sessions', params);
  const list = document.getElementById('sessions-list');
  if (!sessions || !sessions.sessions?.length) {
    list.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:2rem">No sessions found. Complete an interview to see history.</p>';
    return;
  }
  list.innerHTML = sessions.sessions.map(s => {
    const score = s.overall_score != null ? `${s.overall_score.toFixed(1)}/100` : 'N/A';
    const statusClass = `status-${s.status}`;
    const date = new Date(s.start_time).toLocaleDateString();
    return `
      <div class="session-item">
        <div class="session-info">
          <h4>${s.user_name} — ${s.job_role}</h4>
          <p>${date} · ${s.question_count} questions · ${s.duration_minutes || '?'} min</p>
        </div>
        <div style="display:flex;align-items:center;gap:1rem">
          <span class="session-score" style="color:${scoreColor(s.overall_score||0)}">${score}</span>
          <span class="session-status ${statusClass}">${s.status.toUpperCase()}</span>
        </div>
      </div>`;
  }).join('');
}

function renderTrendChart(trend) {
  const canvas = document.getElementById('trend-chart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.offsetWidth || 600;
  const H = 80;
  canvas.width = W; canvas.height = H;
  ctx.clearRect(0, 0, W, H);

  const scores = trend.map(t => t.score);
  const min = Math.min(...scores) - 5;
  const max = Math.max(...scores) + 5;
  const xStep = W / (trend.length - 1 || 1);

  ctx.beginPath();
  ctx.strokeStyle = '#6366f1';
  ctx.lineWidth = 2.5;
  ctx.lineJoin = 'round';
  trend.forEach((t, i) => {
    const x = i * xStep;
    const y = H - ((t.score - min) / (max - min)) * (H - 10) - 5;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Dots
  trend.forEach((t, i) => {
    const x = i * xStep;
    const y = H - ((t.score - min) / (max - min)) * (H - 10) - 5;
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fillStyle = scoreColor(t.score);
    ctx.fill();
  });
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  showPage('home');
});
