const API = '';

async function api(method, path, body) {
  const opts = { method, headers: {} };
  if (body) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  const res = await fetch(API + path, opts);
  if (!res.ok) { const err = await res.text(); throw new Error(err); }
  return res.status === 204 ? null : res.json();
}

function toast(msg, isError) {
  const el = document.getElementById('toast');
  el.textContent = (isError ? '✕  ' : '✓  ') + msg;
  el.className = 'fixed bottom-6 right-6 toast translate-y-0 opacity-100 transition-all duration-300 z-50 pointer-events-none' + (isError ? ' error' : '');
  clearTimeout(el._t);
  el._t = setTimeout(() => { el.className = 'fixed bottom-6 right-6 toast translate-y-32 opacity-0 transition-all duration-300 z-50 pointer-events-none' + (isError ? ' error' : ''); }, 3000);
}

function logLine(msg, type) {
  const log = document.getElementById('log');
  if (!log) return;
  const time = new Date().toTimeString().slice(0, 8);
  const colors = { error: 'var(--danger)', warn: 'var(--warn)', success: 'var(--accent)', info: 'var(--info)' };
  const line = document.createElement('div');
  line.style.paddingLeft = '16px';
  line.innerHTML = '<span style="color:var(--text-3)">[' + time + ']</span> <span style="color:' + (colors[type] || 'var(--text-1)') + '">' + msg + '</span>';
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

const PANEL_KEY = 'senior-rpa.panel';
const PERSIST_PANELS = ['tasks', 'credentials', 'history'];
var _prevPanel = 'tasks';

function switchPanel(name) {
  if (name !== 'task-detail' && _stopCurrentWatch) { _stopCurrentWatch(); _stopCurrentWatch = null; }
  if (PERSIST_PANELS.includes(name)) _prevPanel = name;
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  var btn = document.querySelector('.nav-btn[data-panel="' + name + '"]');
  if (btn) btn.classList.add('active');
  document.querySelectorAll('.panel').forEach(p => p.classList.add('hidden'));
  document.getElementById('panel-' + name).classList.remove('hidden');
  if (name === 'tasks') loadTasks();
  if (name === 'credentials') loadCredentials();
  if (name === 'history') loadHistory();
  if (PERSIST_PANELS.includes(name)) try { sessionStorage.setItem(PANEL_KEY, name); } catch(e) {}
}

var _backFn = null;
function goBack() {
  if (_backFn) { var fn = _backFn; _backFn = null; fn(); }
  else switchPanel(_prevPanel);
}

const STATUS_PT = { idle: 'ocioso', running: 'executando', paused: 'pausado', completed: 'concluído', failed: 'falhou', cancelled: 'cancelado' };

function updateSidebarRunning(tasks) {
  const entries = Object.values(tasks);
  const active = entries.filter(r => r.status === 'running' || r.status === 'paused');
  const dot = document.getElementById('statusDot');
  const text = document.getElementById('statusText');
  const sidebar = document.getElementById('runningCountSidebar');
  if (active.length === 0) {
    dot.className = 'dot dot-idle';
    text.textContent = 'ocioso';
    sidebar.textContent = '';
  } else {
    const running = active.filter(r => r.status === 'running').length;
    const paused = active.filter(r => r.status === 'paused').length;
    dot.className = 'dot dot-running pulse';
    text.textContent = active.length + ' ativa' + (active.length > 1 ? 's' : '');
    sidebar.textContent = [running && running + ' rodando', paused && paused + ' pausada'].filter(Boolean).join(' · ');
  }
}

function renderRunningTasks(tasks) {
  const entries = Object.entries(tasks);
  const countEl = document.getElementById('runningCount');
  if (countEl) countEl.textContent = entries.length;
  const container = document.getElementById('runningTasks');
  if (!container) { updateSidebarRunning(tasks); return; }
  if (entries.length === 0) {
    container.innerHTML = '<div class="text-xs" style="color:var(--text-3)">Nenhuma tarefa em execução.</div>';
    return;
  }
  container.innerHTML = entries.map(([id, info]) => {
    const s = info.status;
    return '<div class="cred-row" id="run-' + id + '">'
      + '<div class="flex items-center gap-3">'
        + '<span class="dot dot-' + s + (s === 'running' || s === 'paused' ? ' pulse' : '') + '"></span>'
        + '<div>'
          + '<div class="text-xs font-medium" style="color:var(--text-0)">' + esc(id) + '</div>'
          + '<div class="text-[10px]" style="color:var(--text-2)">' + (STATUS_PT[s] || s) + '</div>'
        + '</div>'
      + '</div>'
      + '<div class="flex gap-1">'
        + '<button class="btn btn-ghost" style="padding:5px 10px;font-size:11px" ' + (s !== 'running' ? 'disabled' : '') + ' onclick="pauseById(\'' + id + '\')">pausar</button>'
        + '<button class="btn btn-ghost" style="padding:5px 10px;font-size:11px" ' + (s !== 'paused' ? 'disabled' : '') + ' onclick="resumeById(\'' + id + '\')">continuar</button>'
        + '<button class="btn btn-danger" style="padding:5px 10px;font-size:11px" ' + (!['running','paused'].includes(s) ? 'disabled' : '') + ' onclick="cancelById(\'' + id + '\')">cancelar</button>'
      + '</div>'
    + '</div>';
  }).join('');
  updateSidebarRunning(tasks);
}

async function refreshRunning() {
  try { renderRunningTasks(await api('GET', '/api/tasks/running')); } catch (e) {}
}

async function pauseById(id) {
  try { await api('POST', '/api/tasks/' + id + '/pause'); toast('Pausada'); logLine('task ' + id + ' pausada', 'warn'); }
  catch (e) { toast(e.message, true); }
}
async function resumeById(id) {
  try { await api('POST', '/api/tasks/' + id + '/resume'); toast('Continuada'); logLine('task ' + id + ' continuada', 'info'); }
  catch (e) { toast(e.message, true); }
}
async function cancelById(id) {
  try { await api('POST', '/api/tasks/' + id + '/cancel'); toast('Cancelando'); logLine('task ' + id + ' cancelada', 'error'); }
  catch (e) { toast(e.message, true); }
}

/* Credentials */
async function loadCredentials() {
  try {
    const data = await api('GET', '/api/credentials');
    document.getElementById('credCount').textContent = String(data.length).padStart(2, '0') + ' / ' + String(data.length).padStart(2, '0');
    document.getElementById('credList').innerHTML = data.length
      ? data.map((c, i) => '<div class="cred-row fade-up" style="animation-delay:' + (i * 0.03) + 's"><div class="flex items-center gap-4 min-w-0"><div class="text-[10px] tabular-nums" style="color:var(--text-3)">' + String(i + 1).padStart(2, '0') + '</div><div class="min-w-0"><div class="text-sm font-medium truncate" style="color:var(--text-0)">' + esc(c.service) + '</div><div class="text-[11px] truncate" style="color:var(--text-2)">' + esc(c.usernames.join(' · ')) + '</div></div></div><button class="btn btn-danger" style="padding:6px 12px;font-size:11px" onclick="deleteCred(\'' + esc(c.service) + '\')"><svg width="10" height="10" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>remover</button></div>').join('')
      : '<div class="card p-8 text-center" style="border-style:dashed"><div class="text-sm mb-1" style="color:var(--text-1)">Nenhuma credencial salva</div><div class="text-xs" style="color:var(--text-3)">Adicione sua primeira entrada acima para começar</div></div>';
  } catch (e) { toast('Falha ao carregar credenciais', true); }
}

async function deleteCred(service) {
  try { await api('DELETE', '/api/credentials/' + encodeURIComponent(service)); toast('Credencial removida'); logLine('credencial removida: ' + service, 'warn'); loadCredentials(); }
  catch (e) { toast('Falha ao excluir', true); }
}

document.getElementById('credForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = { service: document.getElementById('service').value, username: document.getElementById('username').value, password: document.getElementById('password').value };
  try { await api('POST', '/api/credentials', data); toast('Credencial salva'); logLine('credencial salva: ' + data.service, 'success'); e.target.reset(); loadCredentials(); }
  catch (err) { toast('Falha ao salvar: ' + err.message, true); }
});

