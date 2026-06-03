var allTasks = [];
var currentTask = '';
var _execParamsCache = {};

// ---------------------------------------------------------------------------
// Task list
// ---------------------------------------------------------------------------

async function loadTasks() {
  try {
    const data = await api('GET', '/api/tasks');
    allTasks = data.available;
    document.getElementById('taskCount').textContent = String(allTasks.length).padStart(2, '0') + ' ROTINAS';
    renderTaskList(allTasks);
  } catch (e) { toast('Falha ao carregar tarefas', true); }
}

function filterTasks() {
  const q = document.getElementById('taskSearch').value.toLowerCase();
  renderTaskList(allTasks.filter(function(t) { return t.toLowerCase().indexOf(q) !== -1; }));
}

function renderTaskList(tasks) {
  document.getElementById('taskCards').innerHTML = tasks.length
    ? tasks.map(function(t, i) {
        return '<div class="task-tile fade-up" style="animation-delay:' + (i * 0.04) + 's" onclick="openTaskDetail(\'' + esc(t) + '\')">'
          + '<div class="flex items-center justify-between mb-3">'
          + '<div class="text-[10px] tabular-nums" style="color:var(--text-3);letter-spacing:.1em">ROTINA · ' + String(i + 1).padStart(2, '0') + '</div>'
          + '<div class="dot dot-idle"></div>'
          + '</div>'
          + '<div class="text-sm mb-1" style="color:var(--text-0);font-weight:500">' + esc(t) + '</div>'
          + '<div class="text-[11px]" style="color:var(--text-2)">clique para abrir</div>'
          + '</div>';
      }).join('')
    : '<div class="card p-8 text-center" style="border-style:dashed"><div class="text-sm" style="color:var(--text-1)">Nenhuma tarefa encontrada</div></div>';
}

// ---------------------------------------------------------------------------
// Task detail panel
// ---------------------------------------------------------------------------

async function openTaskDetail(name) {
  currentTask = name;
  _backFn = null;
  try { sessionStorage.setItem('TerminalServerRPA.task', name); } catch(e) {}
  document.getElementById('detailTaskName').textContent = name;
  document.getElementById('detailContent').innerHTML = '<div class="text-sm" style="color:var(--text-2)">Carregando...</div>';
  switchPanel('task-detail');

  try {
    const [formRes, executions] = await Promise.all([
      api('GET', '/api/tasks/' + encodeURIComponent(name) + '/form'),
      api('GET', '/api/executions'),
    ]);
    renderTaskDetail(name, formRes.html, executions);
  } catch (e) {
    document.getElementById('detailContent').innerHTML = '<div class="text-sm" style="color:var(--danger)">Erro: ' + esc(e.message) + '</div>';
  }
}

function renderTaskDetail(name, formHtml, executions) {
  var myExecs = (executions || []).filter(function(e) { return e.task_name === name; }).slice(0, 10);
  var histHtml = myExecs.length
    ? myExecs.map(function(e) {
        var sc = 'dot-' + e.status;
        var sl = STATUS_PT[e.status] || e.status;
        var st = e.started_at ? e.started_at.slice(11, 19) : '--:--:--';
        var dur = '';
        if (e.started_at && e.finished_at) {
          var diff = new Date(e.finished_at) - new Date(e.started_at);
          var sec = Math.floor(diff / 1000);
          dur = (sec >= 60 ? Math.floor(sec / 60) + 'm ' : '') + (sec % 60) + 's';
        } else if (e.started_at) {
          var diff2 = Date.now() - new Date(e.started_at);
          var sec2 = Math.floor(diff2 / 1000);
          dur = (sec2 >= 60 ? Math.floor(sec2 / 60) + 'm ' : '') + (sec2 % 60) + 's';
        }
        return '<div class="cred-row" style="cursor:pointer;margin-bottom:6px" onclick="openExecutionDetail(\'' + e.id + '\')">'
          + '<div class="flex items-center gap-3 min-w-0">'
          + '<span class="dot ' + sc + '" style="flex-shrink:0"></span>'
          + '<div class="min-w-0"><div class="text-sm" style="color:var(--text-0)">' + esc(e.task_name) + '</div>'
          + '<div class="text-[11px]" style="color:var(--text-2)">' + sl + (dur ? ' · ' + dur : '') + '</div></div>'
          + '</div>'
          + '<span class="text-[10px] tabular-nums hist-time">' + st + '</span>'
          + '</div>';
      }).join('')
    : '<div class="text-xs" style="color:var(--text-3)">Nenhuma execução anterior.</div>';

  document.getElementById('detailContent').innerHTML = ''
    + '<div class="card p-6"><div class="label" style="margin-bottom:12px">PARÂMETROS</div>'
    + (formHtml || '<div class="text-sm" style="color:var(--text-2)">Sem parâmetros.</div>')
    + '<div class="flex gap-2 mt-4">'
    + '<button class="btn btn-ghost" onclick="saveDetailConfig()"><svg width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>salvar config</button>'
    + '<button class="btn btn-primary" onclick="runDetailTask()"><svg width="11" height="11" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>executar</button>'
    + '</div></div>'
    + '<div class="card p-6"><div class="label" style="margin-bottom:12px">ÚLTIMAS EXECUÇÕES</div>' + histHtml + '</div>';

  _initFormContainer(document.getElementById('detailContent'), name);
}

