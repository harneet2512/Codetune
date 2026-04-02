/**
 * ToolTune Playground — Main Application
 *
 * Hash-based SPA routing with three views:
 *   #playground (default), #eval, #about
 */

import { renderFlowchart } from './flowchart.js';
import { renderRawTrace } from './trace.js';
import { renderVerdictPanel } from './verdict.js';
import { renderEvalStats, renderEvalBars, renderEvalTable, renderEvalFailures, renderEvalLoop } from './eval.js';

// ================================================================
// Constants
// ================================================================

const MODELS = ['base', 'sft', 'grpo'];
const PAGES = ['playground', 'eval', 'about'];
const $ = (id) => document.getElementById(id);

// ================================================================
// State
// ================================================================

const state = {
  page: 'playground',
  tasks: [],
  tasksFull: [],      // full task objects with traces (for eval)
  traces: {},
  stats: {},
  activeTaskId: null,
  activeModel: 'grpo',
  activeNodeId: null,
  playing: false,
  playTimer: null,
  visibleCount: 0,
  evalLoaded: false,
};

// ================================================================
// Utilities
// ================================================================

async function fetchJson(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}

function task() { return state.tasks.find((t) => t.id === state.activeTaskId); }

function trace(m) {
  return state.traces[`${state.activeTaskId}:${m || state.activeModel}`]?.trace;
}

function verdictCls(v) { return v === 'correct' ? 'correct' : v === 'partial' ? 'partial' : 'fail'; }
function verdictText(v) { return v === 'correct' ? 'PASS' : v === 'partial' ? 'PARTIAL' : 'FAIL'; }

function difficultyBadge(d) {
  const lower = (d || '').toLowerCase();
  if (lower === 'hard') return 'badge badge--hard';
  if (lower === 'medium') return 'badge badge--medium';
  if (lower === 'easy') return 'badge badge--easy';
  return 'badge';
}

// ================================================================
// Router
// ================================================================

function getHash() {
  const h = window.location.hash.replace('#', '') || 'playground';
  return PAGES.includes(h) ? h : 'playground';
}

function navigate(page) {
  state.page = page;

  // Toggle page visibility
  for (const p of PAGES) {
    const el = $(`page-${p}`);
    if (el) {
      el.style.display = p === page ? '' : 'none';
    }
  }

  // Update nav links
  document.querySelectorAll('.topnav-link').forEach((link) => {
    link.classList.toggle('active', link.dataset.nav === page);
  });

  // Lazy-load eval data
  if (page === 'eval' && !state.evalLoaded) {
    loadEval();
  }
}

function initRouter() {
  window.addEventListener('hashchange', () => navigate(getHash()));
  navigate(getHash());
}

// ================================================================
// Data Loading
// ================================================================

async function loadTasks() {
  const d = await fetchJson('/api/tasks');
  state.tasks = d.tasks;
  state.activeTaskId = d.tasks[0]?.id ?? null;
  $('taskCount').textContent = d.tasks.length;
}

async function loadTrace(taskId, model) {
  const key = `${taskId}:${model}`;
  if (!state.traces[key]) {
    state.traces[key] = await fetchJson(`/api/traces/${taskId}/${model}`);
  }
  return state.traces[key];
}

async function warmTask() {
  if (!state.activeTaskId) return;
  await Promise.all(MODELS.map((m) => loadTrace(state.activeTaskId, m)));
}

async function loadEval() {
  try {
    const [statsData, evalData] = await Promise.all([
      fetchJson('/api/stats'),
      fetchJson('/api/eval'),
    ]);
    state.stats = statsData;
    state.tasksFull = evalData.tasks || [];
    state.evalLoaded = true;
    renderEvalPage();
  } catch (err) {
    console.error('Failed to load eval data:', err);
  }
}

// ================================================================
// Playground Rendering
// ================================================================

function renderSidebar() {
  const list = $('taskList');
  list.innerHTML = '';

  // Group tasks by category
  const groups = {};
  for (const t of state.tasks) {
    if (!groups[t.category]) groups[t.category] = [];
    groups[t.category].push(t);
  }

  for (const [category, tasks] of Object.entries(groups)) {
    // Group label
    const label = document.createElement('div');
    label.className = 'sidebar-group-label';
    label.innerHTML = `<span class="sidebar-group-arrow">\u25BE</span> ${category}`;

    const items = document.createElement('div');
    items.className = 'sidebar-group-items';

    label.addEventListener('click', () => {
      label.classList.toggle('collapsed');
      items.classList.toggle('hidden');
    });

    for (const t of tasks) {
      const btn = document.createElement('button');
      btn.className = `task-item${t.id === state.activeTaskId ? ' active' : ''}`;

      const dots = MODELS.map((m) => {
        const key = `${t.id}:${m}`;
        const cached = state.traces[key]?.trace;
        const v = cached?.verdict || 'fail';
        return `<span class="task-dot ${verdictCls(v)}"></span>`;
      }).join('');

      btn.innerHTML = `
        <div class="task-item-dots">${dots}</div>
        <div class="task-item-text">
          <p class="task-item-title">${t.title}</p>
          <p class="task-item-cat">${t.difficulty}</p>
        </div>`;

      btn.addEventListener('click', async () => {
        state.activeTaskId = t.id;
        state.activeNodeId = null;
        stopPlay();
        await warmTask();
        renderPlayground();
      });

      items.appendChild(btn);
    }

    list.appendChild(label);
    list.appendChild(items);
  }
}