/* Tasks */
var allTasks = [];
var currentTask = '';

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

async function openTaskDetail(name) {
  currentTask = name;
  _backFn = null;
  document.getElementById('detailTaskName').textContent = name;
  document.getElementById('detailContent').innerHTML = '<div class="text-sm" style="color:var(--text-2)">Carregando...</div>';
  switchPanel('task-detail');

  try {
    const [schema, config, creds, executions] = await Promise.all([
      api('GET', '/api/tasks/' + encodeURIComponent(name) + '/schema'),
      api('GET', '/api/tasks/' + encodeURIComponent(name) + '/config'),
      api('GET', '/api/credentials'),
      api('GET', '/api/executions'),
    ]);
    renderTaskDetail(name, schema, config, creds, executions);
  } catch (e) {
    document.getElementById('detailContent').innerHTML = '<div class="text-sm" style="color:var(--danger)">Erro: ' + esc(e.message) + '</div>';
  }
}

function renderTaskDetail(name, schema, config, creds, executions) {
  var paramsHtml = '';
  for (var i = 0; i < schema.length; i++) {
    var f = schema[i];
    var fieldId = 'cfg-' + f.name;
    if (f.type === 'credential') {
      paramsHtml += '<div><label class="label">' + esc(f.label) + '</label><select id="' + fieldId + '" class="input"><option value="">— selecione —</option>';
      if (creds) for (var j = 0; j < creds.length; j++) {
        var svc = creds[j].service;
        var sel = config && config[f.name] && config[f.name].service === svc ? ' selected' : '';
        paramsHtml += '<option value="' + esc(svc) + '"' + sel + '>' + esc(svc) + '</option>';
      }
      paramsHtml += '</select></div>';
    } else if (f.type === 'json') {
      var val = config && config[f.name] !== undefined ? JSON.stringify(config[f.name], null, 2) : '';
      paramsHtml += '<div><label class="label">' + esc(f.label) + '</label><textarea id="' + fieldId + '" rows="5" class="input" style="font-family:\'JetBrains Mono\',monospace">' + esc(val) + '</textarea></div>';
    } else if (f.type === 'number') {
      var nv = config && config[f.name] !== undefined ? config[f.name] : '';
      paramsHtml += '<div><label class="label">' + esc(f.label) + '</label><input id="' + fieldId + '" type="number" value="' + esc(String(nv)) + '" class="input"></div>';
    } else {
      var sv = config && config[f.name] !== undefined ? config[f.name] : '';
      paramsHtml += '<div><label class="label">' + esc(f.label) + '</label><input id="' + fieldId + '" type="text" value="' + esc(String(sv)) + '" class="input"></div>';
    }
  }
  if (!schema.length) paramsHtml = '<div class="text-sm" style="color:var(--text-2)">Sem parâmetros.</div>';

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
          var diff = Date.now() - new Date(e.started_at);
          var sec = Math.floor(diff / 1000);
          dur = (sec >= 60 ? Math.floor(sec / 60) + 'm ' : '') + (sec % 60) + 's';
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
    + '<div class="card p-6"><div class="label" style="margin-bottom:12px">PARÂMETROS</div>' + paramsHtml
    + '<div class="flex gap-2 mt-4"><button class="btn btn-ghost" onclick="saveDetailConfig()"><svg width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>salvar config</button>'
    + '<button class="btn btn-primary" onclick="runDetailTask()"><svg width="11" height="11" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>executar</button></div></div>'
    + '<div class="card p-6"><div class="label" style="margin-bottom:12px">ÚLTIMAS EXECUÇÕES</div>' + histHtml + '</div>';
}

