var _ws = null;
var _wsCallbacks = {};
var _stopCurrentWatch = null;
var _screenshotSubExecId = null;

function toggleScreenModal() {
  var modal = document.getElementById('screenModal');
  var btn = document.getElementById('screenDrawerBtn');
  if (!modal || !btn) return;
  var execId = btn.dataset.execId;
  if (modal.classList.contains('hidden')) {
    modal.classList.remove('hidden');
    btn.textContent = 'fechar tela';
    if (_ws && _ws.readyState === WebSocket.OPEN && execId) {
      _ws.send(JSON.stringify({ type: 'screenshot:subscribe', execution_id: execId }));
      _screenshotSubExecId = execId;
    }
    _renderScreenFlow(execId);
  } else {
    modal.classList.add('hidden');
    btn.textContent = 'visualizar tela';
    _unsubscribeScreenshot();
  }
}

function _renderScreenFlow(execId) {
  var container = document.getElementById('screenFlow');
  if (!container) return;
  api('GET', '/api/executions/' + execId).then(function(exec) {
    if (!exec.steps || !exec.steps.length) return;
    var cls = { completed: 'c', running: 'r', failed: 'f' };
    var html = '';
    var steps = exec.steps;
    for (var i = 0; i < steps.length; i++) {
      var s = steps[i];
      var t = s.timestamp ? s.timestamp.slice(11, 19) : '';
      html += '<div class="flow-node ' + (cls[s.status] || 'p') + '" data-step="' + esc(s.name) + '"'
        + ' title="' + esc(t || s.name) + '"'
        + ' style="display:flex;align-items:center;gap:6px;flex-shrink:0;white-space:nowrap">'
        + '<span style="font-size:11px;font-weight:700;color:var(--text-3);flex-shrink:0">' + (i + 1) + '</span>'
        + '<span>' + esc(s.name) + '</span></div>';
      if (i < steps.length - 1) {
        html += '<div style="flex-shrink:0;padding:0 4px;color:var(--line-2)">→</div>';
      }
    }
    container.innerHTML = html;
    _scrollToActiveStep();
  }).catch(function() {});
}

function _scrollToActiveStep() {
  var container = document.getElementById('screenFlow');
  var scroll = document.getElementById('screenFlowScroll');
  if (!container || !scroll) return;
  var active = container.querySelector('.flow-node.r');
  if (!active) active = container.querySelector('.flow-node.c:last-of-type');
  if (active) {
    var nodeLeft = active.offsetLeft;
    var nodeWidth = active.offsetWidth;
    var scrollWidth = scroll.offsetWidth;
    scroll.scrollLeft = nodeLeft - (scrollWidth / 2) + (nodeWidth / 2);
  }
}

function _unsubscribeScreenshot() {
  if (_ws && _ws.readyState === WebSocket.OPEN && _screenshotSubExecId) {
    _ws.send(JSON.stringify({ type: 'screenshot:unsubscribe', execution_id: _screenshotSubExecId }));
    _screenshotSubExecId = null;
  }
  var modal = document.getElementById('screenModal');
  var btn = document.getElementById('screenDrawerBtn');
  if (modal) modal.classList.add('hidden');
  if (btn) btn.textContent = 'visualizar tela';
}

function _connectWS() {
  if (_ws && _ws.readyState !== WebSocket.CLOSED) _ws.close();
  var proto = location.protocol === "https:" ? "wss" : "ws";
  var token = _getToken();
  _ws = new WebSocket(proto + "://" + location.host + "/ws?token=" + encodeURIComponent(token));
  _ws.onmessage = function(e) {
    try {
      var data = JSON.parse(e.data);
      if (data.type === 'pool:update') {
        refreshRunning();
        return;
      }
      if (data.type === 'pool:queue') {
        var qEl = document.getElementById('queueCountSidebar');
        if (qEl) qEl.textContent = data.size > 0 ? data.size + ' na fila' : '';
        return;
      }
      if (data.type && data.execution_id && _wsCallbacks[data.execution_id]) {
        _wsCallbacks[data.execution_id](data);
      }
    } catch(x) {}
  };
  _ws.onclose = function() { setTimeout(_connectWS, 10000); };
}

