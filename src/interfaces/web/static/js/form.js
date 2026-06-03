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
}
