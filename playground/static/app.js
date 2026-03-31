const state = {
  variants: [],
  showcase: [],
  runs: {},
  runOrder: [],
  selectedRunKey: null,
  activePhaseFilter: 'all',
};

async function boot() {
  await Promise.all([loadShowcase(), renderRewardLab(), renderModelCard()]);
  wireControls();
  setProgressionDefaults();
  onExampleChange();
  renderExamplePills();
  resetArena();
}

async function loadShowcase() {
  const showcase = await fetch('/api/showcase').then((res) => res.json());
  state.variants = showcase.variants || [];
  state.showcase = showcase.examples || [];
  fillSelect(document.getElementById('model-a'), state.variants, 'base');
  fillSelect(document.getElementById('model-b'), state.variants, 'sft');
  fillSelect(document.getElementById('model-c'), state.variants, 'grpo-balanced');
  fillSelect(document.getElementById('example-select'), state.showcase, state.showcase[0]?.id, 'title');
}

function wireControls() {
  document.getElementById('example-select').addEventListener('change', onExampleChange);
  document.getElementById('set-progression').addEventListener('click', setProgressionDefaults);
  document.getElementById('run-both').addEventListener('click', runArena);
  document.querySelectorAll('#phase-filters .filter-chip').forEach((button) => {
    button.addEventListener('click', () => {
      document.querySelectorAll('#phase-filters .filter-chip').forEach((chip) => chip.classList.remove('active'));
      button.classList.add('active');
      state.activePhaseFilter = button.dataset.phase;
      renderArenaWindows();
      renderTraceExplorer();
    });
  });
}

function fillSelect(select, items, selected, labelKey = 'label') {
  select.innerHTML = '';
  items.forEach((item) => {
    const option = document.createElement('option');
    option.value = item.key || item.id;
    option.textContent = item[labelKey];
    option.selected = option.value === selected;
    select.appendChild(option);
  });
}

function setSelectValue(id, value) {
  const select = document.getElementById(id);
  const option = Array.from(select.options).find((item) => item.value === value);
  if (option) select.value = value;
}

function setProgressionDefaults() {
  setSelectValue('model-a', 'base');
  setSelectValue('model-b', 'sft');
  setSelectValue('model-c', 'grpo-balanced');
}

function onExampleChange() {
  const id = document.getElementById('example-select').value;
  const example = state.showcase.find((item) => item.id === id);
  if (example) document.getElementById('task-input').value = example.task;
  document.querySelectorAll('#example-pills .pill').forEach((pill) => {
    pill.classList.toggle('active', pill.textContent === example?.title);
  });
}

function renderExamplePills() {
  const root = document.getElementById('example-pills');
  root.innerHTML = '';
  state.showcase.forEach((example, index) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `pill ${index === 0 ? 'active' : ''}`;
    button.textContent = example.title;
    button.addEventListener('click', () => {
      document.getElementById('example-select').value = example.id;
      onExampleChange();
    });
    root.appendChild(button);
  });
}

function resetArena() {
  document.getElementById('ribbon-headline').textContent = 'Waiting for a run';
  document.getElementById('ribbon-copy').textContent = 'Run a scenario to compare base, SFT, and GRPO policy behavior.';
  ['a', 'b', 'c'].forEach((slot) => {
    document.getElementById(`summary-${slot}`).textContent = 'Waiting';
    document.getElementById(`output-${slot}`).innerHTML = '<div class="trace-empty">Run a prompt to start streaming.</div>';
    document.getElementById(`flow-${slot}`).innerHTML = renderFlowSteps(null, null);
  });
  document.getElementById('trace-title').textContent = 'No run selected';
  document.getElementById('trace-subtitle').textContent = 'Click any stage or step to inspect the full trace.';
  document.getElementById('trace-detail').innerHTML = '<div class="trace-empty">Detailed timeline will appear here.</div>';
}

async function runArena() {
  resetArena();
  const task = document.getElementById('task-input').value.trim();
  const models = {
    a: document.getElementById('model-a').value,
    b: document.getElementById('model-b').value,
    c: document.getElementById('model-c').value,
  };
  await Promise.all([
    runStream(task, models.a, 'a'),
    runStream(task, models.b, 'b'),
    runStream(task, models.c, 'c'),
  ]);
}

