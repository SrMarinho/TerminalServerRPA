async function _applyWhen(container, taskName) {
  var params = _collectParams(container);
  if (!params) return;
  try {
    var vis = await api('POST', '/api/tasks/' + encodeURIComponent(taskName) + '/visibility', { params: params });
    Object.entries(vis).forEach(function(entry) {
      var wrap = container.querySelector('#wrap-' + entry[0]);
      if (wrap) wrap.style.display = entry[1] ? '' : 'none';
    });
  } catch(e) {}
}

function _initWhen(container, taskName) {
  _applyWhen(container, taskName);
  container.querySelectorAll('select[data-field-type="select"]').forEach(function(sel) {
    sel.addEventListener('change', function() { _applyWhen(container, taskName); });
  });
}

function _collectParams(container) {
  var p = {};
  var els = container.querySelectorAll('[id^="cfg-"]');
  for (var i = 0; i < els.length; i++) {
    var el = els[i];
    var name = el.id.replace('cfg-', '');
    if (el.tagName === 'SELECT') {
      if (el.dataset.fieldType === 'select') { p[name] = el.value; }
      else { if (el.value) p[name] = { service: el.value }; }
    } else if (el.type === 'number') {
      p[name] = parseFloat(el.value) || 0;
    } else if (el.tagName === 'TEXTAREA') {
      try { p[name] = JSON.parse(el.value); } catch(e) { toast('JSON inválido em ' + name, true); return null; }
    } else {
      p[name] = el.value;
    }
  }
  return p;
}

function _initFormContainer(container, taskName) {
  _initWhen(container, taskName);
  _initFormulaAutocomplete(container);
  _initTemplateAutocomplete(container);
  container.querySelectorAll('[data-required="1"]').forEach(function(el) {
    el.addEventListener('input', function() {
      if (el.value.trim()) { el.style.borderColor = ''; el.style.boxShadow = ''; }
    });
    el.addEventListener('change', function() {
      if (el.value) { el.style.borderColor = ''; el.style.boxShadow = ''; }
    });
  });
}

// Returns true if valid. On failure: highlights + focuses first invalid field.
function _validateRequired(container) {
  var invalid = [];
  container.querySelectorAll('[id^="cfg-"][data-required="1"]').forEach(function(el) {
    var wrap = el.closest('[id^="wrap-"]') || el.parentElement;
    var hidden = wrap && wrap.style.display === 'none';
    if (hidden) return;
    var empty = el.tagName === 'SELECT' ? !el.value : !el.value.trim();
    if (empty) {
      el.style.borderColor = 'var(--danger)';
      el.style.boxShadow = '0 0 0 3px rgba(248,113,113,.25)';
      invalid.push(el);
    } else {
      el.style.borderColor = '';
      el.style.boxShadow = '';
    }
  });
  if (invalid.length) {
    // Open parent <details> if collapsed
    var first = invalid[0];
    var details = first.closest('details.form-group');
    if (details && !details.open) details.open = true;
    first.scrollIntoView({ behavior: 'smooth', block: 'center' });
    first.focus();
    return false;
  }
  return true;
}
