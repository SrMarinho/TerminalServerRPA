const PANEL_KEY = 'TerminalServerRPA.panel';
const PERSIST_PANELS = ['tasks', 'credentials', 'history', 'schedules'];
var _prevPanel = 'tasks';
var _backFn = null;

const STATUS_PT = { idle: 'ocioso', running: 'executando', paused: 'pausado', completed: 'concluído', failed: 'falhou', cancelled: 'cancelado' };

function switchPanel(name) {
  if (name !== 'task-detail' && _stopCurrentWatch) { _stopCurrentWatch(); _stopCurrentWatch = null; }
  if (name !== 'task-detail') try { sessionStorage.removeItem('TerminalServerRPA.task'); sessionStorage.removeItem('TerminalServerRPA.exec'); } catch(e) {}
  if (PERSIST_PANELS.includes(name)) _prevPanel = name;
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  var btn = document.querySelector('.nav-btn[data-panel="' + name + '"]');
  if (btn) btn.classList.add('active');
  document.querySelectorAll('.panel').forEach(p => p.classList.add('hidden'));
  document.getElementById('panel-' + name).classList.remove('hidden');
  if (name === 'tasks') loadTasks();
  if (name === 'credentials') loadCredentials();
  if (name === 'history') loadHistory();
  if (name === 'schedules') loadSchedules();
  if (PERSIST_PANELS.includes(name)) try { sessionStorage.setItem(PANEL_KEY, name); } catch(e) {}
}

function goBack() {
  if (_backFn) { var fn = _backFn; _backFn = null; fn(); }
  else switchPanel(_prevPanel);
}

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
async function skipById(id) {
  try { await api('POST', '/api/tasks/' + id + '/skip'); toast('Step pulado'); logLine('task ' + id + ' step pulado', 'warn'); }
  catch (e) { toast(e.message, true); }
}

/* Uptime */
const bootEpoch = Date.now();
var _bootEl = document.getElementById('bootTime');
if (_bootEl) _bootEl.textContent = new Date().toTimeString().slice(0, 8);
setInterval(function() {
  var s = Math.floor((Date.now() - bootEpoch) / 1000);
  document.getElementById('uptime').textContent = String(Math.floor(s / 3600)).padStart(2, '0') + ':' + String(Math.floor((s % 3600) / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0');
}, 1000);

/* Theme */
const THEME_KEY = 'TerminalServerRPA.theme';
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
