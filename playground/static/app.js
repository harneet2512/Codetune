const state = {
  variants: [],
  showcase: [],
  health: null,
  runs: {},
  runOrder: [],
  selectedRunKey: null,
  activePhaseFilter: "all",
};

const tabs = document.querySelectorAll(".tab");
const panels = document.querySelectorAll(".panel");

tabs.forEach((button) => {
  button.addEventListener("click", () => {
    tabs.forEach((item) => item.classList.remove("active"));
    panels.forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    document.getElementById(`tab-${button.dataset.tab}`).classList.add("active");
  });
});

async function boot() {
  await Promise.all([loadShowcase(), loadHealth(), renderRewardLab(), renderModelCard()]);
  wireControls();
  onExampleChange();
  renderExamplePills();
  resetArena();
  renderTraceExplorer();
}

async function loadShowcase() {
  const showcase = await fetch("/api/showcase").then((res) => res.json());
  state.variants = showcase.variants;
  state.showcase = showcase.examples;
  fillSelect(document.getElementById("model-a"), state.variants, "base");
  fillSelect(document.getElementById("model-b"), state.variants, "grpo-balanced");
  fillSelect(document.getElementById("example-select"), state.showcase, state.showcase[0]?.id, "title");
}

async function loadHealth() {
  const health = await fetch("/api/health").then((res) => res.json()).catch(() => ({ mode: "unknown" }));
  state.health = health;
  document.getElementById("health-mode").textContent = health.mode || "unknown";
}

function wireControls() {
  document.getElementById("example-select").addEventListener("change", onExampleChange);
  document.getElementById("run-both").addEventListener("click", runArena);
  document.getElementById("swap-models").addEventListener("click", swapModels);
  document.querySelectorAll("#phase-filters .filter-chip").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("#phase-filters .filter-chip").forEach((chip) => chip.classList.remove("active"));
      button.classList.add("active");
      state.activePhaseFilter = button.dataset.phase;
      renderTraceExplorer();
    });
  });
}

function fillSelect(select, items, selected, labelKey = "label") {
  select.innerHTML = "";
  items.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.key || item.id;
    option.textContent = item[labelKey];
    if (option.value === selected) option.selected = true;
    select.appendChild(option);
  });
}

function renderExamplePills() {
  const root = document.getElementById("example-pills");
  root.innerHTML = "";
  state.showcase.forEach((example, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `pill ${index === 0 ? "active" : ""}`;
    button.textContent = example.title;
    button.addEventListener("click", () => {
      document.getElementById("example-select").value = example.id;
      onExampleChange();
      root.querySelectorAll(".pill").forEach((pill) => pill.classList.remove("active"));
      button.classList.add("active");
    });
    root.appendChild(button);
  });
}

function onExampleChange() {
  const id = document.getElementById("example-select").value;
  const example = state.showcase.find((item) => item.id === id);
  if (example) document.getElementById("task-input").value = example.task;
  document.querySelectorAll("#example-pills .pill").forEach((pill) => {
    pill.classList.toggle("active", pill.textContent === example?.title);
  });
}

function swapModels() {
  const modelA = document.getElementById("model-a");
  const modelB = document.getElementById("model-b");
  const next = modelA.value;
  modelA.value = modelB.value;
  modelB.value = next;
}

function resetArena() {
  renderEmptyTrace("output-a");
  renderEmptyTrace("output-b");
  document.getElementById("summary-a").textContent = "Waiting for run";
  document.getElementById("summary-b").textContent = "Waiting for run";
  resetCompareOverview();
}

function renderEmptyTrace(id) {
  const container = document.getElementById(id);
  container.innerHTML = "";
  const empty = document.createElement("div");
  empty.className = "trace-empty";
  empty.textContent = "Trace output will stream here.";
  container.appendChild(empty);
}

function resetCompareOverview() {
  document.getElementById("compare-a-status").textContent = "Waiting";
  document.getElementById("compare-a-meta").textContent = "Run a comparison to populate this.";
  document.getElementById("compare-b-status").textContent = "Waiting";
  document.getElementById("compare-b-meta").textContent = "Run a comparison to populate this.";
  document.getElementById("compare-summary").textContent = "No active comparison";
  document.getElementById("compare-summary-meta").textContent = "Outcomes, loop count, and tool behavior will appear here.";
}

