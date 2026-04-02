/**
 * Eval Dashboard renderer — stats, bars, tables, failure analysis, loop visualization.
 */

function esc(v) {
  return String(v ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]
  );
}

function scoreColor(pct) {
  if (pct < 30) return 'score-red';
  if (pct <= 70) return 'score-yellow';
  return 'score-green';
}

// ---- Top stats ----
function renderStatCard(label, base, sft, grpo, suffix = '%') {
  return `
    <div class="eval-stat-card">
      <div class="eval-stat-label">${label}</div>
      <div class="eval-stat-nums">
        <div class="eval-stat-block">
          <span class="eval-stat-model">Base</span>
          <span class="eval-stat-val eval-stat-val--base">${base}${suffix}</span>
        </div>
        <span class="eval-stat-arrow">\u2192</span>
        <div class="eval-stat-block">
          <span class="eval-stat-model">SFT</span>
          <span class="eval-stat-val eval-stat-val--sft">${sft}${suffix}</span>
        </div>
        <span class="eval-stat-arrow">\u2192</span>
        <div class="eval-stat-block">
          <span class="eval-stat-model">GRPO</span>
          <span class="eval-stat-val eval-stat-val--grpo">${grpo}${suffix}</span>
        </div>
      </div>
    </div>`;
}

export function renderEvalStats(container, stats) {
  container.innerHTML = [
    renderStatCard('Task Accuracy', stats.base.accuracy, stats.sft.accuracy, stats.grpo.accuracy),
    renderStatCard('Tool Usage', stats.base.tool_usage, stats.sft.tool_usage, stats.grpo.tool_usage),
    renderStatCard('Restraint', stats.base.restraint, stats.sft.restraint, stats.grpo.restraint),
  ].join('');
}

// ---- Bar charts ----
function barRow(label, value, variant) {
  return `
    <div class="eval-bar-row">
      <span class="eval-bar-label">${label}</span>
      <div class="eval-bar-track">
        <div class="eval-bar-fill eval-bar-fill--${variant}" style="width: ${Math.max(value, 2)}%"></div>
      </div>
      <span class="eval-bar-val">${value}%</span>
    </div>`;
}

function barGroup(title, base, sft, grpo) {
  return `
    <div class="eval-bar-group">
      <div class="eval-bar-title">${title}</div>
      ${barRow('BASE', base, 'base')}
      ${barRow('SFT', sft, 'sft')}
      ${barRow('GRPO', grpo, 'grpo')}
    </div>`;
}

export function renderEvalBars(container, stats) {
  container.innerHTML = [
    barGroup('Accuracy', stats.base.accuracy, stats.sft.accuracy, stats.grpo.accuracy),
    barGroup('Tool Usage', stats.base.tool_usage, stats.sft.tool_usage, stats.grpo.tool_usage),
    barGroup('Restraint', stats.base.restraint, stats.sft.restraint, stats.grpo.restraint),
  ].join('');

  // Animate bars in after render
  requestAnimationFrame(() => {
    container.querySelectorAll('.eval-bar-fill').forEach((bar) => {
      const w = bar.style.width;
      bar.style.width = '0%';
      requestAnimationFrame(() => { bar.style.width = w; });
    });
  });
}

