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
  const time = new Date().toTimeString().slice(0, 8);
  const colors = { error: 'var(--danger)', warn: 'var(--warn)', success: 'var(--accent)', info: 'var(--info)' };
  const line = document.createElement('div');
  line.style.paddingLeft = '16px';
  line.innerHTML = '<span style="color:var(--text-3)">[' + time + ']</span> <span style="color:' + (colors[type] || 'var(--text-1)') + '">' + msg + '</span>';
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

function switchPanel(name) {
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.querySelector('.nav-btn[data-panel="' + name + '"]').classList.add('active');
  document.querySelectorAll('.panel').forEach(p => p.classList.add('hidden'));
  document.getElementById('panel-' + name).classList.remove('hidden');
  if (name === 'tasks') loadTasks();
  if (name === 'credentials') loadCredentials();
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
  document.getElementById('runningCount').textContent = entries.length;
  const container = document.getElementById('runningTasks');
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
let currentTask = '';

async function loadTasks() {
  try {
    const data = await api('GET', '/api/tasks');
    document.getElementById('taskCount').textContent = String(data.available.length).padStart(2, '0') + ' ROTINAS';
    document.getElementById('taskCards').innerHTML = data.available.map((t, i) =>
      '<div class="task-tile fade-up" style="animation-delay:' + (i * 0.04) + 's">'
        + '<div class="flex items-center justify-between mb-3">'
          + '<div class="text-[10px] tabular-nums" style="color:var(--text-3);letter-spacing:.1em">ROTINA · ' + String(i + 1).padStart(2, '0') + '</div>'
          + '<div class="flex gap-1">'
            + '<button class="btn btn-ghost" style="padding:4px 8px;font-size:11px" onclick="event.stopPropagation();openConfigModal(\'' + esc(t) + '\')" title="Configurar">⚙</button>'
          + '</div>'
        + '</div>'
        + '<div class="text-sm mb-1" style="color:var(--text-0);font-weight:500" onclick="event.stopPropagation();runTaskDirect(\'' + esc(t) + '\')">' + esc(t) + '</div>'
        + '<div class="text-[11px] flex items-center gap-1.5" style="color:var(--text-2)">clique para executar</div>'
      + '</div>'
    ).join('');
  } catch (e) { toast('Falha ao carregar tarefas', true); }
}

async function runTaskDirect(name) {
  try {
    const config = await api('GET', '/api/tasks/' + encodeURIComponent(name) + '/config');
    const res = await api('POST', '/api/run/' + encodeURIComponent(name), config && Object.keys(config).length ? config : {});
    toast('Tarefa iniciada: ' + name);
    logLine('▶ ' + name + ' [' + res.task_id + ']', 'success');
    switchPanel('tasks');
  } catch (e) { toast('Erro: ' + e.message, true); }
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
    logLine('▶ ' + currentTask + ' [' + res.task_id + ']', 'success');
    closeConfigModal();
    switchPanel('tasks');
  } catch (e) { toast('Erro: ' + e.message, true); }
}

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


function esc(s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

/* Uptime */
const bootEpoch = Date.now();
document.getElementById('bootTime').textContent = new Date().toTimeString().slice(0, 8);
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

loadCredentials();
loadTasks();
setInterval(refreshRunning, 1000);