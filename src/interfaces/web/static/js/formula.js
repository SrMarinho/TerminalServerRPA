var _resolverMeta = null;

async function _loadResolverMeta() {
  if (_resolverMeta) return _resolverMeta;
  try { _resolverMeta = await api('GET', '/api/resolvers'); } catch(e) { _resolverMeta = {}; }
  return _resolverMeta;
}

function _initFormulaAutocomplete(container) {
  var dropdown = document.getElementById('formula-dropdown');
  if (!dropdown) return;

  container.querySelectorAll('input[type="text"]').forEach(function(input) {
    var state = { items: [], selectedIndex: -1, currentPartial: '' };
    var tooltip = document.getElementById('formula-tooltip');
    var previewTimer = null;
    var tooltipHideTimer = null;

    var ghost = document.createElement('div');
    ghost.className = 'formula-ghost';
    ghost.style.cssText = 'display:none;font-size:10px;color:var(--text-3);'
      + "font-family:'JetBrains Mono',ui-monospace,monospace;margin-top:3px;letter-spacing:.02em";
    input.parentNode.insertBefore(ghost, input.nextSibling);

    function _highlightItem(index) {
      state.selectedIndex = index;
      dropdown.querySelectorAll('.formula-item').forEach(function(el, i) {
        el.style.background = i === index ? 'var(--bg-2)' : '';
      });
      if (index >= 0) {
        var el = dropdown.querySelectorAll('.formula-item')[index];
        if (el) el.scrollIntoView({ block: 'nearest' });
      }
    }

    function _positionDropdown(rect) {
      dropdown.style.left = rect.left + window.scrollX + 'px';
      dropdown.style.top = (rect.bottom + window.scrollY + 2) + 'px';
      dropdown.style.minWidth = rect.width + 'px';
    }

    function _populateDropdown(items) {
      state.items = items;
      state.selectedIndex = -1;
      dropdown.innerHTML = items.map(function(item, i) {
        return '<div class="formula-item" data-i="' + i + '" style="display:flex;justify-content:space-between;align-items:center;gap:12px;padding:6px 10px;cursor:pointer;font-family:\'JetBrains Mono\',monospace;font-size:11px">'
          + '<code style="color:var(--accent)">' + esc(item.text) + '</code>'
          + '<span style="color:var(--text-3);font-size:10px">' + esc(item.hint) + '</span>'
          + '</div>';
      }).join('');
      dropdown.classList.remove('hidden');
      dropdown.querySelectorAll('.formula-item').forEach(function(el, i) {
        el.addEventListener('mousedown', function(e) { e.preventDefault(); _applyItem(items[i]); });
        el.addEventListener('mouseenter', function() { _highlightItem(i); });
      });
    }

    function _applyItem(item) {
      if (!item) return;
      dropdown.classList.add('hidden');
      state.items = [];
      state.selectedIndex = -1;

      if (item.insert_kwarg !== undefined) {
        var cursorPos = input.selectionStart;
        var beforeCursor = input.value.slice(0, cursorPos);
        var afterCursor = input.value.slice(cursorPos);
        var replaced = beforeCursor.slice(0, beforeCursor.length - state.currentPartial.length) + item.insert_kwarg;
        input.value = replaced + afterCursor;
        input.setSelectionRange(replaced.length, replaced.length);
        state.currentPartial = '';
        input.focus();
        _showDropdown();
        return;
      }

      input.value = item.insert;
      input.focus();
      input.setSelectionRange(input.value.length, input.value.length);
      if (item.params_count === 0) {
        input.value += ')';
        input.setSelectionRange(input.value.length, input.value.length);
      } else {
        _showDropdown();
      }
    }

    async function _showParamHint(namespace, fnName, partialParam, usedParams) {
      var meta = await _loadResolverMeta();
      var fnInfo = (meta[namespace] || {})[fnName];
      if (!fnInfo) { dropdown.classList.add('hidden'); return; }

      var rect = input.getBoundingClientRect();
      _positionDropdown(rect);

      // bare variadic function — show description hint only
      if (fnInfo.variadic) {
        var header = '<div style="padding:6px 10px 4px;font-size:10px;color:var(--text-3);letter-spacing:.05em">' + esc(fnName) + '</div>';
        dropdown.innerHTML = header + '<div style="padding:2px 10px 6px;font-family:\'JetBrains Mono\',monospace;font-size:11px;color:var(--text-2)">' + esc(fnInfo.description || '') + '</div>';
        dropdown.classList.remove('hidden');
        return;
      }

      var excluded = usedParams || [];

      if (partialParam !== undefined && fnInfo.params.length) {
        var matchingParams = fnInfo.params.filter(function(p) {
          return p.name.startsWith(partialParam) && excluded.indexOf(p.name) === -1;
        });
        if (matchingParams.length) {
          state.currentPartial = partialParam;
          var kwargItems = matchingParams.map(function(p) {
            return {
              text: p.name + '=',
              hint: p.type + (p.default !== undefined ? ' = ' + p.default : ''),
              insert_kwarg: p.name + '=',
              params_count: 0,
            };
          });
          _populateDropdown(kwargItems);
          return;
        }
      }

      state.items = [];
      state.selectedIndex = -1;
      var header = '<div style="padding:4px 10px 2px;font-size:10px;color:var(--text-3);letter-spacing:.05em">'
        + esc(namespace + '.' + fnName) + (fnInfo.description ? ' — ' + esc(fnInfo.description) : '') + '</div>';
      dropdown.innerHTML = fnInfo.params.length
        ? header + fnInfo.params.map(function(p) {
            return '<div style="display:flex;justify-content:space-between;align-items:center;gap:12px;padding:5px 10px;font-family:\'JetBrains Mono\',monospace;font-size:11px">'
              + '<code style="color:var(--accent)">' + esc(p.name) + '</code>'
              + '<span style="color:var(--text-2);font-size:10px">' + esc(p.type) + (p.default !== undefined ? ' = ' + p.default : '') + '</span>'
              + '</div>';
          }).join('')
        : header + '<div style="padding:4px 10px 6px;font-family:\'JetBrains Mono\',monospace;font-size:11px;color:var(--text-3)">sem parâmetros</div>';
      dropdown.classList.remove('hidden');
    }

    function _parseParenContext() {
      var cursorPos = input.selectionStart;
      var beforeCursor = input.value.slice(0, cursorPos);

      // bare fn( — e.g. =concat(
      var bareMatch = beforeCursor.match(/^=(\w+)\(([^)]*)$/);
      if (bareMatch) {
        return { namespace: '__fn__', fnName: bareMatch[1], partial: null, usedParams: [], isBare: true };
      }

      var parenMatch = beforeCursor.match(/^=(\w+)\.(\w+)\(([^)]*)$/);
      if (!parenMatch) return null;
      var namespace = parenMatch[1], fnName = parenMatch[2], argsStr = parenMatch[3];
      var lastArg = argsStr.split(',').pop().trim();
      var partialMatch = lastArg.match(/^(\w*)$/);
      var usedParams = [];
      argsStr.split(',').slice(0, -1).forEach(function(arg) {
        var kwargMatch = arg.trim().match(/^(\w+)=/);
        if (kwargMatch) usedParams.push(kwargMatch[1]);
      });
      return { namespace: namespace, fnName: fnName, partial: partialMatch ? partialMatch[1] : null, usedParams: usedParams, isBare: false };
    }

    async function _showDropdown() {
      var formula = input.value;
      if (!formula.startsWith('=')) { dropdown.classList.add('hidden'); state.items = []; return; }

      var parenContext = _parseParenContext();
      if (parenContext) {
        if (parenContext.isBare) { dropdown.classList.add('hidden'); return; }
        await _showParamHint(
          parenContext.namespace,
          parenContext.fnName,
          parenContext.partial !== null ? parenContext.partial : undefined,
          parenContext.usedParams
        );
        return;
      }

      var meta = await _loadResolverMeta();
      var query = formula.slice(1);
      if (query.includes(')')) { dropdown.classList.add('hidden'); return; }
      var suggestions = [];

      if (!query.includes('.')) {
        Object.keys(meta).filter(function(ns) { return ns !== '__fn__' && ns.startsWith(query); })
          .forEach(function(ns) {
            suggestions.push({ text: ns + '.', hint: 'namespace', insert: '=' + ns + '.', params_count: -1 });
          });
        // bare functions (no namespace)
        var bareFns = meta['__fn__'] || {};
        Object.entries(bareFns).filter(function(e) { return e[0].startsWith(query); })
          .forEach(function(e) {
            var fnName = e[0], fnInfo = e[1];
            var sig = fnInfo.variadic ? fnName + '(...)' : fnName + '()';
            suggestions.push({ text: sig, hint: fnInfo.label, insert: '=' + fnName + '(', params_count: fnInfo.variadic ? -1 : 0 });
          });
      } else {
        var dotIndex = query.indexOf('.');
        var namespace = query.slice(0, dotIndex);
        var fnQuery = query.slice(dotIndex + 1).split('(')[0];
        var namespaceFns = meta[namespace] || {};
        Object.entries(namespaceFns)
          .filter(function(entry) { return entry[0].startsWith(fnQuery); })
          .forEach(function(entry) {
            var fnName = entry[0], fnInfo = entry[1];
            var sig = fnName + '(' + fnInfo.params.map(function(p) { return p.label || p.name; }).join(', ') + ')';
            suggestions.push({ text: sig, hint: fnInfo.label, insert: '=' + namespace + '.' + fnName + '(', params_count: fnInfo.params.length });
          });
      }

      if (!suggestions.length) { dropdown.classList.add('hidden'); return; }
      var rect = input.getBoundingClientRect();
      _positionDropdown(rect);
      _populateDropdown(suggestions);
    }

    function _positionTooltip(rect) {
      tooltip.style.left = rect.left + window.scrollX + 'px';
      tooltip.style.top = (rect.bottom + window.scrollY + 4) + 'px';
      tooltip.style.minWidth = rect.width + 'px';
    }

    function _showTooltipFor(duration) {
      tooltip.classList.remove('hidden');
      clearTimeout(tooltipHideTimer);
      if (duration) tooltipHideTimer = setTimeout(function() { tooltip.classList.add('hidden'); }, duration);
    }

    function _getCharPosFromMouseX(mouseX, inputEl) {
      var canvas = document.createElement('canvas');
      var ctx = canvas.getContext('2d');
      var style = window.getComputedStyle(inputEl);
      ctx.font = style.fontSize + ' ' + style.fontFamily;
      var rect = inputEl.getBoundingClientRect();
      var paddingLeft = parseFloat(style.paddingLeft) || 0;
      var relX = mouseX - rect.left - paddingLeft;
      var text = inputEl.value;
      for (var i = 0; i <= text.length; i++) {
        if (ctx.measureText(text.slice(0, i)).width >= relX) return i;
      }
      return text.length;
    }

    function _fnAtCursor(formula, pos) {
      var s = formula.slice(1); // strip leading '='
      pos = Math.max(0, pos - 1);
      // walk backwards from pos to find innermost function call
      var depth = 0;
      for (var i = pos; i >= 0; i--) {
        if (s[i] === ')') { depth++; continue; }
        if (s[i] === '(') {
          if (depth > 0) { depth--; continue; }
          // found opening paren for innermost function — get name before it
          var fnEnd = i;
          var fnStart = fnEnd;
          while (fnStart > 0 && /\w/.test(s[fnStart - 1])) fnStart--;
          var fn = s.slice(fnStart, fnEnd);
          if (!fn) return null;
          if (fnStart > 0 && s[fnStart - 1] === '.') {
            var nsEnd = fnStart - 1, nsStart = nsEnd;
            while (nsStart > 0 && /\w/.test(s[nsStart - 1])) nsStart--;
            return { namespace: s.slice(nsStart, nsEnd), fnName: fn };
          }
          return { namespace: '__fn__', fnName: fn };
        }
      }
      return null;
    }

    function _buildRichHint(namespace, fnName, fnInfo, resolvedValue) {
      var isBare = namespace === '__fn__';
      var sig = isBare
        ? fnName + '(...)'
        : namespace + '.' + fnName + '(' + (fnInfo ? fnInfo.params.map(function(p) { return p.name; }).join(', ') : '') + ')';
      var html = '<div style="padding:6px 10px 4px;font-family:\'JetBrains Mono\',monospace;font-size:11px">'
        + '<code style="color:var(--accent)">' + esc(sig) + '</code></div>';
      if (fnInfo && fnInfo.description) {
        html += '<div style="padding:2px 10px 6px;font-size:11px;color:var(--text-2)">' + esc(fnInfo.description) + '</div>';
      }
      if (fnInfo && fnInfo.params.length) {
        html += '<div style="border-top:1px solid var(--line);padding:4px 10px">';
        html += fnInfo.params.map(function(p) {
          return '<div style="display:flex;justify-content:space-between;padding:2px 0;font-family:\'JetBrains Mono\',monospace;font-size:10px">'
            + '<code style="color:var(--text-1)">' + esc(p.name) + '</code>'
            + '<span style="color:var(--text-3)">' + esc(p.type) + (p.default !== undefined ? ' = ' + p.default : '') + '</span>'
            + '</div>';
        }).join('');
        html += '</div>';
      }
      if (resolvedValue) {
        html += '<div style="border-top:1px solid var(--line);padding:5px 10px;font-family:\'JetBrains Mono\',monospace;font-size:11px">'
          + '<span style="color:var(--accent)">' + esc(resolvedValue) + '</span></div>';
      }
      return html;
    }

    async function _showRichHint(mouseX) {
      var formula = input.value;
      if (!formula.startsWith('=') || !tooltip) return;
      var charPos = mouseX !== undefined ? _getCharPosFromMouseX(mouseX, input) : input.selectionStart;
      var ctx = _fnAtCursor(formula, charPos);
      if (!ctx) { tooltip.classList.add('hidden'); return; }
      try {
        var meta = await _loadResolverMeta();
        var fnInfo = (meta[ctx.namespace] || {})[ctx.fnName];
        if (!fnInfo) { tooltip.classList.add('hidden'); return; }
        var resolvedValue = null;
        // only fetch preview for the specific sub-expression around cursor
        try {
          var preview = await api('POST', '/api/resolvers/preview', { formula: formula });
          resolvedValue = preview.result;
        } catch(e) {}
        var rect = input.getBoundingClientRect();
        tooltip.innerHTML = _buildRichHint(ctx.namespace, ctx.fnName, fnInfo, resolvedValue);
        _positionTooltip(rect);
        _showTooltipFor(0);
      } catch(e) {}
    }

    async function _updatePreview() {
      var formula = input.value;
      if (!formula.startsWith('=')) { ghost.style.display = 'none'; return; }
      try {
        var preview = await api('POST', '/api/resolvers/preview', { formula: formula });
        if (preview.result) {
          ghost.textContent = '→ ' + preview.result;
          ghost.style.display = 'block';
        } else {
          ghost.style.display = 'none';
        }
      } catch(e) { ghost.style.display = 'none'; }
    }

    function _updateFormulaStyle() {
      var isFormula = input.value.startsWith('=');
      input.classList.toggle('formula-active', isFormula);
      input.spellcheck = !isFormula;
      if (!isFormula) { ghost.style.display = 'none'; ghost.textContent = ''; }
    }

    input.addEventListener('input', function() {
      _updateFormulaStyle();
      _showDropdown();
      clearTimeout(previewTimer);
      previewTimer = setTimeout(_updatePreview, 400);
    });

    var hintTimer = null;
    input.addEventListener('mousemove', function(e) {
      if (!input.value.startsWith('=')) return;
      clearTimeout(hintTimer);
      hintTimer = setTimeout(function() { _showRichHint(e.clientX); }, 120);
    });
    input.addEventListener('mouseleave', function() {
      clearTimeout(hintTimer);
      if (tooltip) tooltip.classList.add('hidden');
    });

    _updateFormulaStyle();

    input.addEventListener('keydown', function(e) {
      var dropdownOpen = !dropdown.classList.contains('hidden');
      if (e.key === 'Escape') {
        dropdown.classList.add('hidden'); state.items = [];
        if (tooltip) tooltip.classList.add('hidden');
        return;
      }
      if ((e.ctrlKey || e.metaKey) && e.key === ' ') {
        e.preventDefault();
        var parenContext = _parseParenContext();
        if (parenContext) {
          _showParamHint(parenContext.namespace, parenContext.fnName, parenContext.partial !== null ? parenContext.partial : undefined, parenContext.usedParams);
        } else if (input.value.startsWith('=')) {
          _showRichHint();
        } else {
          _showDropdown();
        }
        return;
      }
      if (!dropdownOpen || !state.items.length) return;
      if (e.key === 'ArrowDown') {
        e.preventDefault(); _highlightItem((state.selectedIndex + 1) % state.items.length);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault(); _highlightItem((state.selectedIndex - 1 + state.items.length) % state.items.length);
      } else if (e.key === 'Enter' || e.key === 'Tab') {
        if (state.selectedIndex >= 0) { e.preventDefault(); _applyItem(state.items[state.selectedIndex]); }
        else if (state.items.length === 1) { e.preventDefault(); _applyItem(state.items[0]); }
      }
    });

    input.addEventListener('blur', function() {
      clearTimeout(previewTimer);
      clearTimeout(tooltipHideTimer);
      if (tooltip) tooltip.classList.add('hidden');
      ghost.style.display = 'none';
      setTimeout(function() { dropdown.classList.add('hidden'); state.items = []; state.selectedIndex = -1; }, 150);
    });
  });
}