function collectDetailParams() { return _collectParams(document.getElementById('detailContent')); }

async function saveDetailConfig() {
  var p = collectDetailParams(); if (!p) return;
  await api('POST', '/api/tasks/' + encodeURIComponent(currentTask) + '/config', p);
  toast('Config salva');
}

async function runDetailTask() {
  var p = collectDetailParams(); if (!p) return;
  await api('POST', '/api/tasks/' + encodeURIComponent(currentTask) + '/config', p);
  var res = await api('POST', '/api/run/' + encodeURIComponent(currentTask), p);
  toast('Tarefa iniciada');
  openExecutionDetail(res.task_id);
}

async function rerunExec(execId) {
  var entry = _execParamsCache[execId];
  if (!entry) { toast('Params não encontrados', true); return; }
  try {
    var bps = Object.keys(_execBreakpoints).filter(function(k) { return _execBreakpoints[k]; });
    var res = await api('POST', '/api/run/' + encodeURIComponent(entry.taskName), Object.assign({}, entry.params, { _breakpoints: bps }));
    toast('Re-executando');
    openExecutionDetail(res.task_id);
  } catch (e) { toast('Erro: ' + e.message, true); }
}

// ---------------------------------------------------------------------------
// Config modal
// ---------------------------------------------------------------------------

async function openConfigModal(name) {
  currentTask = name;
  document.getElementById('configModalTitle').textContent = name;
  document.getElementById('configFields').innerHTML = '<div class="text-sm" style="color:var(--text-2)">Carregando...</div>';
  document.getElementById('configModal').classList.remove('hidden');
  document.getElementById('configModal').classList.add('flex');
  try {
    var res = await api('GET', '/api/tasks/' + encodeURIComponent(name) + '/form?wrap_class=mb-4');
    document.getElementById('configFields').innerHTML = res.html || '';
    _initFormContainer(document.getElementById('configFields'), name);
  } catch (e) {
    document.getElementById('configFields').innerHTML = '<div class="text-sm" style="color:var(--danger)">Erro ao carregar: ' + e.message + '</div>';
  }
}

function closeConfigModal() {
  document.getElementById('configModal').classList.add('hidden');
  document.getElementById('configModal').classList.remove('flex');
  currentTask = '';
}

function collectConfigParams() { return _collectParams(document.getElementById('configFields')); }

async function saveModalConfig() {
  var params = collectConfigParams(); if (!params) return;
  try {
    await api('POST', '/api/tasks/' + encodeURIComponent(currentTask) + '/config', params);
    toast('Config salva');
    logLine('config salva: ' + currentTask, 'info');
    closeConfigModal();
  } catch (e) { toast('Erro ao salvar: ' + e.message, true); }
}

async function saveAndRun() {
  var params = collectConfigParams(); if (!params) return;
  try {
    await api('POST', '/api/tasks/' + encodeURIComponent(currentTask) + '/config', params);
    const res = await api('POST', '/api/run/' + encodeURIComponent(currentTask), params);
    toast('Tarefa iniciada');
    closeConfigModal();
    openExecutionDetail(res.task_id);
  } catch (e) { toast('Erro: ' + e.message, true); }
}