function collectDetailParams() {
  var p = {};
  var els = document.querySelectorAll('#detailContent [id^="cfg-"]');
  for (var i = 0; i < els.length; i++) {
    var el = els[i];
    var name = el.id.replace('cfg-', '');
    if (el.tagName === 'SELECT') { if (el.value) p[name] = { service: el.value }; }
    else if (el.type === 'number') { p[name] = parseFloat(el.value) || 0; }
    else if (el.tagName === 'TEXTAREA') { try { p[name] = JSON.parse(el.value); } catch(e) { toast('JSON inválido em ' + name, true); return null; } }
    else { p[name] = el.value; }
  }
  return p;
}

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

async function openConfigModal(name) {
  currentTask = name;
  document.getElementById('configModalTitle').textContent = name;
  document.getElementById('configFields').innerHTML = '<div class="text-sm" style="color:var(--text-2)">Carregando...</div>';
  document.getElementById('configModal').classList.remove('hidden');
  document.getElementById('configModal').classList.add('flex');

  try {
    const schema = await api('GET', '/api/tasks/' + encodeURIComponent(name) + '/schema');
    const config = await api('GET', '/api/tasks/' + encodeURIComponent(name) + '/config');
    const creds = await api('GET', '/api/credentials');
    renderConfigFields(schema, config, creds);
  } catch (e) {
    document.getElementById('configFields').innerHTML = '<div class="text-sm" style="color:var(--danger)">Erro ao carregar: ' + e.message + '</div>';
  }
}