async function runArena() {
  const task = document.getElementById("task-input").value.trim();
  const modelA = document.getElementById("model-a").value;
  const modelB = document.getElementById("model-b").value;
  const variantA = state.variants.find((item) => item.key === modelA);
  const variantB = state.variants.find((item) => item.key === modelB);
  document.getElementById("title-a").textContent = variantA?.label || modelA;
  document.getElementById("title-b").textContent = variantB?.label || modelB;
  document.getElementById("summary-a").textContent = "Streaming trace...";
  document.getElementById("summary-b").textContent = "Streaming trace...";
  resetCompareOverview();

  await Promise.all([
    runStream(task, modelA, "output-a", "summary-a"),
    runStream(task, modelB, "output-b", "summary-b"),
  ]);
  renderCompareOverview(modelA, modelB);
}

async function runStream(task, model, containerId, summaryId) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";

  const runState = {
    key: `${model}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    model,
    task,
    phases: [],
    verification: null,
    mode: "unknown",
    summaryTarget: summaryId,
  };
  state.runs[runState.key] = runState;
  state.runOrder = [runState.key, ...state.runOrder.filter((key) => key !== runState.key)].slice(0, 8);
  if (!state.selectedRunKey) state.selectedRunKey = runState.key;
  renderTraceExplorer();

  const response = await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      task,
      model,
      inject_errors: document.getElementById("inject-errors").checked,
    }),
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop();
    parts.forEach((chunk) => handleChunk(chunk, container, runState, summaryId));
  }
}

function handleChunk(chunk, container, runState, summaryId) {
  const line = chunk.trim();
  if (!line.startsWith("data: ")) return;
  const payload = line.slice(6);
  if (payload === "[DONE]") {
    updateSummary(summaryId, runState);
    renderCompareOverview();
    if (state.selectedRunKey === runState.key) renderTraceExplorer();
    return;
  }

  const event = JSON.parse(payload);

  if (event.type === "token") {
    const step = { phase: event.data.phase, text: event.data.text };
    runState.phases.push(step);
    appendPhase(container, step.phase, step.text, runState);
    if (state.selectedRunKey === runState.key) renderTraceExplorer();
  }

  if (event.type === "verification") {
    runState.verification = event.data;
    appendVerification(container, event.data, runState);
    updateSummary(summaryId, runState);
    renderCompareOverview();
    renderTraceExplorer();
  }

  if (event.type === "run_completed") {
    runState.mode = event.data.mode || runState.mode;
    updateSummary(summaryId, runState);
    renderCompareOverview();
    renderTraceExplorer();
  }
}

function appendPhase(container, phase, text, runState) {
  const node = document.createElement("button");
  node.type = "button";
  node.className = `phase ${phase}`;
  node.dataset.label = phase.replace("_", " ");
  node.textContent = text;
  node.addEventListener("click", () => selectRun(runState.key));
  container.appendChild(node);
}

function appendVerification(container, verification, runState) {
  const node = document.createElement("button");
  node.type = "button";
  node.className = "phase verification";
  node.dataset.label = verification.correct ? "verification / pass" : "verification / fail";
  node.innerHTML = `
    <strong>${verification.correct ? "Correct answer" : "Incorrect answer"}</strong>
    <div class="verification-grid">
      ${renderVerificationChip("Expected tools", (verification.expected_tools || []).join(", ") || "none", true)}
      ${renderVerificationChip("Actual tools", (verification.actual_tools || []).join(", ") || "none", true)}
      ${renderVerificationChip("Argument validity", verification.arg_validity ? "valid" : "invalid", verification.arg_validity)}
      ${renderVerificationChip("Over-tooling", verification.overtooling ? "yes" : "no", !verification.overtooling)}
    </div>
  `;
  node.addEventListener("click", () => selectRun(runState.key));
  container.appendChild(node);
}

function renderVerificationChip(label, value, positive) {
  return `<div class="verification-chip ${positive ? "pass" : "fail"}"><strong>${label}</strong><br>${value}</div>`;
}

function updateSummary(summaryId, runState) {
  const summary = document.getElementById(summaryId);
  if (!summary) return;
  if (!runState.verification) {
    summary.textContent = `${runState.phases.length} phases`;
    return;
  }
  const correctness = runState.verification.correct ? "Pass" : "Fail";
  summary.textContent = `${correctness} / ${runState.verification.loop_count} tool calls / ${runState.mode}`;
}

function renderCompareOverview(modelAKey, modelBKey) {
  const modelA = modelAKey || document.getElementById("model-a")?.value;
  const modelB = modelBKey || document.getElementById("model-b")?.value;
  const runs = state.runOrder.map((key) => state.runs[key]).filter(Boolean);
  const runA = runs.find((run) => run.model === modelA);
  const runB = runs.find((run) => run.model === modelB);

  updateCompareCard("a", runA);
  updateCompareCard("b", runB);

  const summary = document.getElementById("compare-summary");
  const meta = document.getElementById("compare-summary-meta");
  if (!runA || !runB || !runA.verification || !runB.verification) {
    summary.textContent = "Comparison pending";
    meta.textContent = "Both runs need to finish before differences can be summarized.";
    return;
  }

  if (runA.verification.correct && !runB.verification.correct) {
    summary.textContent = `${labelFor(modelA)} leads`;
    meta.textContent = `${labelFor(modelA)} solved the task while ${labelFor(modelB)} did not.`;
    return;
  }
  if (!runA.verification.correct && runB.verification.correct) {
    summary.textContent = `${labelFor(modelB)} leads`;
    meta.textContent = `${labelFor(modelB)} solved the task while ${labelFor(modelA)} did not.`;
    return;
  }

  const loopDelta = (runA.verification.loop_count || 0) - (runB.verification.loop_count || 0);
  summary.textContent = runA.verification.correct ? "Both variants solved it" : "Both variants missed";
  meta.textContent = loopDelta === 0
    ? "They used the same number of tool calls. Inspect the trace for reasoning differences."
    : `${Math.abs(loopDelta)} tool-call difference. ${loopDelta < 0 ? labelFor(modelA) : labelFor(modelB)} was more tool-efficient.`;
}

function updateCompareCard(side, run) {
  const status = document.getElementById(`compare-${side}-status`);
  const meta = document.getElementById(`compare-${side}-meta`);
  if (!run || !run.verification) {
    status.textContent = "Waiting";
    meta.textContent = "Run a comparison to populate this.";
    return;
  }
  status.textContent = `${run.verification.correct ? "Pass" : "Fail"} / ${run.mode}`;
  meta.textContent = `${run.verification.loop_count} tool calls, expected tools: ${(run.verification.expected_tools || []).join(", ") || "none"}`;
}

function labelFor(modelKey) {
  return state.variants.find((item) => item.key === modelKey)?.label || modelKey;
}

function selectRun(runKey) {
  state.selectedRunKey = runKey;
  renderTraceExplorer();
  document.querySelector('[data-tab="trace"]').click();
}

function renderTraceExplorer() {
  const title = document.getElementById("trace-title");
  const subtitle = document.getElementById("trace-subtitle");
  const stats = document.getElementById("trace-stats");
  const detail = document.getElementById("trace-detail");
  const runList = document.getElementById("trace-run-list");
  detail.innerHTML = "";
  stats.innerHTML = "";
  runList.innerHTML = "";

  state.runOrder.forEach((key) => {
    const run = state.runs[key];
    if (!run) return;
    const variant = state.variants.find((item) => item.key === run.model);
    const button = document.createElement("button");
    button.type = "button";
    button.className = `run-item ${state.selectedRunKey === key ? "active" : ""}`;
    button.innerHTML = `
      <strong>${variant?.label || run.model}</strong>
      <span>${run.verification?.correct ? "Pass" : run.verification ? "Fail" : "Pending"} / ${run.mode}</span>
      <span>${truncate(run.task, 78)}</span>
    `;
    button.addEventListener("click", () => selectRun(key));
    runList.appendChild(button);
  });

  const run = state.runs[state.selectedRunKey];
  if (!run) {
    title.textContent = "No run selected";
    subtitle.textContent = "Run a comparison in Arena, then click a result card to inspect the full timeline here.";
    const empty = document.createElement("div");
    empty.className = "timeline-empty";
    empty.textContent = "No trace loaded yet.";
    detail.appendChild(empty);
    return;
  }

  const variant = state.variants.find((item) => item.key === run.model);
  title.textContent = variant?.label || run.model;
  subtitle.textContent = run.task;

  const metrics = [
    { label: "Mode", value: run.mode },
    { label: "Steps", value: run.phases.length },
    { label: "Tool Calls", value: run.verification?.loop_count ?? "-" },
    { label: "Correct", value: run.verification?.correct ? "yes" : run.verification ? "no" : "pending" },
  ];
  metrics.forEach((item) => {
    const card = document.createElement("div");
    card.className = "score-card";
    card.innerHTML = `<span class="metric-label">${item.label}</span><strong>${item.value}</strong>`;
    stats.appendChild(card);
  });

  const visiblePhases = run.phases.filter((phase) => state.activePhaseFilter === "all" || phase.phase === state.activePhaseFilter);
  if (visiblePhases.length === 0) {
    const empty = document.createElement("div");
    empty.className = "timeline-empty";
    empty.textContent = `No ${state.activePhaseFilter} steps in this run.`;
    detail.appendChild(empty);
  } else {
    visiblePhases.forEach((phase, index) => {
      const node = document.createElement("article");
      node.className = `timeline-step ${phase.phase}`;
      node.innerHTML = `
        <header>
          <span>${phase.phase.replace("_", " ")}</span>
          <span>Step ${index + 1}</span>
        </header>
        <div>${escapeHtml(phase.text).replace(/\n/g, "<br>")}</div>
      `;
      detail.appendChild(node);
    });
  }

  if (run.verification) {
    const verify = document.createElement("article");
    verify.className = "timeline-step answer";
    verify.innerHTML = `
      <header>
        <span>verification</span>
        <span>${run.verification.correct ? "pass" : "fail"}</span>
      </header>
      <div>${escapeHtml(JSON.stringify(run.verification, null, 2)).replace(/\n/g, "<br>")}</div>
    `;
    detail.appendChild(verify);
  }
}

async function renderRewardLab() {
  const experiments = ["reward-design", "method-comparison", "kl-penalty"];
  const root = document.getElementById("reward-lab");
  root.innerHTML = "";

  for (const experiment of experiments) {
    const payload = await fetch(`/api/reward-lab/${experiment}`).then((res) => res.json());
    const card = document.createElement("article");
    card.className = "reward-card";
    const items = (payload.items || []).map((item) => {
      const label = item.variant || (item.beta !== undefined ? `beta=${item.beta}` : "item");
      return `<div class="reward-item"><strong>${label}</strong><p>${item.annotation || "No annotation provided."}</p></div>`;
    }).join("");
    card.innerHTML = `
      <span class="section-kicker">${payload.experiment}</span>
      <h3>${payload.title}</h3>
      <div class="reward-list">${items}</div>
    `;
    root.appendChild(card);
  }
}

async function renderModelCard() {
  const payload = await fetch("/api/model-card").then((res) => res.json());
  const root = document.getElementById("model-card");
  const tools = (payload.tool_set || []).map((tool) => `<span class="pill">${tool}</span>`).join("");
  const failures = (payload.failure_taxonomy || []).map((item) => `<span class="pill">${item}</span>`).join("");
  const rows = (payload.cross_variant_table || []).map((row) => `
    <tr>
      <td>${row.variant}</td>
      <td>${formatPct(row.overall_accuracy)}</td>
      <td>${formatPct(row.tool_hallucination_rate)}</td>
      <td>${formatPct(row.overtooling_rate)}</td>
      <td>${formatPct(row.error_recovery_rate)}</td>
      <td>${formatPct(row.planning_rate)}</td>
    </tr>
  `).join("");

  root.innerHTML = `
    <section class="model-card-block">
      <span class="section-kicker">Base</span>
      <h3>${payload.base_model}</h3>
      <p class="muted">${payload.training_method}</p>
      <p class="muted">Estimated training cost: ${payload.training_cost_estimate || "-"}</p>
    </section>
    <section class="model-card-block">
      <span class="section-kicker">Tool Set</span>
      <div class="pill-row">${tools}</div>
    </section>
    <section class="model-card-block">
      <span class="section-kicker">Cross-Variant Comparison</span>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Variant</th>
              <th>Overall</th>
              <th>Hallucination</th>
              <th>Over-tooling</th>
              <th>Recovery</th>
              <th>Planning</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </section>
    <section class="model-card-block">
      <span class="section-kicker">Failure Taxonomy</span>
      <div class="pill-row">${failures}</div>
    </section>
  `;
}

function formatPct(value) {
  if (typeof value !== "number") return "-";
  return `${(value * 100).toFixed(1)}%`;
}

function truncate(text, maxLength) {
  if (!text || text.length <= maxLength) return text;
  return `${text.slice(0, maxLength - 3)}...`;
}

function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

boot();
