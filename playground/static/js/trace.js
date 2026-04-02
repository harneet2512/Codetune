/**
 * Raw trace renderer — syntax-highlighted trace output.
 */

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]
  );
}

function highlightLine(line) {
  let html = esc(line);
  html = html.replace(/(&lt;think&gt;.*?&lt;\/think&gt;)/g, '<span class="trace-think">$1</span>');
  html = html.replace(/(&lt;tool_call&gt;.*?&lt;\/tool_call&gt;)/g, '<span class="trace-tool">$1</span>');
  html = html.replace(/(&lt;observation&gt;.*?&lt;\/observation&gt;)/g, '<span class="trace-observation">$1</span>');
  html = html.replace(/(&lt;answer&gt;.*?&lt;\/answer&gt;)/g, '<span class="trace-answer">$1</span>');
  return html;
}

export function renderRawTrace(container, rawTrace) {
  const lines = String(rawTrace || '').split('\n');
  container.innerHTML = lines
    .map((line, i) =>
      `<span class="trace-line"><span class="trace-line-no">${String(i + 1).padStart(2, '0')}</span><span>${highlightLine(line)}</span></span>`
    )
    .join('');
}
