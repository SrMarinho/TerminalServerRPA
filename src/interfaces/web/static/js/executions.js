var _ws = null;
var _wsCallbacks = {};
var _stopCurrentWatch = null;

function _connectWS() {
  if (_ws && _ws.readyState !== WebSocket.CLOSED) _ws.close();
  var proto = location.protocol === "https:" ? "wss" : "ws";
  _ws = new WebSocket(proto + "://" + location.host + "/ws");
  _ws.onmessage = function(e) {
    try {
      var data = JSON.parse(e.data);
      if (data.type === 'pool:update') {
        refreshRunning();
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

function _renderExecDetail(id, exec) {
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
  if (exec.params && Object.keys(exec.params).length) {
    paramsRows = Object.entries(exec.params).map(function(kv) {
      var k = kv[0], v = kv[1];
      var display = (v && typeof v === 'object' && v.service)
        ? '<span style="color:var(--text-3);font-size:10px">credential</span> <span style="color:var(--text-1)">' + esc(v.service) + '</span>'
        : '<span style="color:var(--text-1)">' + esc(typeof v === 'object' ? JSON.stringify(v) : String(v)) + '</span>';
      return '<div style="display:flex;gap:12px;padding:5px 0;border-bottom:1px solid var(--line)">'
        + '<span style="color:var(--text-3);flex:0 0 160px;font-size:11px">' + esc(k) + '</span>'
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
    + '<div class="card p-6"><div class="label" style="margin-bottom:8px">LOG</div><div id="execLogBox" class="log-box" style="height:240px;overflow-y:auto">' + logEntries + '</div></div>'
    + resultHtml
    + '';

  var logBox = document.getElementById('execLogBox');
  if (logBox) logBox.scrollTop = logBox.scrollHeight;
  setTimeout(function() { _drawSnakeArrows(); _reapplyBreakpoints(); }, 0);
}

async function openExecutionDetail(id) {
  if (_stopCurrentWatch) { _stopCurrentWatch(); _stopCurrentWatch = null; }
  try { sessionStorage.setItem('senior-rpa.exec', id); sessionStorage.removeItem('senior-rpa.task'); } catch(e) {}

  document.getElementById('detailTaskName').textContent = '…';
  document.getElementById('detailContent').innerHTML = '<div class="text-sm" style="color:var(--text-2)">Carregando...</div>';
  switchPanel('task-detail');

  try {
    const exec = await api('GET', '/api/executions/' + id);
    _backFn = function() { openTaskDetail(exec.task_name); };
    _renderExecDetail(id, exec);

    if (!['completed', 'failed', 'cancelled'].includes(exec.status)) {
      _stopCurrentWatch = _watchExec(id, function(data) {
        if (data.type === 'execution:log') {
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
        } else {
          api('GET', '/api/executions/' + id).then(function(updated) {
            _renderExecDetail(id, updated);
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
          var borderColor = e.status === 'completed' ? 'var(--accent)' : e.status === 'failed' ? 'var(--danger)' : e.status === 'cancelled' ? 'var(--warn)' : 'var(--line)';
          var statusBadge = e.status === 'completed' ? 'background:var(--accent);color:var(--accent-on)' : e.status === 'failed' ? 'background:var(--danger);color:#fff' : e.status === 'cancelled' ? 'background:var(--warn);color:#000' : 'background:var(--accent-glow);color:var(--accent)';
          var dur = '';
          if (e.started_at && e.finished_at) {
            var diff = new Date(e.finished_at) - new Date(e.started_at);
            var sec = Math.floor(diff / 1000);
            dur = (sec >= 60 ? Math.floor(sec / 60) + 'm ' : '') + (sec % 60) + 's';
          }
          return '<div class="card p-4" onclick="openExecutionDetail(\'' + e.id + '\')" style="cursor:pointer;border-left:3px solid ' + borderColor + '">'
            + '<div class="flex items-start justify-between mb-3">'
            + '<span class="text-sm font-medium" style="color:var(--text-0)">' + esc(e.task_name) + '</span>'
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
