// Template field autocomplete — resolves {var} tokens with a dropdown + live
// ghost preview. Reuses FormulaDropdown from formula.js.
// Path fields also get filesystem directory autocomplete.

const TEMPLATE_BUILTINS = [
  { name: 'now', hint: 'data+hora (%Y%m%d_%H%M%S)' },
  { name: 'date', hint: 'data (%Y%m%d)' },
  { name: 'year', hint: 'ano (%Y)' },
  { name: 'month', hint: 'mês (%m)' },
  { name: 'day', hint: 'dia (%d)' },
  { name: 'time', hint: 'hora (%H%M%S)' },
];

function _pad(n, w) { return String(n).padStart(w || 2, '0'); }

function _strftime(d, fmt) {
  var map = {
    Y: d.getFullYear(), y: _pad(d.getFullYear() % 100),
    m: _pad(d.getMonth() + 1), d: _pad(d.getDate()),
    H: _pad(d.getHours()), M: _pad(d.getMinutes()), S: _pad(d.getSeconds()),
  };
  return fmt.replace(/%([YymdHMS%])/g, function(_, c) { return c === '%' ? '%' : map[c]; });
}

class TemplateInput {
  #input;
  #dropdown;
  #ghost;
  #vars;
  #isPath;
  #previewTimer = null;
  #fsTimer = null;
  #fsCache = {};

