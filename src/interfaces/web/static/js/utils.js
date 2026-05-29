const API = '';

function _getToken() {
  var meta = document.querySelector('meta[name="api-token"]');
  return meta ? meta.getAttribute('content') : '';
}

async function api(method, path, body) {
  const opts = { method, headers: {} };
  var token = _getToken();
  if (token) {
    opts.headers['Authorization'] = 'Bearer ' + token;
  }
  if (body) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  const res = await fetch(API + path, opts);
  if (!res.ok) { const err = await res.text(); throw new Error(err); }
  return res.status === 204 ? null : res.json();
}

function toast(msg, isError) {
  const el = document.getElementById('toast');
  el.textContent = (isError ? '\u2715  ' : '\u2713  ') + msg;
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

function esc(s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

function renderJson(obj, depth) {
  if (depth > 10) return '<span style="color:var(--text-3)">\u2026</span>';
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