function renderConfigFields(schema, config, creds) {
  var html = '';
  for (var i = 0; i < schema.length; i++) {
    var field = schema[i];
    var val = config && config[field.name] !== undefined ? JSON.stringify(config[field.name], null, 2) : '';
    if (field.type === 'credential') {
      html += '<div class="mb-4"><label class="label" style="margin-bottom:6px">' + esc(field.label) + '</label><select id="cfg-' + field.name + '" class="input">';
      html += '<option value="">— selecione —</option>';
      if (creds) {
        for (var j = 0; j < creds.length; j++) {
          var svc = creds[j].service;
          var selected = config && config[field.name] && config[field.name].service === svc ? ' selected' : '';
          html += '<option value="' + esc(svc) + '"' + selected + '>' + esc(svc) + '</option>';
        }
      }
      html += '</select></div>';
    } else if (field.type === 'json') {
      html += '<div class="mb-4"><label class="label" style="margin-bottom:6px">' + esc(field.label) + '</label><textarea id="cfg-' + field.name + '" rows="6" class="input" style="font-family:\'JetBrains Mono\',monospace;resize:vertical;line-height:1.6" spellcheck="false">' + esc(val) + '</textarea></div>';
    } else if (field.type === 'number') {
      var numVal = config && config[field.name] !== undefined ? config[field.name] : '';
      html += '<div class="mb-4"><label class="label" style="margin-bottom:6px">' + esc(field.label) + '</label><input id="cfg-' + field.name + '" type="number" value="' + esc(String(numVal)) + '" class="input"></div>';
    } else {
      var strVal = config && config[field.name] !== undefined ? config[field.name] : '';
      html += '<div class="mb-4"><label class="label" style="margin-bottom:6px">' + esc(field.label) + '</label><input id="cfg-' + field.name + '" type="text" value="' + esc(String(strVal)) + '" placeholder="' + esc(field.label) + '" class="input"></div>';
    }
  }
  if (schema.length === 0) {
    html = '<div class="text-sm" style="color:var(--text-2)">Esta tarefa não requer parâmetros.</div>';
  }
  document.getElementById('configFields').innerHTML = html;
}

function closeConfigModal() {
  document.getElementById('configModal').classList.add('hidden');
  document.getElementById('configModal').classList.remove('flex');
  currentTask = '';
}

async function saveModalConfig() {
  var params = collectConfigParams();
  if (!params) return;
  try {
    await api('POST', '/api/tasks/' + encodeURIComponent(currentTask) + '/config', params);
    toast('Config salva');
    logLine('config salva: ' + currentTask, 'info');
    closeConfigModal();
  } catch (e) { toast('Erro ao salvar: ' + e.message, true); }
}

async function saveAndRun() {
  var params = collectConfigParams();
  if (!params) return;
  try {
    await api('POST', '/api/tasks/' + encodeURIComponent(currentTask) + '/config', params);
    const res = await api('POST', '/api/run/' + encodeURIComponent(currentTask), params);
    toast('Tarefa iniciada');
    closeConfigModal();
    openExecutionDetail(res.task_id);
  } catch (e) { toast('Erro: ' + e.message, true); }
}

/* Init */
try { _connectWS(); } catch(e) {}
loadCredentials();
var savedPanel = 'tasks';
try { var p = sessionStorage.getItem('senior-rpa.panel'); if (p) savedPanel = p; } catch(e) {}
switchPanel(savedPanel);
var initWatch = setInterval(function() {
  var cards = document.getElementById('taskCards');
  if (cards && cards.children.length > 0) clearInterval(initWatch);
  else loadTasks();
}, 1000);
setTimeout(function() { clearInterval(initWatch); }, 8000);
setInterval(refreshRunning, 2000);

function collectConfigParams() {
  var schema = document.querySelectorAll('#configFields .mb-4');
  if (schema.length === 0) return {};
  var params = {};
  for (var i = 0; i < schema.length; i++) {
    var input = schema[i].querySelector('input,textarea,select');
    if (!input) continue;
    var name = input.id.replace('cfg-', '');
    var type = input.type || 'text';
    if (type === 'number') {
      params[name] = parseFloat(input.value) || 0;
    } else if (input.tagName === 'SELECT') {
      if (input.value) {
        params[name] = { service: input.value };
      }
    } else if (type === 'textarea' || name === 'users') {
      try { params[name] = JSON.parse(input.value); } catch(e) { toast('JSON inválido no campo ' + name, true); return null; }
    } else {
      params[name] = input.value;
    }
  }
  return params;
}