  constructor(inputEl, dropdown) {
    this.#input = inputEl;
    this.#dropdown = dropdown;
    try { this.#vars = JSON.parse(inputEl.dataset.templateVars || '[]'); }
    catch (e) { this.#vars = []; }
    this.#isPath = inputEl.dataset.isPath === '1';
  }

  init() {
    this.#injectGhost();
    this.#bindEvents();
    this.#updatePreview();
  }

  #injectGhost() {
    this.#ghost = document.createElement('div');
    this.#ghost.className = 'template-ghost';
    this.#ghost.style.cssText = 'display:none;font-size:10px;color:var(--text-3);'
      + "font-family:'JetBrains Mono',ui-monospace,monospace;margin-top:3px;letter-spacing:.02em;word-break:break-all";
    this.#input.parentNode.insertBefore(this.#ghost, this.#input.nextSibling);
  }

  #bindEvents() {
    this.#input.addEventListener('input', () => {
      clearTimeout(this.#previewTimer);
      clearTimeout(this.#fsTimer);
      const ctx = this.#partialAtCursor();
      if (ctx !== null) {
        // Token autocomplete takes priority
        this.#showDropdown();
      } else if (this.#isPath) {
        // Debounce FS lookup — only when not inside a {token}
        this.#fsTimer = setTimeout(() => this.#showFsDropdown(), 120);
      } else {
        this.#dropdown.hide();
      }
      this.#previewTimer = setTimeout(() => this.#updatePreview(), 200);
    });
    this.#input.addEventListener('keydown', e => this.#onKeyDown(e));
    this.#input.addEventListener('blur', () => {
      setTimeout(() => this.#dropdown.hide(), 150);
    });
  }

  #onKeyDown(e) {
    if (e.key === 'Escape') { this.#dropdown.hide(); return; }
    if ((e.ctrlKey || e.metaKey) && e.key === ' ') {
      e.preventDefault();
      const ctx = this.#partialAtCursor();
      if (ctx !== null) this.#showDropdown(true);
      else if (this.#isPath) this.#showFsDropdown(true);
      return;
    }
    if (!this.#dropdown.isOpen) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); this.#dropdown.navigateDown(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); this.#dropdown.navigateUp(); }
    else if (e.key === 'Enter' || e.key === 'Tab') {
      const item = this.#dropdown.selectedItem ?? this.#dropdown.firstItem;
      if (item) { e.preventDefault(); this.#applyItem(item); }
    }
  }

  // Partial token being typed: last unclosed `{` before the cursor.
  #partialAtCursor() {
    const pos = this.#input.selectionStart;
    const before = this.#input.value.slice(0, pos);
    const open = before.lastIndexOf('{');
    if (open === -1) return null;
    const seg = before.slice(open + 1);
    if (/[}\s]/.test(seg)) return null; // already closed or spaced out
    return { open: open, partial: seg };
  }

  #allVars() {
    const seen = {};
    const out = [];
    const add = (v) => { if (v.name && !seen[v.name]) { seen[v.name] = 1; out.push(v); } };
    (this.#vars || []).forEach(add);
    TEMPLATE_BUILTINS.forEach(add);
    return out;
  }

  #showDropdown(force) {
    const ctx = this.#partialAtCursor();
    if (!ctx && !force) { this.#dropdown.hide(); return; }
    const partial = ctx ? ctx.partial : '';
    const items = this.#allVars()
      .filter(v => v.name.startsWith(partial))
      .map(v => ({ text: '{' + v.name + '}', hint: v.hint || '', insert_var: v.name, _type: 'var' }));
    if (!items.length) { this.#dropdown.hide(); return; }
    this.#dropdown.currentPartial = partial;
    this.#dropdown.position(this.#input.getBoundingClientRect());
    this.#dropdown.populate(items, item => this.#applyItem(item));
  }

  async #showFsDropdown(force) {
    const val = this.#input.value;
    const cacheKey = val;
    let dirs = this.#fsCache[cacheKey];
    if (!dirs) {
      try {
        const res = await api('GET', '/api/fs/dirs?prefix=' + encodeURIComponent(val));
        dirs = res.dirs || [];
        this.#fsCache[cacheKey] = dirs;
      } catch (e) {
        return;
      }
    }
    if (!dirs.length) { this.#dropdown.hide(); return; }
    const items = dirs.map(d => ({ text: d, hint: '', _type: 'fs', _path: d }));
    this.#dropdown.position(this.#input.getBoundingClientRect());
    this.#dropdown.populate(items, item => this.#applyFsItem(item));
  }

  #applyItem(item) {
    this.#dropdown.hide();
    const pos = this.#input.selectionStart;
    const value = this.#input.value;
    const before = value.slice(0, pos);
    const after = value.slice(pos);
    const open = before.lastIndexOf('{');
    const head = open === -1 ? before : before.slice(0, open);
    const replaced = head + '{' + item.insert_var + '}';
    this.#input.value = replaced + after;
    const caret = replaced.length;
    this.#input.setSelectionRange(caret, caret);
    this.#input.focus();
    this.#updatePreview();
  }

  #applyFsItem(item) {
    this.#dropdown.hide();
    // Replace entire value with selected path + separator so user keeps typing
    const sep = item._path.includes('/') ? '/' : '\\';
    this.#input.value = item._path + sep;
    this.#input.setSelectionRange(this.#input.value.length, this.#input.value.length);
    this.#input.focus();
    this.#updatePreview();
    // Immediately show next level
    this.#fsTimer = setTimeout(() => this.#showFsDropdown(), 80);
  }

  #resolveToken(name, fmt) {
    const now = new Date();
    if (fmt) return _strftime(now, fmt);
    switch (name) {
      case 'now': return _strftime(now, '%Y%m%d_%H%M%S');
      case 'date': return _strftime(now, '%Y%m%d');
      case 'year': return String(now.getFullYear());
      case 'month': return _pad(now.getMonth() + 1);
      case 'day': return _pad(now.getDate());
      case 'time': return _strftime(now, '%H%M%S');
    }
    const def = (this.#vars || []).find(v => v.name === name);
    const fieldName = (def && def.source) || name;
    const el = document.getElementById('cfg-' + fieldName);
    if (el && el.value) return el.value;
    return '‹' + name + '›';
  }

  #render(template) {
    return template.replace(/\{(\w+)(?::([^}]+))?\}/g, (m, name, fmt) => this.#resolveToken(name, fmt));
  }

  #updatePreview() {
    const tpl = this.#input.value;
    if (!tpl || tpl.indexOf('{') === -1) { this.#ghost.style.display = 'none'; return; }
    this.#ghost.textContent = '→ ' + this.#render(tpl);
    this.#ghost.style.display = 'block';
  }
}

function _initTemplateAutocomplete(container) {
  const dropdownEl = document.getElementById('formula-dropdown');
  if (!dropdownEl) return;
  const dropdown = new FormulaDropdown(dropdownEl);
  container.querySelectorAll('input[data-field-type="template"]').forEach(el => {
    new TemplateInput(el, dropdown).init();
  });
}
