/**
 * Flowchart renderer — vertical timeline with typed node cards.
 */

const TYPE_LABELS = {
  think: 'Think',
  tool_call: 'Tool Call',
  observation: 'Observe',
  answer: 'Answer',
  error: 'Error',
  warning_terminal: 'Warning',
  failure_terminal: 'Failure',
};

function esc(v) {
  return String(v ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]
  );
}

/**
 * @param {HTMLElement} el - container
 * @param {Array} nodes - trace nodes
 * @param {Function} onSelect - callback(node, index)
 * @param {Object} opts - { activeNodeId }
 */
export function renderFlowchart(el, nodes, onSelect, opts = {}) {
  const { activeNodeId } = opts;
  el.innerHTML = '';

  nodes.forEach((node, i) => {
    const wrap = document.createElement('div');
    wrap.className = `flow-node ${node.type}`;

    const card = document.createElement('button');
    card.type = 'button';
    card.className = `flow-card ${node.type}${node.id === activeNodeId ? ' active' : ''}`;

    let html = `<p class="flow-type">${esc(TYPE_LABELS[node.type] || node.type)}</p>`;
    html += `<p class="flow-title">${esc(node.title)}</p>`;
    if (node.summary) {
      html += `<p class="flow-summary">${esc(node.summary)}</p>`;
    }
    if (node.decision) {
      html += `<p class="flow-decision">${esc(node.decision)}</p>`;
    }

    card.innerHTML = html;
    card.addEventListener('click', () => onSelect(node, i));

    wrap.appendChild(card);
    el.appendChild(wrap);
  });
}