/* JSON syntax highlight */
function renderJson(obj, depth) {
  if (depth > 10) return '<span style="color:var(--text-3)">…</span>';
  if (obj === null || obj === undefined) return '<span style="color:#78716c">null</span>';
  if (typeof obj === 'string') return '<span style="color:#22c55e">"' + esc(obj) + '"</span>';
  if (typeof obj === 'number') return '<span style="color:#f59e0b">' + obj + '</span>';
  if (typeof obj === 'boolean') return '<span style="color:#a78bfa">' + obj + '</span>';
  if (Array.isArray(obj)) {
    if (obj.length === 0) return '[]';
    var items = obj.map(function(v) { return renderJson(v, depth + 1); });
    return '[\n' + items.map(function(v) { return '  ' + v; }).join(',\n') + '\n]';
  }
  if (typeof obj === 'object') {
    var keys = Object.keys(obj);
    if (keys.length === 0) return '{}';
    var pairs = keys.map(function(k) {
      return '<span style="color:#06b6d4">"' + esc(k) + '"</span>: ' + renderJson(obj[k], depth + 1);
    });
    return '{\n' + pairs.map(function(v) { return '  ' + v; }).join(',\n') + '\n}';
  }
  return esc(String(obj));
}


function esc(s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

/* Uptime */
const bootEpoch = Date.now();
var _bootEl = document.getElementById('bootTime');
if (_bootEl) _bootEl.textContent = new Date().toTimeString().slice(0, 8);
setInterval(function() {
  var s = Math.floor((Date.now() - bootEpoch) / 1000);
  document.getElementById('uptime').textContent = String(Math.floor(s / 3600)).padStart(2, '0') + ':' + String(Math.floor((s % 3600) / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0');
}, 1000);

/* Theme */
const THEME_KEY = 'senior-rpa.theme';
function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  try { localStorage.setItem(THEME_KEY, theme); } catch(e) {}
  document.querySelectorAll('.theme-opt').forEach(function(b) { b.classList.toggle('active', b.dataset.themeValue === theme); });
}
setTheme(document.documentElement.getAttribute('data-theme') || 'light');
try {
  window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', function(e) {
    if (!localStorage.getItem(THEME_KEY)) setTheme(e.matches ? 'light' : 'dark');
  });
} catch(e) {}

var _initPanel = 'tasks';
try { _initPanel = localStorage.getItem(PANEL_KEY) || 'tasks'; } catch(e) {}
loadCredentials();
switchPanel(_initPanel);
setInterval(refreshRunning, 1000);

/* History */
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
            + '<div class="flex items-center justify-between mb-2">'
            + '<div class="flex items-center gap-2 min-w-0">'
            + '<span class="text-sm font-medium truncate" style="color:var(--text-0)">' + esc(e.task_name) + '</span>'
            + '<span class="text-[10px] px-2 py-0.5 rounded-sm font-semibold" style="' + statusBadge + '">' + statusText + '</span>'
            + '</div>'
            + (dur ? '<span class="text-[10px] tabular-nums hist-time">' + start + ' (' + dur + ')</span>' : '<span class="text-[10px] tabular-nums hist-time">' + start + '</span>')
            + '</div>'
            + (e.finished_at ? '<div class="text-[10px] hist-time">fim: ' + end + '</div>' : '')
            + '</div>';
        }).join('')
      : '<div class="card p-8 text-center" style="border-style:dashed"><div class="text-sm" style="color:var(--text-1)">Nenhuma execução ainda.</div></div>';
  } catch (e) { toast('Falha ao carregar histórico', true); }
}

/* WebSocket */
var _ws = null;
var _wsCallbacks = {};