function _watchExec(id, cb) {
  _wsCallbacks[id] = cb;
  return function() { delete _wsCallbacks[id]; };
}

async function runSnippet(execId) {
  var code = (document.getElementById('snippetCode') || {value:''}).value;
  var status = document.getElementById('snippetStatus');
  var output = document.getElementById('snippetOutput');
  if (!code.trim()) return;
  status.textContent = 'executando...';
  status.style.color = 'var(--text-2)';
  output.textContent = '';
  try {
    var res = await api('POST', '/api/executions/' + execId + '/snippet', { code: code });
    status.textContent = res.ok ? 'ok' : 'erro';
    status.style.color = res.ok ? 'var(--accent)' : 'var(--danger)';
    output.textContent = (res.output || []).join('\n') + (res.error ? '\n' + res.error : '');
  } catch(e) {
    status.textContent = 'erro';
    status.style.color = 'var(--danger)';
    output.textContent = e.message;
  }
}

async function _renderExecDetail(id, exec) {
  var statusText = STATUS_PT[exec.status] || exec.status;
  var stepsHtml = renderFlowChart(exec.steps, id);

  var logEntries = exec.logs && exec.logs.length
    ? exec.logs.map(function(l) {
        var lvlColor = { error: 'var(--danger)', warn: 'var(--warn)', info: 'var(--text-1)' };
        return '<div style="padding-left:8px"><span style="color:var(--text-3)">[' + (l.timestamp ? l.timestamp.slice(11, 19) : '') + ']</span> '
          + '<span style="color:' + (lvlColor[l.level] || 'var(--text-1)') + '">' + esc(l.message) + '</span></div>';
      }).join('')
    : '';

  _execParamsCache[id] = { taskName: exec.task_name, params: exec.params };
  var paramsRows = '';
  var displayParams = exec.params_display && Object.keys(exec.params_display).length ? exec.params_display : exec.params;
  if (exec.params && Object.keys(exec.params).length) {
    var schema = [], visibility = {};
    try {
      var results = await Promise.all([
        api('GET', '/api/tasks/' + encodeURIComponent(exec.task_name) + '/schema'),
        api('POST', '/api/tasks/' + encodeURIComponent(exec.task_name) + '/visibility', { params: exec.params }),
      ]);
      schema = results[0] || [];
      visibility = results[1] || {};
    } catch(e) {}

    var labelMap = {};
    schema.forEach(function(f) { if (f.name && f.label) labelMap[f.name] = f.label; });

    paramsRows = Object.entries(exec.params).filter(function(kv) {
      var k = kv[0];
      return !(k in visibility) || visibility[k];
    }).map(function(kv) {
      var k = kv[0], v = kv[1];
      var resolved = displayParams[k];
      var label = labelMap[k] || k;
      var display = (v && typeof v === 'object' && v.service)
        ? '<span style="color:var(--text-3);font-size:10px">credential</span> <span style="color:var(--text-1)">' + esc(v.service) + '</span>'
        : '<span style="color:var(--text-1)">' + esc(typeof resolved === 'object' ? JSON.stringify(resolved) : String(resolved ?? v)) + '</span>';
      return '<div style="display:flex;gap:12px;padding:5px 0;border-bottom:1px solid var(--line)">'
        + '<span style="color:var(--text-3);flex:0 0 160px;font-size:11px">' + esc(label) + '</span>'
        + display + '</div>';
    }).join('');
  }
  var paramsHtml = paramsRows
    ? '<div class="card p-6"><div class="flex items-center justify-between" style="margin-bottom:8px">'
      + '<div class="label" style="margin-bottom:0">CONFIGURAÇÃO</div>'
      + '<button class="btn btn-primary" style="padding:6px 14px;font-size:11px" onclick="rerunExec(\'' + id + '\')">'
      + '<svg width="10" height="10" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>re-executar</button>'
      + '</div>' + paramsRows + '</div>'
    : '';

  var resultHtml = exec.result
    ? '<div class="card p-6"><div class="flex items-center justify-between mb-2"><div class="label" style="margin-bottom:0">RESULTADO</div>'
      + '<button class="btn btn-ghost" style="padding:4px 8px;font-size:10px" onclick="var t=this.nextElementSibling;if(t.style.display===\'none\'){t.style.display=\'block\';this.textContent=\'ocultar\'}else{t.style.display=\'none\';this.textContent=\'mostrar\'}">ocultar</button>'
      + '<textarea readonly style="position:absolute;left:-9999px" id="copyTarget-' + id + '">' + esc(JSON.stringify(exec.result, null, 2)) + '</textarea>'
      + '</div>'
      + '<button class="btn btn-ghost" style="padding:4px 8px;font-size:10px;float:right" onclick="var t=document.getElementById(\'copyTarget-' + id + '\');t.select();navigator.clipboard.writeText(t.value);toast(\'Copiado\')">📋 copiar</button>'
      + '<pre id="resultDisplay-' + id + '" class="text-xs" style="white-space:pre-wrap;color:var(--text-1)">' + renderJson(exec.result, 0) + '</pre></div>'
    : '';

  var isActive = exec.status === 'running' || exec.status === 'paused';

  document.getElementById('detailTaskName').textContent = exec.task_name + ' (' + id + ')';
  document.getElementById('detailContent').innerHTML = ''
    + '<div class="card p-6"><span class="label" style="margin-bottom:4px">STATUS</span><span class="text-sm" style="color:var(--text-0)">' + statusText + '</span></div>'
    + paramsHtml
    + '<div class="card p-6"><div class="flex items-center justify-between" style="margin-bottom:8px"><div class="label" style="margin-bottom:0">PASSOS</div>'
    + (isActive ? '<div class="flex gap-2">'
      + '<button class="btn btn-ghost" style="padding:5px 12px;font-size:11px" ' + (exec.status !== 'running' ? 'disabled' : '') + ' onclick="pauseById(\'' + id + '\')">pausar</button>'
      + '<button class="btn btn-ghost" style="padding:5px 12px;font-size:11px" ' + (exec.status !== 'paused' ? 'disabled' : '') + ' onclick="resumeById(\'' + id + '\')">continuar</button>'
      + '<button class="btn btn-ghost" style="padding:5px 12px;font-size:11px" ' + (exec.status !== 'paused' ? 'disabled' : '') + ' onclick="skipById(\'' + id + '\')">pular</button>'
      + '<button class="btn btn-danger" style="padding:5px 12px;font-size:11px" onclick="cancelById(\'' + id + '\')">cancelar</button>'
      + '</div>' : '')
    + '</div>' + stepsHtml + '</div>'
    + '<div class="card p-6"><div class="flex items-center justify-between" style="margin-bottom:8px"><div class="label" style="margin-bottom:0">LOG</div>'
    + '<button class="btn btn-ghost" style="padding:4px 8px;font-size:10px" onclick="var btn=this,b=document.getElementById(\'execLogBox\');navigator.clipboard.writeText(b.innerText);btn.textContent=\'copiado\';var t=setTimeout(function(){btn.textContent=\'📋\'},2000);btn.addEventListener(\'mouseenter\',function h(){btn.textContent=\'📋\';clearTimeout(t);btn.removeEventListener(\'mouseenter\',h)},{once:true})">📋</button>'
    + '</div><div id="execLogBox" class="log-box" style="height:240px;overflow-y:auto">' + logEntries + '</div></div>'
    + (exec.result && exec.result.arquivo
        ? '<div class="card p-6"><div class="flex items-center justify-between" style="margin-bottom:8px"><div class="label" style="margin-bottom:0">ARQUIVO GERADO</div>'
          + '<button class="btn btn-ghost" style="padding:4px 8px;font-size:10px" onclick="var btn=this;navigator.clipboard.writeText(\'' + esc(exec.result.arquivo) + '\');btn.textContent=\'copiado\';var t=setTimeout(function(){btn.textContent=\'📋\'},2000);btn.addEventListener(\'mouseenter\',function h(){btn.textContent=\'📋\';clearTimeout(t);btn.removeEventListener(\'mouseenter\',h)},{once:true})">📋</button>'
          + '</div><span style="font-family:\'JetBrains Mono\',monospace;font-size:12px;color:var(--text-0)">' + esc(exec.result.arquivo) + '</span></div>'
        : '')
    + resultHtml
    + '';

  var drawerBtn = document.getElementById('screenDrawerBtn');
  if (drawerBtn) {
    if (isActive) { drawerBtn.classList.remove('hidden'); drawerBtn.dataset.execId = id; }
    else { drawerBtn.classList.add('hidden'); }
  }

  var logBox = document.getElementById('execLogBox');
  if (logBox) logBox.scrollTop = logBox.scrollHeight;
  setTimeout(function() { _drawSnakeArrows(); _reapplyBreakpoints(); }, 0);
}