function renderTaskHeader() {
  const t = task();
  if (!t) return;
  $('taskTitle').textContent = t.title;
  $('taskPrompt').textContent = t.prompt;
  $('taskDifficulty').textContent = t.difficulty;
  $('taskDifficulty').className = difficultyBadge(t.difficulty);
  $('taskCategory').textContent = t.category;
}

function renderModelTabs() {
  const tabs = $('modelTabs');
  tabs.innerHTML = '';

  for (const m of MODELS) {
    const tr = trace(m);
    const btn = document.createElement('button');
    btn.className = `model-tab${state.activeModel === m ? ' active' : ''}`;
    btn.dataset.model = m;

    const v = tr?.verdict || 'fail';
    btn.innerHTML = `${m.toUpperCase()} <span class="tab-chip ${verdictCls(v)}">${verdictText(v)}</span>`;

    btn.addEventListener('click', () => {
      state.activeModel = m;
      state.activeNodeId = null;
      stopPlay();
      renderModelTabs();
      renderTraceView();
    });

    tabs.appendChild(btn);
  }
}

function renderTraceView() {
  const tr = trace();
  if (!tr) return;

  const nodes = state.playing ? tr.nodes.slice(0, state.visibleCount) : tr.nodes;

  renderFlowchart($('flowchart'), nodes, (node, index) => {
    state.activeNodeId = node.id;
    updateInspector(node, index, nodes.length);
    // Re-render flowchart to update active state without re-animating
    renderFlowchart($('flowchart'), nodes, (n, i) => {
      state.activeNodeId = n.id;
      updateInspector(n, i, nodes.length);
      renderFlowchart($('flowchart'), nodes, arguments.callee, { activeNodeId: state.activeNodeId });
    }, { activeNodeId: state.activeNodeId });
  }, { activeNodeId: state.activeNodeId });

  renderRawTrace($('rawTrace'), tr.raw_trace);
  renderVerdictPanel($('verdictCard'), tr);

  // Auto-select last or current node
  const sel = nodes.find((n) => n.id === state.activeNodeId) || nodes[nodes.length - 1];
  if (sel) {
    state.activeNodeId = sel.id;
    updateInspector(sel, nodes.indexOf(sel), nodes.length);
  }
}

function updateInspector(node, index, total) {
  if (!node) {
    $('inspectorTitle').textContent = 'Select a step';
    $('inspectorMeta').textContent = '';
    $('inspectorContent').textContent = '';
    return;
  }
  $('inspectorTitle').textContent = node.title;
  $('inspectorMeta').textContent = `Step ${index + 1} / ${total}  \u00b7  ${(node.type || '').replace(/_/g, ' ')}`;
  let content = node.content || '';
  if (node.decision) content += `\n\nDecision: ${node.decision}`;
  $('inspectorContent').textContent = content;
}

// ================================================================
// Playback
// ================================================================

function startPlay() {
  stopPlay();
  state.playing = true;
  state.visibleCount = 0;
  $('playLabel').textContent = 'Stop';
  $('playBtn').classList.add('playing');

  const tr = trace();
  if (!tr) return;

  state.playTimer = setInterval(() => {
    state.visibleCount++;
    if (state.visibleCount <= tr.nodes.length) {
      state.activeNodeId = tr.nodes[state.visibleCount - 1]?.id;
    }
    renderTraceView();
    if (state.visibleCount >= tr.nodes.length) {
      stopPlay();
    }
  }, 700);
}

function stopPlay() {
  if (state.playTimer) clearInterval(state.playTimer);
  state.playTimer = null;
  state.playing = false;
  $('playLabel').textContent = 'Play';
  $('playBtn').classList.remove('playing');
}

// ================================================================
// Playground full render
// ================================================================

function renderPlayground() {
  renderSidebar();
  renderTaskHeader();
  renderModelTabs();
  renderTraceView();
}

// ================================================================
// Eval Dashboard
// ================================================================

function renderEvalPage() {
  renderEvalStats($('evalStatsRow'), state.stats);
  renderEvalBars($('evalBars'), state.stats);
  renderEvalTable($('evalTable'), state.tasksFull);
  renderEvalFailures($('evalFailures'), state.tasksFull);
  renderEvalLoop($('evalLoop'));
}

// ================================================================
// Init
// ================================================================

function bind() {
  $('playBtn').addEventListener('click', () => {
    if (state.playing) stopPlay();
    else startPlay();
    renderTraceView();
  });
}

async function init() {
  bind();
  initRouter();
  await loadTasks();
  await warmTask();
  renderPlayground();

  // Preload all traces for sidebar dots
  preloadAllTraces();
}

async function preloadAllTraces() {
  for (const t of state.tasks) {
    for (const m of MODELS) {
      const key = `${t.id}:${m}`;
      if (!state.traces[key]) {
        try {
          state.traces[key] = await fetchJson(`/api/traces/${t.id}/${m}`);
        } catch { /* ignore */ }
      }
    }
  }
  // Re-render sidebar with correct dots
  renderSidebar();
}

init().catch((err) => {
  console.error('Init failed:', err);
  $('taskTitle').textContent = 'Error loading data';
  $('taskPrompt').textContent = err.message;
});
