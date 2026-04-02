/**
 * Verdict panel renderer — metrics for a single trace.
 */

function verdictClass(v) {
  if (v === 'correct') return 'good';
  if (v === 'partial') return 'warn';
  return 'bad';
}

function verdictLabel(v) {
  if (v === 'correct') return 'PASS';
  if (v === 'partial') return 'PARTIAL';
  return 'FAIL';
}

function restraintClass(r) {
  const v = String(r || '').toLowerCase();
  if (v === 'strong' || v === 'high') return 'good';
  if (v === 'none' || v === 'n/a') return 'bad';
  return 'warn';
}

function row(label, value, cls = '') {
  return `<div class="verdict-row"><span class="verdict-label">${label}</span><span class="verdict-value ${cls}">${value}</span></div>`;
}

export function renderVerdictPanel(container, trace) {
  if (!trace) { container.innerHTML = ''; return; }

  const behaviors = (trace.behaviors_detected || []).join(', ') || '\u2014';

  container.innerHTML = [
    row('Verdict', verdictLabel(trace.verdict), verdictClass(trace.verdict)),
    row('Tools Used', `${trace.tool_calls_used} / ${trace.optimal_tool_calls}`),
    row('Steps', trace.steps),
    row('Restraint', trace.restraint || '\u2014', restraintClass(trace.restraint)),
    row('Evidence', trace.evidence_count || 0),
    `<div class="verdict-row"><span class="verdict-label">Behaviors</span><span class="verdict-value" style="font-size:11px;font-family:var(--sans);text-align:right;max-width:180px">${behaviors}</span></div>`,
  ].join('');
}
