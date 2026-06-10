var _devPanelOpen = false;
var _devEditor = null;
var _devSnippetAbortCtrl = null;
var _devSnippetExecId = null;

function initDevTools() {
  var btn = document.getElementById('devBtn');
  if (btn) btn.style.display = 'flex';
  document.addEventListener('click', function(e) {
    if (!_devPanelOpen) return;
    var panel = document.getElementById('devPanel');
    var btn2 = document.getElementById('devBtn');
    if (panel && !panel.contains(e.target) && btn2 && !btn2.contains(e.target)) {
      _closeDevPanel();
    }
  });
}

function _closeDevPanel() {
  _devPanelOpen = false;
  document.getElementById('devPanel').classList.add('hidden');
}

function toggleDevPanel() {
  _devPanelOpen = !_devPanelOpen;
  var panel = document.getElementById('devPanel');
  if (_devPanelOpen) {
    panel.classList.remove('hidden');
    refreshDevExecs();
    if (!_devEditor) {
      var el = document.getElementById('devSnippetCode');
      if (el && typeof CodeMirror !== 'undefined') {
        _devEditor = CodeMirror.fromTextArea(el, {
          mode: 'python',
          theme: 'default',
          lineNumbers: true,
          indentUnit: 4,
          tabSize: 4,
          indentWithTabs: false,
          lineWrapping: false,
          autofocus: false,
        });
        _devEditor.setSize('100%', '600px');
      }
    }
  } else {
    _closeDevPanel();
  }
}

async function refreshDevExecs() {
  try {
    var running = await api('GET', '/api/tasks/running');
    var select = document.getElementById('devExecSelect');
    var current = select.value;
    select.innerHTML = '<option value="">— selecione —</option>';
    Object.entries(running).forEach(function(entry) {
      var id = entry[0], info = entry[1];
      var opt = document.createElement('option');
      opt.value = id;
      opt.textContent = (info.task_name || id) + ' · ' + (STATUS_PT[info.status] || info.status);
      if (id === current) opt.selected = true;
      select.appendChild(opt);
    });
  } catch(e) {}
}

function onDevExecChange() {
  document.getElementById('devSnippetStatus').textContent = '';
  document.getElementById('devSnippetOutput').textContent = '';
}

async function runDevSnippet() {
  var execId = document.getElementById('devExecSelect').value;
  var code = _devEditor ? _devEditor.getValue() : document.getElementById('devSnippetCode').value;
  if (!code.trim()) return;
  var status = document.getElementById('devSnippetStatus');
  var output = document.getElementById('devSnippetOutput');
  var abortBtn = document.getElementById('devSnippetAbort');
  var runBtn = document.getElementById('devSnippetRun');
  status.textContent = 'executando...';
  status.style.color = 'var(--text-2)';
  output.textContent = '';
  _devSnippetAbortCtrl = new AbortController();
  _devSnippetExecId = execId || '__standalone__';
  var url = execId ? '/api/executions/' + execId + '/snippet' : '/api/dev/snippet';
  if (abortBtn) abortBtn.style.display = '';
  if (runBtn) runBtn.disabled = true;
  try {
    var res = await api('POST', url, { code: code }, _devSnippetAbortCtrl.signal);
    if (res.error === 'abortado') {
      status.textContent = 'abortado';
      status.style.color = 'var(--warn)';
    } else {
      status.textContent = res.ok ? 'ok' : 'erro';
      status.style.color = res.ok ? 'var(--accent)' : 'var(--danger)';
    }
    output.textContent = (res.output || []).join('\n') + (res.error && res.error !== 'abortado' ? '\n' + res.error : '');
  } catch(e) {
    if (e.name === 'AbortError') {
      status.textContent = 'abortado';
      status.style.color = 'var(--warn)';
    } else {
      status.textContent = 'erro';
      status.style.color = 'var(--danger)';
      output.textContent = e.message;
    }
  } finally {
    _devSnippetAbortCtrl = null;
    _devSnippetExecId = null;
    if (abortBtn) abortBtn.style.display = 'none';
    if (runBtn) runBtn.disabled = false;
  }
}

async function abortDevSnippet() {
  var deleteUrl = _devSnippetExecId === '__standalone__'
    ? '/api/dev/snippet'
    : '/api/executions/' + _devSnippetExecId + '/snippet';
  try { await api('DELETE', deleteUrl); } catch(e) {}
  if (_devSnippetAbortCtrl) _devSnippetAbortCtrl.abort();
}

async function reloadPlugins() {
  var status = document.getElementById('devSnippetStatus');
  status.textContent = 'recarregando plugins...';
  status.style.color = 'var(--text-2)';
  try {
    var res = await api('POST', '/api/plugins/reload');
    status.textContent = 'ok — ' + (res.reloaded || []).join(', ');
    status.style.color = 'var(--accent)';
  } catch(e) {
    status.textContent = 'erro';
    status.style.color = 'var(--danger)';
    document.getElementById('devSnippetOutput').textContent = e.message;
  }
}

async function runDevOcr() {
  var execId = document.getElementById('devExecSelect').value;
  if (!execId) { toast('Selecione uma execução', true); return; }
  var status = document.getElementById('devSnippetStatus');
  var output = document.getElementById('devSnippetOutput');
  status.textContent = 'ocr...';
  status.style.color = 'var(--text-2)';
  output.textContent = '';
  try {
    var res = await api('POST', '/api/executions/' + execId + '/ocr');
    status.textContent = 'ok';
    status.style.color = 'var(--accent)';
    output.textContent = res.text || '';
  } catch(e) {
    status.textContent = 'erro';
    status.style.color = 'var(--danger)';
    output.textContent = e.message;
  }
}
