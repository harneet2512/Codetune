const TYPE_LABELS = {
  think: 'Think',
  tool_call: 'Tool',
  observation: 'Observe',
  answer: 'Answer',
  error: 'Error',
  warning_terminal: 'Warning',
  failure_terminal: 'Failure',
};

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
}

export function renderMiniFlow(container, nodes, totalNodes = nodes.length) {
  container.innerHTML = '';
  const visibleNodes = nodes.slice(0, 5);

  visibleNodes.forEach((node, index) => {
    const pill = document.createElement('span');
    pill.className = `mini-node ${node.type}`;
    pill.textContent = TYPE_LABELS[node.type] || node.type;
    container.appendChild(pill);

    if (index < visibleNodes.length - 1) {
      const arrow = document.createElement('span');
      arrow.className = 'mini-arrow';
      arrow.textContent = '→';
      container.appendChild(arrow);
    }
  });

  const remaining = Math.max(totalNodes - visibleNodes.length, 0);
  if (remaining > 0) {
    const extra = document.createElement('span');
    extra.className = 'mini-more';
    extra.textContent = `+${remaining} more`;
    container.appendChild(extra);
  }
}

export function renderFlowchart(container, nodes, onSelect, options = {}) {
  const { activeNodeId = null } = options;
  container.innerHTML = '';

  nodes.forEach((node, index) => {
    const wrap = document.createElement('div');
    wrap.className = 'flow-node fade-in';

    const step = document.createElement('div');
    step.className = 'flow-step';
    step.textContent = `Step ${index + 1}`;
    wrap.appendChild(step);

    const card = document.createElement('button');
    card.type = 'button';
    card.className = `flow-card ${node.type}${node.id === activeNodeId ? ' active' : ''}`;
    card.innerHTML = `
      <div class="flow-card-head">
        <div>
          <p class="flow-type">${esc(TYPE_LABELS[node.type] || node.type)}</p>
          <h4 class="flow-title">${esc(node.title)}</h4>
        </div>
        <div class="flow-card-meta">
          ${node.status ? `<span class="meta-chip">${esc(node.status)}</span>` : ''}
          <span class="flow-expand" aria-hidden="true">...</span>
        </div>
      </div>
      <p class="flow-summary">${esc(node.summary)}</p>
      ${node.decision ? `<p class="flow-decision">Decision: ${esc(node.decision)}</p>` : ''}
    `;
    card.addEventListener('click', () => onSelect(node));
    wrap.appendChild(card);
    container.appendChild(wrap);
  });
}
