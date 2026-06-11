// ─── ResolverMetaService ──────────────────────────────────────────────────────

class ResolverMetaService {
  #cache = null;

  async load() {
    if (this.#cache) return this.#cache;
    try { this.#cache = await api('GET', '/api/resolvers'); }
    catch (e) { this.#cache = {}; }
    return this.#cache;
  }
}

const resolverMeta = new ResolverMetaService();

// ─── FormulaParser ────────────────────────────────────────────────────────────

class FormulaParser {
  static parseParenContext(value, cursorPos) {
    const before = value.slice(0, cursorPos);

    const bareMatch = before.match(/^=(\w+)\(([^)]*)$/);
    if (bareMatch) {
      return { namespace: '__fn__', fnName: bareMatch[1], partial: null, usedParams: [], isBare: true };
    }

    const nsMatch = before.match(/^=(\w+)\.(\w+)\(([^)]*)$/);
    if (!nsMatch) return null;

    const [, namespace, fnName, argsStr] = nsMatch;
    const lastArg = argsStr.split(',').pop().trim();
    const partialMatch = lastArg.match(/^(\w*)$/);
    const usedParams = argsStr.split(',').slice(0, -1)
      .flatMap(arg => { const m = arg.trim().match(/^(\w+)=/); return m ? [m[1]] : []; });

    return { namespace, fnName, partial: partialMatch ? partialMatch[1] : null, usedParams, isBare: false };
  }

  static fnAtCursor(formula, pos) {
    const s = formula.slice(1);
    pos = Math.max(0, pos - 1);
    let depth = 0;

    for (let i = pos; i >= 0; i--) {
      if (s[i] === ')') { depth++; continue; }
      if (s[i] === '(') {
        if (depth > 0) { depth--; continue; }
        let fnEnd = i, fnStart = fnEnd;
        while (fnStart > 0 && /\w/.test(s[fnStart - 1])) fnStart--;
        const fn = s.slice(fnStart, fnEnd);
        if (!fn) return null;
        if (fnStart > 0 && s[fnStart - 1] === '.') {
          let nsEnd = fnStart - 1, nsStart = nsEnd;
          while (nsStart > 0 && /\w/.test(s[nsStart - 1])) nsStart--;
          return { namespace: s.slice(nsStart, nsEnd), fnName: fn };
        }
        return { namespace: '__fn__', fnName: fn };
      }
    }
    return null;
  }

  static charPosFromMouseX(mouseX, inputEl) {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const style = window.getComputedStyle(inputEl);
    ctx.font = `${style.fontSize} ${style.fontFamily}`;
    const rect = inputEl.getBoundingClientRect();
    const relX = mouseX - rect.left - (parseFloat(style.paddingLeft) || 0);
    const text = inputEl.value;
    for (let i = 0; i <= text.length; i++) {
      if (ctx.measureText(text.slice(0, i)).width >= relX) return i;
    }
    return text.length;
  }
}

// ─── FormulaDropdown ──────────────────────────────────────────────────────────

class FormulaDropdown {
  #el;
  #items = [];
  #selectedIndex = -1;
  #currentPartial = '';

  constructor(el) { this.#el = el; }

  get el() { return this.#el; }
  get isOpen() { return !this.#el.classList.contains('hidden'); }
  get selectedItem() { return this.#selectedIndex >= 0 ? this.#items[this.#selectedIndex] : null; }
  get firstItem() { return this.#items.length === 1 ? this.#items[0] : null; }
  get currentPartial() { return this.#currentPartial; }
  set currentPartial(v) { this.#currentPartial = v; }

  hide() { this.#el.classList.add('hidden'); this.#items = []; this.#selectedIndex = -1; }

  position(rect) {
    this.#el.style.left = `${rect.left + window.scrollX}px`;
    this.#el.style.top = `${rect.bottom + window.scrollY + 2}px`;
    this.#el.style.minWidth = `${rect.width}px`;
  }

  populate(items, onApply) {
    this.#items = items;
    this.#selectedIndex = -1;
    this.#el.innerHTML = items.map((item, i) =>
      `<div class="formula-item" data-i="${i}" style="display:flex;justify-content:space-between;align-items:center;gap:12px;padding:6px 10px;cursor:pointer;font-family:'JetBrains Mono',monospace;font-size:11px">`
      + `<code style="color:var(--accent)">${esc(item.text)}</code>`
      + `<span style="color:var(--text-3);font-size:10px">${esc(item.hint)}</span>`
      + `</div>`
    ).join('');
    this.#el.classList.remove('hidden');
    this.#el.querySelectorAll('.formula-item').forEach((el, i) => {
      el.addEventListener('mousedown', e => { e.preventDefault(); onApply(items[i]); });
      el.addEventListener('mouseenter', () => this.highlight(i));
    });
  }

  showRaw(html, rect) {
    this.#items = [];
    this.#selectedIndex = -1;
    this.#el.innerHTML = html;
    this.position(rect);
    this.#el.classList.remove('hidden');
  }

  highlight(index) {
    this.#selectedIndex = index;
    this.#el.querySelectorAll('.formula-item').forEach((el, i) => {
      el.style.background = i === index ? 'var(--bg-2)' : '';
    });
    if (index >= 0) {
      const el = this.#el.querySelectorAll('.formula-item')[index];
      if (el) el.scrollIntoView({ block: 'nearest' });
    }
  }

  navigateDown() { if (this.#items.length) this.highlight((this.#selectedIndex + 1) % this.#items.length); }
  navigateUp() { if (this.#items.length) this.highlight((this.#selectedIndex - 1 + this.#items.length) % this.#items.length); }
}

// ─── FormulaTooltip ───────────────────────────────────────────────────────────

class FormulaTooltip {
  #el;
  #hideTimer = null;

  constructor(el) { this.#el = el; }

  hide() {
    clearTimeout(this.#hideTimer);
    this.#el.classList.add('hidden');
  }

  show(html, rect, duration = 0) {
    clearTimeout(this.#hideTimer);
    this.#el.innerHTML = html;
    this.#el.style.left = `${rect.left + window.scrollX}px`;
    this.#el.style.top = `${rect.bottom + window.scrollY + 4}px`;
    this.#el.style.minWidth = `${rect.width}px`;
    this.#el.classList.remove('hidden');
    if (duration) this.#hideTimer = setTimeout(() => this.#el.classList.add('hidden'), duration);
  }

  buildHtml(namespace, fnName, fnInfo, resolvedValue) {
    const sig = namespace === '__fn__'
      ? `${fnName}(...)`
      : `${namespace}.${fnName}(${fnInfo?.params.map(p => p.name).join(', ') ?? ''})`;

    let html = `<div style="padding:6px 10px 4px;font-family:'JetBrains Mono',monospace;font-size:11px">`
      + `<code style="color:var(--accent)">${esc(sig)}</code></div>`;

    if (fnInfo?.description) {
      html += `<div style="padding:2px 10px 6px;font-size:11px;color:var(--text-2)">${esc(fnInfo.description)}</div>`;
    }
    if (fnInfo?.params?.length) {
      html += `<div style="border-top:1px solid var(--line);padding:4px 10px">`
        + fnInfo.params.map(p =>
            `<div style="display:flex;justify-content:space-between;padding:2px 0;font-family:'JetBrains Mono',monospace;font-size:10px">`
            + `<code style="color:var(--text-1)">${esc(p.name)}</code>`
            + `<span style="color:var(--text-3)">${esc(p.type)}${p.default !== undefined ? ' = ' + p.default : ''}</span>`
            + `</div>`
          ).join('') + `</div>`;
    }
    if (resolvedValue) {
      html += `<div style="border-top:1px solid var(--line);padding:5px 10px;font-family:'JetBrains Mono',monospace;font-size:11px">`
        + `<span style="color:var(--accent)">${esc(resolvedValue)}</span></div>`;
    }
    return html;
  }
}

// ─── FormulaInput ─────────────────────────────────────────────────────────────

class FormulaInput {
  #input;
  #dropdown;
  #tooltip;
  #meta;
  #ghost;
  #previewTimer = null;
  #hintTimer = null;

  constructor(inputEl, dropdown, tooltip, metaService) {
    this.#input = inputEl;
    this.#dropdown = dropdown;
    this.#tooltip = tooltip;
    this.#meta = metaService;
  }

  init() {
    this.#injectGhost();
    this.#bindEvents();
    this.#updateStyle();
    if (this.#input.value.startsWith('=')) this.#updatePreview();
  }

  #injectGhost() {
    this.#ghost = document.createElement('div');
    this.#ghost.className = 'formula-ghost';
    this.#ghost.style.cssText = 'display:none;font-size:10px;color:var(--text-3);'
      + "font-family:'JetBrains Mono',ui-monospace,monospace;margin-top:3px;letter-spacing:.02em";
    this.#input.parentNode.insertBefore(this.#ghost, this.#input.nextSibling);
  }

  #bindEvents() {
    this.#input.addEventListener('input', () => {
      this.#updateStyle();
      this.#showDropdown();
      clearTimeout(this.#previewTimer);
      this.#previewTimer = setTimeout(() => this.#updatePreview(), 400);
    });

    this.#input.addEventListener('mousemove', e => {
      if (!this.#input.value.startsWith('=')) return;
      clearTimeout(this.#hintTimer);
      this.#hintTimer = setTimeout(() => this.#showRichHint(e.clientX), 120);
    });

    this.#input.addEventListener('mouseleave', () => {
      clearTimeout(this.#hintTimer);
      this.#tooltip.hide();
    });

    this.#input.addEventListener('keydown', e => this.#onKeyDown(e));

    this.#input.addEventListener('blur', () => {
      clearTimeout(this.#previewTimer);
      this.#tooltip.hide();
      setTimeout(() => this.#dropdown.hide(), 150);
    });
  }

  #onKeyDown(e) {
    if (e.key === 'Escape') {
      this.#dropdown.hide();
      this.#tooltip.hide();
      return;
    }
    if ((e.ctrlKey || e.metaKey) && e.key === ' ') {
      e.preventDefault();
      const ctx = FormulaParser.parseParenContext(this.#input.value, this.#input.selectionStart);
      if (ctx && !ctx.isBare) {
        this.#showParamHint(ctx.namespace, ctx.fnName, ctx.partial ?? undefined, ctx.usedParams);
      } else if (this.#input.value.startsWith('=')) {
        this.#showRichHint();
      } else {
        this.#showDropdown();
      }
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

  #applyItem(item) {
    this.#dropdown.hide();
    if (item.insert_kwarg !== undefined) {
      const pos = this.#input.selectionStart;
      const before = this.#input.value.slice(0, pos);
      const after = this.#input.value.slice(pos);
      const replaced = before.slice(0, before.length - this.#dropdown.currentPartial.length) + item.insert_kwarg;
      this.#input.value = replaced + after;
      this.#input.setSelectionRange(replaced.length, replaced.length);
      this.#dropdown.currentPartial = '';
      this.#input.focus();
      this.#showDropdown();
      return;
    }
    this.#input.value = item.insert;
    this.#input.focus();
    if (item.params_count === 0) this.#input.value += ')';
    else this.#showDropdown();
    this.#input.setSelectionRange(this.#input.value.length, this.#input.value.length);
  }

  async #showDropdown() {
    const formula = this.#input.value;
    if (!formula.startsWith('=')) { this.#dropdown.hide(); return; }

    const ctx = FormulaParser.parseParenContext(formula, this.#input.selectionStart);
    if (ctx) {
      if (ctx.isBare) { this.#dropdown.hide(); return; }
      await this.#showParamHint(ctx.namespace, ctx.fnName, ctx.partial ?? undefined, ctx.usedParams);
      return;
    }

    const meta = await this.#meta.load();
    const query = formula.slice(1);
    if (query.includes(')')) { this.#dropdown.hide(); return; }

    const suggestions = this.#buildSuggestions(meta, query);
    if (!suggestions.length) { this.#dropdown.hide(); return; }

    const rect = this.#input.getBoundingClientRect();
    this.#dropdown.position(rect);
    this.#dropdown.populate(suggestions, item => this.#applyItem(item));
  }

  #buildSuggestions(meta, query) {
    const suggestions = [];
    if (!query.includes('.')) {
      Object.keys(meta)
        .filter(ns => ns !== '__fn__' && ns.startsWith(query))
        .forEach(ns => suggestions.push({ text: ns + '.', hint: 'namespace', insert: '=' + ns + '.', params_count: -1 }));

      Object.entries(meta['__fn__'] || {})
        .filter(([name]) => name.startsWith(query))
        .forEach(([name, info]) => suggestions.push({
          text: info.variadic ? `${name}(...)` : `${name}()`,
          hint: info.label,
          insert: `=${name}(`,
          params_count: info.variadic ? -1 : 0,
        }));
    } else {
      const dot = query.indexOf('.');
      const ns = query.slice(0, dot);
      const fnQuery = query.slice(dot + 1).split('(')[0];
      Object.entries(meta[ns] || {})
        .filter(([name]) => name.startsWith(fnQuery))
        .forEach(([name, info]) => suggestions.push({
          text: `${name}(${info.params.map(p => p.label || p.name).join(', ')})`,
          hint: info.label,
          insert: `=${ns}.${name}(`,
          params_count: info.params.length,
        }));
    }
    return suggestions;
  }

  async #showParamHint(namespace, fnName, partialParam, usedParams) {
    const meta = await this.#meta.load();
    const fnInfo = (meta[namespace] || {})[fnName];
    if (!fnInfo) { this.#dropdown.hide(); return; }

    const rect = this.#input.getBoundingClientRect();
    const excluded = usedParams || [];

    if (partialParam !== undefined && fnInfo.params?.length) {
      const matching = fnInfo.params.filter(p => p.name.startsWith(partialParam) && !excluded.includes(p.name));
      if (matching.length) {
        this.#dropdown.currentPartial = partialParam;
        this.#dropdown.position(rect);
        this.#dropdown.populate(matching.map(p => ({
          text: p.name + '=',
          hint: p.type + (p.default !== undefined ? ' = ' + p.default : ''),
          insert_kwarg: p.name + '=',
          params_count: 0,
        })), item => this.#applyItem(item));
        return;
      }
    }

    const label = `${namespace}.${fnName}${fnInfo.description ? ' — ' + fnInfo.description : ''}`;
    const header = `<div style="padding:4px 10px 2px;font-size:10px;color:var(--text-3);letter-spacing:.05em">${esc(label)}</div>`;
    const body = fnInfo.params?.length
      ? fnInfo.params.map(p =>
          `<div style="display:flex;justify-content:space-between;align-items:center;gap:12px;padding:5px 10px;font-family:'JetBrains Mono',monospace;font-size:11px">`
          + `<code style="color:var(--accent)">${esc(p.name)}</code>`
          + `<span style="color:var(--text-2);font-size:10px">${esc(p.type)}${p.default !== undefined ? ' = ' + p.default : ''}</span>`
          + `</div>`
        ).join('')
      : `<div style="padding:4px 10px 6px;font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text-3)">sem parâmetros</div>`;

    this.#dropdown.showRaw(header + body, rect);
  }

  async #showRichHint(mouseX) {
    const formula = this.#input.value;
    if (!formula.startsWith('=')) return;
    const charPos = mouseX !== undefined
      ? FormulaParser.charPosFromMouseX(mouseX, this.#input)
      : this.#input.selectionStart;
    const ctx = FormulaParser.fnAtCursor(formula, charPos);
    if (!ctx) { this.#tooltip.hide(); return; }
    try {
      const meta = await this.#meta.load();
      const fnInfo = (meta[ctx.namespace] || {})[ctx.fnName];
      if (!fnInfo) { this.#tooltip.hide(); return; }
      let resolvedValue = null;
      try {
        const preview = await api('POST', '/api/resolvers/preview', { formula });
        resolvedValue = preview.result;
      } catch (e) {}
      const html = this.#tooltip.buildHtml(ctx.namespace, ctx.fnName, fnInfo, resolvedValue);
      this.#tooltip.show(html, this.#input.getBoundingClientRect());
    } catch (e) {}
  }

  async #updatePreview() {
    const formula = this.#input.value;
    if (!formula.startsWith('=')) { this.#ghost.style.display = 'none'; return; }
    try {
      const preview = await api('POST', '/api/resolvers/preview', { formula });
      if (preview.result) {
        this.#ghost.textContent = '→ ' + preview.result;
        this.#ghost.style.display = 'block';
      } else {
        this.#ghost.style.display = 'none';
      }
    } catch (e) { this.#ghost.style.display = 'none'; }
  }

  #updateStyle() {
    const isFormula = this.#input.value.startsWith('=');
    this.#input.classList.toggle('formula-active', isFormula);
    this.#input.spellcheck = !isFormula;
    if (!isFormula) { this.#ghost.style.display = 'none'; this.#ghost.textContent = ''; }
  }
}

// ─── Entry point ──────────────────────────────────────────────────────────────

function _initFormulaAutocomplete(container) {
  const dropdownEl = document.getElementById('formula-dropdown');
  if (!dropdownEl) return;
  const dropdown = new FormulaDropdown(dropdownEl);
  const tooltip = new FormulaTooltip(document.getElementById('formula-tooltip'));
  container.querySelectorAll('input[type="text"]:not([data-field-type="template"])').forEach(el => {
    new FormulaInput(el, dropdown, tooltip, resolverMeta).init();
  });
}
