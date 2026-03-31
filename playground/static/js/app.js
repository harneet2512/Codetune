import { renderFlowchart, renderMiniFlow } from './flowchart.js';
import { renderRawTrace } from './trace.js';
import { renderVerdictBar } from './verdict.js';

const MODELS = ['base', 'sft', 'grpo'];
const PANEL_LABELS = { base: 'BASE', sft: 'SFT', grpo: 'GRPO' };

const state = {
  tasks: [],
  models: [],
  traces: {},
  activeTaskId: null,
  activeModel: 'grpo',
  activeNodeId: null,
  autoplayTimer: null,
  autoplayIndex: 0,
  runVersion: 0,
  simulationRunning: false,
  runCompleted: false,
  visibleByModel: { base: 0, sft: 0, grpo: 0 },
};

const els = {
  taskList: document.getElementById('taskList'),
  modelTabs: document.getElementById('modelTabs'),
  taskCount: document.getElementById('taskCount'),
  taskCategory: document.getElementById('taskCategory'),
  taskDifficulty: document.getElementById('taskDifficulty'),
  taskTitle: document.getElementById('taskTitle'),
  promptInput: document.getElementById('promptInput'),
  runStatus: document.getElementById('runStatus'),
  runPromptBtn: document.getElementById('runPromptBtn'),
  resetPromptBtn: document.getElementById('resetPromptBtn'),
  flowchart: document.getElementById('flowchart'),
  rawTracePanel: document.getElementById('rawTracePanel'),
  rawTraceContent: document.getElementById('rawTraceContent'),
  verdictBar: document.getElementById('verdictBar'),
  inspectorTitle: document.getElementById('inspectorTitle'),
  inspectorMeta: document.getElementById('inspectorMeta'),
  inspectorContent: document.getElementById('inspectorContent'),
  activeModelTitle: document.getElementById('activeModelTitle'),
  autoplayBtn: document.getElementById('autoplayBtn'),
  playTraceBtn: document.getElementById('playTraceBtn'),
  toggleRawBtn: document.getElementById('toggleRawBtn'),
  panels: [...document.querySelectorAll('.model-panel')],
};

function verdictClass(verdict) {
  if (verdict === 'correct') return 'success';
  if (verdict === 'partial') return 'partial';
  return 'fail';
}

function verdictLabel(verdict) {
  if (verdict === 'correct') return 'CORRECT';
  if (verdict === 'partial') return 'PARTIAL';
  return 'FAIL';
}