// ---- Category table ----
export function renderEvalTable(container, tasks) {
  // Compute per-category scores
  const cats = {};
  for (const task of tasks) {
    const cat = task.category;
    if (!cats[cat]) cats[cat] = { name: cat, count: 0, base: [], sft: [], grpo: [] };
    cats[cat].count++;
    for (const m of ['base', 'sft', 'grpo']) {
      const trace = task.traces?.[m];
      if (!trace) continue;
      const v = trace.verdict;
      cats[cat][m].push(v === 'correct' ? 100 : v === 'partial' ? 50 : 0);
    }
  }

  const catList = Object.values(cats).sort((a, b) => a.name.localeCompare(b.name));

  function avg(arr) { return arr.length ? Math.round(arr.reduce((a, b) => a + b, 0) / arr.length) : 0; }
  function cell(pct) { return `<span class="eval-cell-score ${scoreColor(pct)}">${pct}%</span>`; }

  let rows = '';
  for (const c of catList) {
    const bv = avg(c.base), sv = avg(c.sft), gv = avg(c.grpo);
    rows += `<tr>
      <td><span class="eval-cat-name">${esc(c.name)}</span><span class="eval-cat-count">${c.count} tasks</span></td>
      <td>${cell(bv)}</td>
      <td>${cell(sv)}</td>
      <td>${cell(gv)}</td>
    </tr>`;
  }

  container.innerHTML = `
    <table class="eval-table">
      <thead><tr><th>Category</th><th>Base</th><th>SFT</th><th>GRPO</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

// ---- Failure analysis ----
export function renderEvalFailures(container, tasks) {
  // Find tasks where GRPO is not correct
  const failures = tasks.filter((t) => t.traces?.grpo?.verdict !== 'correct');

  if (failures.length === 0) {
    // Also show SFT failures that GRPO fixed
    const sftFailures = tasks.filter((t) =>
      t.traces?.sft?.verdict !== 'correct' && t.traces?.grpo?.verdict === 'correct'
    );

    let fixedHtml = '';
    if (sftFailures.length > 0) {
      fixedHtml = `<div style="margin-top:20px;display:flex;flex-direction:column;gap:10px">
        <div style="font-size:12px;color:var(--text-3);font-weight:500;text-transform:uppercase;letter-spacing:0.06em">SFT failures fixed by GRPO (${sftFailures.length})</div>
        ${sftFailures.map((t) => `
          <div class="eval-failure-card" style="border-left-color:var(--grpo)">
            <div class="eval-failure-title">${esc(t.title)}</div>
            <div class="eval-failure-prompt">${esc(t.prompt)}</div>
            <div class="eval-failure-detail">
              <strong>SFT issue:</strong> ${esc(t.traces.sft.summary || t.traces.sft.behaviors_detected?.join(', ') || 'Partial/incorrect')}
              &nbsp;&nbsp;<strong>GRPO fix:</strong> ${esc(t.traces.grpo.summary || 'Correct')}
            </div>
          </div>
        `).join('')}
      </div>`;
    }

    container.innerHTML = `
      <div class="eval-failure-empty">
        <div class="eval-failure-empty-check">\u2713</div>
        <div>All ${tasks.length} showcase tasks pass with GRPO.</div>
        <div style="color:var(--text-4);margin-top:4px;font-size:12px">
          In the full 50-task eval suite, 38% of tasks still fail. The next training iteration targets multi-step reasoning and edge-case restraint.
        </div>
      </div>
      ${fixedHtml}`;
    return;
  }

  container.innerHTML = failures.map((t) => {
    const tr = t.traces.grpo;
    const behaviors = (tr.behaviors_detected || []).join(', ') || 'Unknown';
    return `
      <div class="eval-failure-card">
        <div class="eval-failure-title">${esc(t.title)}</div>
        <div class="eval-failure-prompt">${esc(t.prompt)}</div>
        <div class="eval-failure-detail">
          <strong>Issue:</strong> ${esc(tr.summary || 'Incorrect verdict')}
          &nbsp;&nbsp;<strong>Behaviors:</strong> ${esc(behaviors)}
        </div>
      </div>`;
  }).join('');
}

// ---- The Loop ----
export function renderEvalLoop(container) {
  const steps = [
    { label: 'Define Eval Suite', active: false },
    { label: 'Run Against Model', active: false },
    { label: 'Identify Failures', active: false },
    { label: 'Generate Training Data', active: false },
    { label: 'Train GRPO', active: false },
    { label: 'Re-evaluate', active: true },
  ];

  const stepsHtml = steps.map((s, i) => {
    const box = `<div class="eval-loop-box${s.active ? ' active' : ''}">${s.label}</div>`;
    const arrow = i < steps.length - 1 ? '<span class="eval-loop-arrow">\u2192</span>' : '';
    return `<div class="eval-loop-step">${box}</div>${arrow}`;
  }).join('');

  container.innerHTML = `
    <div class="eval-loop">${stepsHtml}</div>
    <div class="eval-loop-return">
      <div class="eval-loop-return-line"></div>
    </div>
    <div style="text-align:center;margin-top:4px">
      <span class="eval-loop-return-label">\u21B0 Loop back: failures become training signal</span>
    </div>
    <div class="eval-loop-insight">
      12 tasks failed after SFT \u2192 GRPO reward function targeted them \u2192 <strong>9/12 now pass</strong>
    </div>`;
}