async function runStream(task, model, slot) {
  const run = {
    key: `${slot}-${model}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    slot,
    model,
    task,
    phases: [],
    verification: null,
    mode: 'unknown',
  };
  state.runs[run.key] = run;
  state.runOrder = [run.key, ...state.runOrder.filter((key) => key !== run.key)].slice(0, 12);
  state.selectedRunKey = state.selectedRunKey || run.key;
  renderEverything();

  const response = await fetch('/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task, model, inject_errors: document.getElementById('inject-errors').checked }),
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop() || '';
    parts.forEach((chunk) => handleChunk(chunk, run));
  }
}

function handleChunk(chunk, run) {
  const line = chunk.trim();
  if (!line.startsWith('data: ')) return;
  const payload = line.slice(6);
  if (payload === '[DONE]') {
    renderEverything();
    return;
  }
  const event = JSON.parse(payload);
  if (event.type === 'token') run.phases.push({ phase: event.data.phase, text: event.data.text });
  if (event.type === 'verification') run.verification = event.data;
  if (event.type === 'run_completed') run.mode = event.data.mode || run.mode;
  renderEverything();
}

function currentRuns() {
  return {
    a: latestRunFor(document.getElementById('model-a').value, 'a'),
    b: latestRunFor(document.getElementById('model-b').value, 'b'),
    c: latestRunFor(document.getElementById('model-c').value, 'c'),
  };
}

function latestRunFor(model, slot) {
  return state.runOrder.map((key) => state.runs[key]).find((run) => run && run.model === model && run.slot === slot);
}

function renderEverything() {
  renderArenaWindows();
  renderRibbon();
  renderTraceExplorer();
}

function renderArenaWindows() {
  const runs = currentRuns();
  ['a', 'b', 'c'].forEach((slot) => {
    const selectedModel = document.getElementById(`model-${slot}`).value;
    const variant = state.variants.find((entry) => entry.key === selectedModel);
    const run = runs[slot];
    document.getElementById(`title-${slot}`).textContent = variant?.label || selectedModel;
    document.getElementById(`summary-${slot}`).textContent = !run?.verification ? `${run?.phases.length || 0} phases` : `${run.verification.correct ? 'Pass' : 'Fail'} / ${run.verification.loop_count} calls`;
    document.getElementById(`flow-${slot}`).innerHTML = renderFlowSteps(run, run?.phases?.length ? run.phases[run.phases.length - 1].phase : null);

    const visible = (run?.phases || []).filter((phase) => state.activePhaseFilter === 'all' || phase.phase === state.activePhaseFilter);
    document.getElementById(`output-${slot}`).innerHTML = visible.length
      ? visible.map((phase, index) => `
          <button type="button" class="phase ${phase.phase}" data-run="${run.key}" data-index="${index}">
            <span>${escapeHtml(labelPhase(phase.phase))}</span>
            <div>${escapeHtml(phase.text).replace(/\n/g, '<br>')}</div>
          </button>
        `).join('')
      : '<div class="trace-empty">No phases for this filter yet.</div>';
  });

  document.querySelectorAll('.phase[data-run], .flow-step[data-run]').forEach((button) => {
    button.addEventListener('click', () => {
      state.selectedRunKey = button.dataset.run;
      renderTraceExplorer();
    });
  });
}

function renderFlowSteps(run, activePhase) {
  const phases = ['think', 'tool_call', 'observation', 'answer'];
  return phases.map((phase) => {
    const seen = !!run?.phases?.some((item) => item.phase === phase);
    const active = activePhase === phase;
    return `<button type="button" class="flow-step ${seen ? 'seen' : ''} ${active ? 'active' : ''}" data-run="${run?.key || ''}">${labelPhase(phase)}</button>`;
  }).join('<div class="flow-sep"></div>');
}

function renderRibbon() {
  const runs = currentRuns();
  if (!runs.a?.verification || !runs.b?.verification || !runs.c?.verification) return;
  const winners = bestRuns([runs.a, runs.b, runs.c]);
  document.getElementById('ribbon-headline').textContent = winners.length === 1 ? `${labelFor(winners[0].model)} leads` : 'No single winner';
  document.getElementById('ribbon-copy').textContent = progressionNarrative(runs.a, runs.b, runs.c, winners);
}

function renderTraceExplorer() {
  const run = state.runs[state.selectedRunKey];
  if (!run) return;
  document.getElementById('trace-title').textContent = `${labelFor(run.model)} / ${run.slot.toUpperCase()}`;
  document.getElementById('trace-subtitle').textContent = run.task;
  const visible = run.phases.filter((phase) => state.activePhaseFilter === 'all' || phase.phase === state.activePhaseFilter);
  document.getElementById('trace-detail').innerHTML = visible.length
    ? visible.map((phase, index) => `
        <article class="timeline-step ${phase.phase}">
          <header><span>${escapeHtml(labelPhase(phase.phase))}</span><span>Step ${index + 1}</span></header>
          <div>${escapeHtml(phase.text).replace(/\n/g, '<br>')}</div>
        </article>
      `).join('')
    : '<div class="trace-empty">No phases for this filter.</div>';
}

function bestRuns(runs) {
  const scored = runs.map((run) => ({ run, score: [run.verification.correct ? 1 : 0, run.verification.overtooling ? 0 : 1, -(run.verification.loop_count || 0)] }));
  const best = scored.reduce((acc, item) => compareScore(item.score, acc) > 0 ? item.score : acc, [-1, -1, -99]);
  return scored.filter((item) => compareScore(item.score, best) === 0).map((item) => item.run);
}

function compareScore(a, b) {
  for (let i = 0; i < a.length; i += 1) {
    if (a[i] > b[i]) return 1;
    if (a[i] < b[i]) return -1;
  }
  return 0;
}

function progressionNarrative(baseRun, sftRun, grpoRun, winners) {
  if (!baseRun.verification.correct && !sftRun.verification.correct && grpoRun.verification.correct) return `${labelFor(grpoRun.model)} is the only stage that solved the task. That is the clearest proof of training payoff.`;
  if (!baseRun.verification.correct && sftRun.verification.correct && grpoRun.verification.correct) return 'SFT teaches the trace protocol. GRPO keeps the win and improves operational behavior.';
  if (baseRun.verification.correct && sftRun.verification.correct && grpoRun.verification.correct) return winners.length === 1 ? `${labelFor(winners[0].model)} currently has the strongest operational trace.` : 'All three solved it. Compare the arenas to see where policy style diverges.';
  if (!grpoRun.verification.correct) return `${labelFor(grpoRun.model)} did not separate on this prompt. Use a harder scenario.`;
  return `${labelFor(grpoRun.model)} converts a miss into a solve on this prompt.`;
}

async function renderRewardLab() {
  const root = document.getElementById('reward-lab');
  root.innerHTML = '';
  for (const experiment of ['reward-design', 'method-comparison', 'kl-penalty']) {
    const payload = await fetch(`/api/reward-lab/${experiment}`).then((res) => res.json());
    const card = document.createElement('article');
    card.className = 'reward-card';
    card.innerHTML = `<span class="eyebrow">${escapeHtml(payload.experiment)}</span><h3>${escapeHtml(payload.title)}</h3><div class="reward-list">${(payload.items || []).map((item) => `<div class="reward-item"><strong>${escapeHtml(item.variant || 'item')}</strong><p>${escapeHtml(item.annotation || '')}</p></div>`).join('')}</div>`;
    root.appendChild(card);
  }
}

async function renderModelCard() {
  const payload = await fetch('/api/model-card').then((res) => res.json());
  const rows = (payload.cross_variant_table || []).map((row) => `<tr><td>${escapeHtml(row.variant)}</td><td>${formatPct(row.overall_accuracy)}</td><td>${formatPct(row.tool_hallucination_rate)}</td><td>${formatPct(row.overtooling_rate)}</td></tr>`).join('');
  document.getElementById('model-card').innerHTML = `<article class="model-card-block"><span class="eyebrow">Base</span><h3>${escapeHtml(payload.base_model)}</h3><p>${escapeHtml(payload.training_method || '')}</p></article><article class="model-card-block"><span class="eyebrow">Comparison</span><div class="table-wrap"><table><thead><tr><th>Variant</th><th>Overall</th><th>Hallucination</th><th>Over-tooling</th></tr></thead><tbody>${rows}</tbody></table></div></article>`;
}

function labelFor(modelKey) { return state.variants.find((item) => item.key === modelKey)?.label || modelKey; }
function labelPhase(phase) { return phase === 'tool_call' ? 'Tool' : phase === 'observation' ? 'Obs' : phase.charAt(0).toUpperCase() + phase.slice(1); }
function formatPct(value) { return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '-'; }
function escapeHtml(text) { return String(text || '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;'); }

boot();