async function openExecutionDetail(id) {
  if (_stopCurrentWatch) { _stopCurrentWatch(); _stopCurrentWatch = null; }
  _unsubscribeScreenshot();
  try { sessionStorage.setItem('TerminalServerRPA.exec', id); sessionStorage.removeItem('TerminalServerRPA.task'); } catch(e) {}

  document.getElementById('detailTaskName').textContent = '…';
  document.getElementById('detailContent').innerHTML = '<div class="text-sm" style="color:var(--text-2)">Carregando...</div>';
  switchPanel('task-detail');

  try {
    const exec = await api('GET', '/api/executions/' + id);
    _backFn = function() { openTaskDetail(exec.task_name); };
    _execBreakpoints = {};
    if (exec.breakpoints && exec.breakpoints.length) {
      exec.breakpoints.forEach(function(s) { _execBreakpoints[s] = true; });
    }
    await _renderExecDetail(id, exec);

    if (!['completed', 'failed', 'cancelled'].includes(exec.status)) {
      _stopCurrentWatch = _watchExec(id, function(data) {
        if (data.type === 'execution:screenshot') {
          var img = document.getElementById('execScreenshot');
          if (img) img.src = 'data:' + (data.mime || 'image/png') + ';base64,' + data.data;
        } else if (data.type === 'execution:log') {
          var box = document.getElementById('execLogBox');
          if (box) {
            var lvlColor = { error: 'var(--danger)', warn: 'var(--warn)', info: 'var(--text-1)' };
            var div = document.createElement('div');
            div.style.paddingLeft = '8px';
            div.innerHTML = '<span style="color:var(--text-3)">[' + (data.timestamp || '').slice(11, 19) + ']</span> '
              + '<span style="color:' + (lvlColor[data.level] || 'var(--text-1)') + '">' + esc(data.message) + '</span>';
            box.appendChild(div);
            box.scrollTop = box.scrollHeight;
          }
        } else if (data.type === 'execution:step') {
          var nodeCls = { running: 'r', completed: 'c', failed: 'f', cancelled: 'f', pending: 'p' };
          var grid = document.getElementById('snake-grid');
          var found = grid ? grid.querySelector('[data-step="' + data.name.replace(/"/g, '\\"') + '"]') : null;
          if (!found) {
            var allNodes = document.querySelectorAll('.flow-node');
            for (var ni = 0; ni < allNodes.length; ni++) {
              if (allNodes[ni].textContent.trim() === data.name) { found = allNodes[ni]; break; }
            }
          }
          if (found) {
            var bpClass = _execBreakpoints[data.name] ? ' bp' : '';
            found.className = 'flow-node ' + (nodeCls[data.status] || 'p') + bpClass;
            if (data.timestamp) found.title = data.timestamp.slice(11, 19);
            _drawSnakeArrows();
          }
          var modal = document.getElementById('screenModal');
          if (modal && !modal.classList.contains('hidden')) {
            var sfNode = document.getElementById('screenFlow');
            if (sfNode) {
              var sfFound = sfNode.querySelector('[data-step="' + data.name.replace(/"/g, '\\"') + '"]');
              if (sfFound) {
                sfFound.className = 'flow-node ' + (nodeCls[data.status] || 'p');
                _scrollToActiveStep();
              }
            }
          }
        } else {
          api('GET', '/api/executions/' + id).then(async function(updated) {
            await _renderExecDetail(id, updated);
            if (['completed', 'failed', 'cancelled'].includes(updated.status)) {
              if (_stopCurrentWatch) { _stopCurrentWatch(); _stopCurrentWatch = null; }
            }
          });
        }
      });
    }
  } catch (e) { toast('Erro: ' + e.message, true); }
}

async function loadHistory() {
  try {
    const data = await api('GET', '/api/executions');
    document.getElementById('historyList').innerHTML = data.length
      ? data.map(function(e) {
          var statusClass = 'dot-' + e.status;
          var statusText = STATUS_PT[e.status] || e.status;
          var start = e.started_at ? e.started_at.slice(11, 19) : '--:--:--';
          var end = e.finished_at ? e.finished_at.slice(11, 19) : '—';
          var isRunning = e.status === 'running' || e.status === 'paused';
          var borderColor = e.status === 'completed' ? 'var(--accent)' : e.status === 'failed' ? 'var(--danger)' : e.status === 'cancelled' ? 'var(--warn)' : isRunning ? 'var(--accent)' : 'var(--line)';
          var statusBadge = e.status === 'completed' ? 'background:var(--accent);color:var(--accent-on)' : e.status === 'failed' ? 'background:var(--danger);color:#fff' : e.status === 'cancelled' ? 'background:var(--warn);color:#000' : 'background:var(--accent-glow);color:var(--accent)';
          var dur = '';
          if (e.started_at && e.finished_at) {
            var diff = new Date(e.finished_at) - new Date(e.started_at);
            var sec = Math.floor(diff / 1000);
            dur = (sec >= 60 ? Math.floor(sec / 60) + 'm ' : '') + (sec % 60) + 's';
          }
          var cardExtra = isRunning ? 'background:color-mix(in srgb,var(--accent) 4%,var(--bg-1));border-left:3px solid ' + borderColor + ';box-shadow:0 0 0 1px var(--accent-glow)' : 'border-left:3px solid ' + borderColor;
          var liveIndicator = isRunning ? '<span class="pulse" style="display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--accent);margin-right:6px;flex-shrink:0;color:var(--accent)"></span>' : '';
          return '<div class="card p-4" onclick="openExecutionDetail(\'' + e.id + '\')" style="cursor:pointer;' + cardExtra + '">'
            + '<div class="flex items-start justify-between mb-3">'
            + '<span class="text-sm font-medium flex items-center" style="color:var(--text-0)">' + liveIndicator + esc(e.task_name) + '</span>'
            + '<span class="text-[10px] px-2 py-0.5 rounded-sm font-semibold ml-2 shrink-0" style="' + statusBadge + '">' + statusText + '</span>'
            + '</div>'
            + '<div class="flex items-center gap-3 text-[10px] tabular-nums hist-time">'
            + '<span>início: ' + start + '</span>'
            + (e.finished_at ? '<span>fim: ' + end + '</span>' : '')
            + (dur ? '<span>duração: ' + dur + '</span>' : '')
            + '</div>'
            + '</div>';
        }).join('')
      : '<div class="card p-8 text-center" style="border-style:dashed"><div class="text-sm" style="color:var(--text-1)">Nenhuma execução ainda.</div></div>';
  } catch (e) { toast('Falha ao carregar histórico', true); }
}