function titleForModel(model) {
  return model === 'base' ? 'BASE trace' : model === 'sft' ? 'SFT trace' : 'GRPO trace';
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Request failed: ${url}`);
  return response.json();
}

async function loadTasks() {
  const payload = await fetchJson('/api/tasks');
  state.tasks = payload.tasks;
  state.models = payload.models;
  state.activeTaskId = payload.tasks[0]?.id ?? null;
  els.taskCount.textContent = `${payload.tasks.length} tasks`;
}

async function loadTrace(taskId, model) {
  const key = `${taskId}:${model}`;
  if (!state.traces[key]) {
    state.traces[key] = await fetchJson(`/api/traces/${taskId}/${model}`);
  }
  return state.traces[key];
}

async function warmCurrentTask() {
  await Promise.all(MODELS.map((model) => loadTrace(state.activeTaskId, model)));
}

function activeTask() {
  return state.tasks.find((item) => item.id === state.activeTaskId);
}

function traceFor(model) {
  return state.traces[`${state.activeTaskId}:${model}`]?.trace;
}

function visibleCountFor(model) {
  const trace = traceFor(model);
  if (!trace) return 0;
  const current = state.visibleByModel[model] || 0;
  if (state.simulationRunning) return Math.min(current, trace.nodes.length);
  if (state.runCompleted) return trace.nodes.length;
  return current;
}

function setPromptFromTask() {
  const task = activeTask();
  if (task) els.promptInput.value = task.prompt;
}

function renderTasks() {
  els.taskList.innerHTML = '';
  state.tasks.forEach((task) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `task-btn${task.id === state.activeTaskId ? ' active' : ''}`;
    button.innerHTML = `<p class="task-btn-title">${task.title}</p><p class="task-btn-meta">${task.category} · ${task.difficulty}</p>`;
    button.addEventListener('click', async () => {
      state.activeTaskId = task.id;
      stopAutoplay(false);
      await warmCurrentTask();
      setPromptFromTask();
      resetRunState();
      renderAll();
    });
    els.taskList.appendChild(button);
  });
}

function renderModelTabs() {
  els.modelTabs.innerHTML = '';
  MODELS.forEach((model) => {
    const trace = traceFor(model);
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.model = model;
    button.className = `model-tab${state.activeModel === model ? ' active' : ''}`;
    button.innerHTML = `<span>${PANEL_LABELS[model]}</span><span class="verdict-chip ${verdictClass(trace?.verdict || 'fail')}">${verdictLabel(trace?.verdict || 'fail')}</span>`;
    button.addEventListener('click', () => {
      state.activeModel = model;
      state.activeNodeId = null;
      renderAll();
    });
    els.modelTabs.appendChild(button);
  });
}

function renderHero() {
  const task = activeTask();
  if (!task) return;
  els.taskCategory.textContent = task.category;
  els.taskDifficulty.textContent = task.difficulty;
  els.taskTitle.textContent = task.title;
}

function renderPanels() {
  MODELS.forEach((model) => {
    const trace = traceFor(model);
    if (!trace) return;

    document.getElementById(`${model}Summary`).textContent = trace.summary;
    const visibleNodes = trace.nodes.slice(0, visibleCountFor(model));
    renderMiniFlow(document.getElementById(`${model}MiniFlow`), visibleNodes, trace.nodes.length);

    const chip = document.getElementById(`${model}VerdictChip`);
    chip.className = `verdict-chip ${verdictClass(trace.verdict)}`;
    chip.textContent = verdictLabel(trace.verdict);

    const stateEl = document.getElementById(`${model}State`);
    const countEl = document.getElementById(`${model}Count`);
    const visible = visibleNodes.length;
    const total = trace.nodes.length;

    if (state.simulationRunning) stateEl.textContent = visible < total ? 'Running' : verdictLabel(trace.verdict);
    else if (state.runCompleted) stateEl.textContent = verdictLabel(trace.verdict);
    else if (visible > 0) stateEl.textContent = 'Paused';
    else stateEl.textContent = 'Idle';

    countEl.textContent = `${visible} / ${total} steps`;
  });

  els.panels.forEach((panel) => {
    panel.classList.toggle('active', panel.dataset.panel === state.activeModel);
    panel.onclick = () => {
      state.activeModel = panel.dataset.panel;
      state.activeNodeId = null;
      renderAll();
    };
  });
}

function updateInspector(node, index, total) {
  if (!node) {
    els.inspectorTitle.textContent = 'Select a node';
    els.inspectorMeta.textContent = 'Trace details appear here.';
    els.inspectorContent.textContent = '';
    return;
  }

  els.inspectorTitle.textContent = node.title;
  els.inspectorMeta.textContent = `Step ${index + 1} of ${total} · ${node.type.replace('_', ' ')}`;
  els.inspectorContent.textContent = node.content + (node.decision ? `\n\nDecision: ${node.decision}` : '');
}

function renderActiveTrace() {
  const trace = traceFor(state.activeModel);
  if (!trace) return;

  const visibleCount = visibleCountFor(state.activeModel);
  const visibleNodes = trace.nodes.slice(0, visibleCount);
  const selectedNode = visibleNodes.find((node) => node.id === state.activeNodeId) || visibleNodes[visibleNodes.length - 1] || null;
  state.activeNodeId = selectedNode?.id ?? null;

  const task = activeTask();
  els.activeModelTitle.textContent = `${titleForModel(state.activeModel)} · ${task?.title || ''}`;

  renderFlowchart(els.flowchart, visibleNodes, (node) => {
    state.activeNodeId = node.id;
    const index = visibleNodes.findIndex((item) => item.id === node.id);
    updateInspector(node, index, visibleNodes.length);
    renderActiveTrace();
  }, { activeNodeId: state.activeNodeId });

  renderRawTrace(els.rawTraceContent, trace.raw_trace);
  renderVerdictBar(els.verdictBar, trace);

  if (selectedNode) updateInspector(selectedNode, visibleNodes.findIndex((node) => node.id === selectedNode.id), visibleNodes.length);
  else updateInspector(null, 0, 0);
}

function renderPanelsAndTrace() {
  renderPanels();
  renderActiveTrace();
}

function renderAll() {
  renderTasks();
  renderModelTabs();
  renderHero();
  renderPanelsAndTrace();
}

function resetRunState() {
  MODELS.forEach((model) => {
    state.visibleByModel[model] = 0;
  });
  state.simulationRunning = false;
  state.runCompleted = false;
  state.activeNodeId = null;
  els.runStatus.textContent = 'Ready';
}

function stopAutoplay(markPaused = true) {
  if (state.autoplayTimer) {
    clearInterval(state.autoplayTimer);
    state.autoplayTimer = null;
  }
  state.autoplayIndex = 0;
  if (markPaused && state.simulationRunning) {
    state.simulationRunning = false;
    state.runCompleted = false;
    els.runStatus.textContent = 'Paused';
  }
  els.autoplayBtn.textContent = 'Autoplay';
  els.playTraceBtn.textContent = 'Play trace';
}

function startSimulation() {
  stopAutoplay(false);
  state.runVersion += 1;
  const runVersion = state.runVersion;
  resetRunState();
  state.simulationRunning = true;
  els.runStatus.textContent = 'Running';
  els.autoplayBtn.textContent = 'Stop';
  els.playTraceBtn.textContent = 'Stop';

  const maxSteps = Math.max(...MODELS.map((model) => traceFor(model)?.nodes.length || 0));
  let tick = 0;

  state.autoplayTimer = window.setInterval(() => {
    if (runVersion !== state.runVersion) return;

    tick += 1;
    let active = false;

    MODELS.forEach((model) => {
      const trace = traceFor(model);
      if (!trace) return;
      if (state.visibleByModel[model] < trace.nodes.length) {
        state.visibleByModel[model] += 1;
        active = true;
      }
    });

    const activeTrace = traceFor(state.activeModel);
    if (activeTrace && state.visibleByModel[state.activeModel] > 0) {
      const index = Math.min(state.visibleByModel[state.activeModel] - 1, activeTrace.nodes.length - 1);
      state.activeNodeId = activeTrace.nodes[index]?.id || null;
    }

    renderPanelsAndTrace();

    if (!active || tick > maxSteps + 2) {
      stopAutoplay(false);
      state.simulationRunning = false;
      state.runCompleted = true;
      MODELS.forEach((model) => {
        const trace = traceFor(model);
        if (trace) state.visibleByModel[model] = trace.nodes.length;
      });
      els.runStatus.textContent = 'Complete';
      renderPanelsAndTrace();
    }
  }, 580);
}

function bindActions() {
  els.toggleRawBtn.addEventListener('click', () => {
    els.rawTracePanel.classList.toggle('hidden');
  });

  els.autoplayBtn.addEventListener('click', () => {
    if (state.autoplayTimer) stopAutoplay(true);
    else startSimulation();
    renderPanelsAndTrace();
  });

  els.playTraceBtn.addEventListener('click', () => {
    if (state.autoplayTimer) stopAutoplay(true);
    else startSimulation();
    renderPanelsAndTrace();
  });

  els.runPromptBtn.addEventListener('click', () => startSimulation());
  els.resetPromptBtn.addEventListener('click', () => {
    setPromptFromTask();
    resetRunState();
    renderAll();
  });
}

async function init() {
  bindActions();
  await loadTasks();
  await warmCurrentTask();
  setPromptFromTask();
  resetRunState();
  renderAll();
}

init().catch((error) => {
  console.error(error);
  els.taskTitle.textContent = 'Failed to load demo';
  els.runStatus.textContent = error.message;
});