function _connectWS() {
  if (_ws && _ws.readyState !== WebSocket.CLOSED) _ws.close();
  var proto = location.protocol === "https:" ? "wss" : "ws";
  _ws = new WebSocket(proto + "://" + location.host + "/ws");
  _ws.onmessage = function(e) {
    try {
      var data = JSON.parse(e.data);
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

var _stopCurrentWatch = null;

function renderFlowChart(steps) {
  if (!steps || !steps.length) return '<div class="text-xs" style="color:var(--text-3)">Nenhum passo registrado.</div>';
  var cls = { completed: "c", running: "r", failed: "f" };
  var tooltip = function(s) {
    var t = s.timestamp ? s.timestamp.slice(11, 19) : "";
    return t ? ' title="' + t + '"' : "";
  };
  var html = '<div class="flowchart" style="padding:8px 0">';
  for (var i = 0; i < steps.length; i++) {
    if (i > 0) html += '<div class="flow-arrow"></div>';
    html += '<div class="flow-node ' + (cls[steps[i].status] || "p") + '"' + tooltip(steps[i]) + '>' + esc(steps[i].name) + '</div>';
  }
  html += '</div>';
  return html;
}

function _renderExecDetail(id, exec) {
  var statusText = STATUS_PT[exec.status] || exec.status;
  var stepsHtml = renderFlowChart(exec.steps);

  var logsHtml = exec.logs && exec.logs.length
    ? '<div class="card p-6 mt-4"><div class="label" style="margin-bottom:8px">LOG</div>'
      + '<div id="execLogBox" class="log-box" style="height:180px;overflow-y:auto">'
      + exec.logs.map(function(l) {
          var lvlColor = { error: 'var(--danger)', warn: 'var(--warn)', info: 'var(--text-1)' };
          return '<div style="padding-left:8px"><span style="color:var(--text-3)">[' + (l.timestamp ? l.timestamp.slice(11, 19) : '') + ']</span> '
            + '<span style="color:' + (lvlColor[l.level] || 'var(--text-1)') + '">' + esc(l.message) + '</span></div>';
        }).join('')
      + '</div></div>'
    : '';

  var resultHtml = exec.result
    ? '<div class="card p-6"><div class="flex items-center justify-between mb-2"><div class="label" style="margin-bottom:0">RESULTADO</div>'
      + '<button class="btn btn-ghost" style="padding:4px 8px;font-size:10px" onclick="var t=this.nextElementSibling;if(t.style.display===\'none\'){t.style.display=\'block\';this.textContent=\'ocultar\'}else{t.style.display=\'none\';this.textContent=\'mostrar\'}">ocultar</button>'
      + '<textarea readonly style="position:absolute;left:-9999px" id="copyTarget-' + id + '">' + esc(JSON.stringify(exec.result, null, 2)) + '</textarea>'
      + '</div>'
      + '<button class="btn btn-ghost" style="padding:4px 8px;font-size:10px;float:right" onclick="var t=document.getElementById(\'copyTarget-' + id + '\');t.select();navigator.clipboard.writeText(t.value);toast(\'Copiado\')">📋 copiar</button>'
      + '<pre id="resultDisplay-' + id + '" class="text-xs" style="white-space:pre-wrap;color:var(--text-1)">' + renderJson(exec.result, 0) + '</pre></div>'
    : '';

  document.getElementById('detailTaskName').textContent = exec.task_name + ' (' + id + ')';
  document.getElementById('detailContent').innerHTML = ''
    + '<div class="card p-6"><span class="label" style="margin-bottom:4px">STATUS</span><span class="text-sm" style="color:var(--text-0)">' + statusText + '</span></div>'
    + '<div class="card p-6"><div class="label" style="margin-bottom:8px">PASSOS</div>' + stepsHtml + logsHtml + '</div>'
    + resultHtml;

  var logBox = document.getElementById('execLogBox');
  if (logBox) logBox.scrollTop = logBox.scrollHeight;
}

async function openExecutionDetail(id) {
  if (_stopCurrentWatch) { _stopCurrentWatch(); _stopCurrentWatch = null; }

  document.getElementById('detailTaskName').textContent = '\u2026';
  document.getElementById('detailContent').innerHTML = '<div class="text-sm" style="color:var(--text-2)">Carregando...</div>';
  switchPanel('task-detail');

  try {
    const exec = await api('GET', '/api/executions/' + id);
    _renderExecDetail(id, exec);

    if (!['completed', 'failed', 'cancelled'].includes(exec.status)) {
      _stopCurrentWatch = _watchExec(id, function() {
        api('GET', '/api/executions/' + id).then(function(updated) {
          _renderExecDetail(id, updated);
        });
      });
    }
  } catch (e) { toast('Erro: ' + e.message, true); }
}