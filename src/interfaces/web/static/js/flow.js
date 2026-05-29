var SNAKE_COLS = 4;
var _execBreakpoints = {};

async function toggleBreakpoint(execId, stepName, el) {
  var enabled = !_execBreakpoints[stepName];
  _execBreakpoints[stepName] = enabled;
  el.classList.toggle('bp', enabled);
  el.title = enabled ? 'Breakpoint: ' + stepName : stepName;
  try { await api('POST', '/api/executions/' + execId + '/breakpoint', { step: stepName, enabled: enabled }); }
  catch(e) { toast('Erro breakpoint: ' + e.message, true); }
}

function _reapplyBreakpoints() {
  Object.keys(_execBreakpoints).forEach(function(name) {
    if (!_execBreakpoints[name]) return;
    var grid = document.getElementById('snake-grid');
    if (!grid) return;
    var node = grid.querySelector('[data-step="' + name.replace(/"/g, '\\"') + '"]');
    if (node) node.classList.add('bp');
  });
}

function renderFlowChart(steps, execId) {
  if (!steps || !steps.length) return '<div class="text-xs" style="color:var(--text-3)">Nenhum passo registrado.</div>';

  var cls = { completed: "c", running: "r", failed: "f" };
  var N = SNAKE_COLS;

  var phases = {};
  var phaseOrder = [];
  for (var i = 0; i < steps.length; i++) {
    var ph = steps[i].phase || "";
    if (!phases[ph]) { phases[ph] = []; phaseOrder.push(ph); }
    phases[ph].push(steps[i]);
  }
  var hasPhases = phaseOrder.some(function(k) { return k !== ""; });

  var gridItems = [];
  var curRow = 0, posInRow = 0, goingRight = true;
  var rowDirs = {}, rowCounts = {};

  function pushStep(s) {
    rowDirs[curRow] = goingRight;
    rowCounts[curRow] = (rowCounts[curRow] || 0) + 1;
    gridItems.push({ type: 'step', step: s, row: curRow, posInRow: posInRow, col: 0 });
    posInRow++;
    if (posInRow >= N) { posInRow = 0; curRow++; goingRight = !goingRight; }
  }

  if (hasPhases) {
    for (var pi = 0; pi < phaseOrder.length; pi++) {
      var phaseName = phaseOrder[pi];
      var phaseSteps = phases[phaseName];
      if (posInRow !== 0) { curRow++; posInRow = 0; }
      goingRight = (pi % 2 === 0);
      if (phaseName) {
        gridItems.push({ type: 'phase', name: phaseName, steps: phaseSteps, row: curRow });
        curRow++;
      }
      for (var j = 0; j < phaseSteps.length; j++) pushStep(phaseSteps[j]);
    }
  } else {
    for (var k = 0; k < steps.length; k++) pushStep(steps[k]);
  }

  for (var gi2 = 0; gi2 < gridItems.length; gi2++) {
    var it = gridItems[gi2];
    if (it.type !== 'step') continue;
    var ltr = rowDirs[it.row];
    var cnt = rowCounts[it.row];
    it.col = ltr ? it.posInRow : (cnt - 1 - it.posInRow);
  }

  var stepNum = 0;
  var html = '<div class="snake-grid" id="snake-grid" style="--cols:' + N + '">';
  html += '<svg id="snake-svg" style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none;overflow:visible;z-index:0">'
    + '<defs>'
    + '<marker id="arr" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto"><circle cx="4" cy="4" r="3" fill="var(--line-2)"/></marker>'
    + '<marker id="arr-act" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto"><circle cx="4" cy="4" r="3" fill="var(--accent)"/></marker>'
    + '</defs></svg>';

  for (var gi = 0; gi < gridItems.length; gi++) {
    var item = gridItems[gi];
    if (item.type === 'phase') {
      var done = item.steps.filter(function(s) { return s.status === 'completed'; }).length;
      html += '<div class="snake-phase-header" style="grid-column:1/' + (N + 1) + ';grid-row:' + (item.row + 1) + '">'
        + '<span class="phase-title">' + esc(item.name) + '</span>'
        + '<span class="phase-count">' + done + '/' + item.steps.length + '</span>'
        + '</div>';
    } else {
      var s = item.step;
      stepNum++;
      var t = s.timestamp ? s.timestamp.slice(11, 19) : '';
      var gridStyle = 'grid-column:' + (item.col + 1) + ';grid-row:' + (item.row + 1) + (execId ? ';cursor:pointer' : '');
      html += '<div class="flow-node ' + (cls[s.status] || 'p') + '"'
        + ' data-step="' + esc(s.name) + '"'
        + ' title="' + esc(t || s.name) + '"'
        + ' style="' + gridStyle + ';display:flex;align-items:center;gap:6px"'
        + (execId ? ' onclick="toggleBreakpoint(\'' + execId + '\',\'' + s.name.replace(/'/g, "\\'") + '\',this)"' : '')
        + '><span style="font-size:11px;font-weight:700;color:var(--text-3);flex-shrink:0;line-height:1.4">' + stepNum + '</span><span style="line-height:1.4">' + esc(s.name) + '</span></div>';
    }
  }

  html += '</div>';
  return html;
}

function _drawSnakeArrows() {
  var grid = document.getElementById('snake-grid');
  var svg = document.getElementById('snake-svg');
  if (!grid || !svg) return;

  var nodes = Array.from(grid.querySelectorAll('.flow-node'));
  if (nodes.length < 2) return;

  var gridRect = grid.getBoundingClientRect();
  var defs = svg.querySelector('defs');
  while (svg.lastChild && svg.lastChild !== defs) svg.removeChild(svg.lastChild);

  for (var i = 0; i < nodes.length - 1; i++) {
    var ra = nodes[i].getBoundingClientRect();
    var rb = nodes[i + 1].getBoundingClientRect();

    var sameRow = Math.abs(ra.top - rb.top) < ra.height * 0.5;
    var isAct = nodes[i].classList.contains('r') || nodes[i + 1].classList.contains('r');
    var stroke = isAct ? 'var(--accent)' : 'var(--line-2)';
    var marker = isAct ? 'url(#arr-act)' : 'url(#arr)';

    if (sameRow) {
      var goingRight = rb.left > ra.left;
      var line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', (goingRight ? ra.right : ra.left) - gridRect.left);
      line.setAttribute('y1', ra.top + ra.height / 2 - gridRect.top);
      line.setAttribute('x2', (goingRight ? rb.left : rb.right) - gridRect.left);
      line.setAttribute('y2', rb.top + rb.height / 2 - gridRect.top);
      line.setAttribute('stroke', stroke);
      line.setAttribute('stroke-width', '1.5');
      line.setAttribute('marker-end', marker);
      svg.appendChild(line);
    } else {
      var x1 = ra.left + ra.width / 2 - gridRect.left;
      var y1 = ra.bottom - gridRect.top;
      var x2 = rb.left + rb.width / 2 - gridRect.left;
      var y2 = rb.top - gridRect.top;
      var ymid = (y1 + y2) / 2;
      var path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', 'M' + x1 + ',' + y1 + ' C' + x1 + ',' + ymid + ' ' + x2 + ',' + ymid + ' ' + x2 + ',' + y2);
      path.setAttribute('stroke', stroke);
      path.setAttribute('stroke-width', '1.5');
      path.setAttribute('fill', 'none');
      path.setAttribute('marker-end', marker);
      svg.appendChild(path);
    }
  }
}
