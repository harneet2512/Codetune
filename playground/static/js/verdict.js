function metric(label, value, classes = '') {
  return `
    <div class="metric-card">
      <span class="metric-label">${label}</span>
      <strong class="metric-value ${classes}">${value}</strong>
    </div>
  `;
}

function verdictLabel(verdict) {
  if (verdict === 'correct') return 'Correct';
  if (verdict === 'partial') return 'Partial';
  return 'Fail';
}

function verdictClass(verdict) {
  if (verdict === 'correct') return 'metric-good';
  if (verdict === 'partial') return 'metric-warn';
  return 'metric-bad';
}

function restraintClass(restraint) {
  const value = String(restraint || '').toLowerCase();
  if (['high', 'strong'].includes(value)) return 'metric-good';
  if (value === 'weak' || value === 'medium') return 'metric-warn';
  if (value === 'none') return 'metric-bad';
  return '';
}

export function renderVerdictBar(container, trace) {
  const behaviors = (trace.behaviors_detected || []).slice(0, 3).join(' · ') || 'None';
  container.innerHTML = `
    <div class="verdict-bar">
      ${metric('Verdict', verdictLabel(trace.verdict), `metric-badge ${verdictClass(trace.verdict)}`)}
      ${metric('Tools', `${trace.tool_calls_used} / ${trace.optimal_tool_calls}`)}
      ${metric('Steps', trace.steps)}
      ${metric('Restraint', trace.restraint, `metric-badge ${restraintClass(trace.restraint)}`)}
      ${metric('Signals', behaviors)}
    </div>
  `;
}
