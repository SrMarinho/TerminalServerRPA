// ---------------------------------------------------------------------------
// Agendamentos — recurring task schedules (cron)
// ---------------------------------------------------------------------------

const _DOW_PT = ['domingo', 'segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado'];

function schedFreqChanged() {
  var freq = document.getElementById('schedFreq').value;
  document.getElementById('schedTimeWrap').classList.toggle('hidden', freq === 'custom');
  document.getElementById('schedDowWrap').classList.toggle('hidden', freq !== 'weekly');
  document.getElementById('schedCronWrap').classList.toggle('hidden', freq !== 'custom');
}

function _buildCron() {
  var freq = document.getElementById('schedFreq').value;
  if (freq === 'custom') return document.getElementById('schedCron').value.trim();
  var t = (document.getElementById('schedTime').value || '07:00').split(':');
  var minute = parseInt(t[1], 10), hour = parseInt(t[0], 10);
  if (freq === 'weekly') return minute + ' ' + hour + ' * * ' + document.getElementById('schedDow').value;
  return minute + ' ' + hour + ' * * *';
}

function _cronHuman(cron) {
  var p = cron.trim().split(/\s+/);
  if (p.length !== 5) return cron;
  var hhmm = function() { return String(p[1]).padStart(2, '0') + ':' + String(p[0]).padStart(2, '0'); };
  if (/^\d+$/.test(p[0]) && /^\d+$/.test(p[1])) {
    if (p[2] === '*' && p[3] === '*' && p[4] === '*') return 'diário às ' + hhmm();
    if (p[2] === '*' && p[3] === '*' && /^\d$/.test(p[4])) return _DOW_PT[+p[4]] + ' às ' + hhmm();
  }
  return cron;
}

async function loadSchedules() {
  // populate the task select once per visit
  try {
    var tasks = await api('GET', '/api/tasks');
    var sel = document.getElementById('schedTask');
    sel.innerHTML = tasks.available.map(function(t) {
      return '<option value="' + t + '">' + (t.split(':').pop()) + '</option>';
    }).join('');
  } catch (e) {}
  refreshSchedules();
}

async function refreshSchedules() {
  var list = document.getElementById('schedList');
  try {
    var rows = await api('GET', '/api/schedules');
    document.getElementById('schedCount').textContent = rows.length || '—';
    if (!rows.length) {
      list.innerHTML = '<div class="text-xs" style="color:var(--text-3)">Nenhum agendamento.</div>';
      return;
    }
    list.innerHTML = rows.map(function(s) {
      var last = s.last_run ? s.last_run.slice(0, 16).replace('T', ' ') : 'nunca';
      return '<div class="card p-4 flex items-center gap-4">' +
        '<div class="flex-1 min-w-0">' +
          '<div class="text-sm truncate" style="color:var(--text-0)">' + s.task_name.split(':').pop() + '</div>' +
          '<div class="text-[11px]" style="color:var(--text-2)">' + _cronHuman(s.cron) +
            ' <span style="color:var(--text-3)">· cron: ' + s.cron + ' · última: ' + last + '</span></div>' +
        '</div>' +
        '<button class="btn btn-ghost" style="padding:5px 12px;font-size:11px" onclick="toggleSchedule(' + s.id + ',' + !s.enabled + ')">' +
          (s.enabled ? 'pausar' : 'ativar') + '</button>' +
        '<span class="dot ' + (s.enabled ? 'dot-running' : 'dot-idle') + '"></span>' +
        '<button class="btn btn-ghost" style="padding:5px 10px;font-size:11px;color:var(--text-3)" onclick="deleteSchedule(' + s.id + ')">excluir</button>' +
      '</div>';
    }).join('');
  } catch (e) {
    list.innerHTML = '<div class="text-xs" style="color:var(--text-3)">Erro: ' + e.message + '</div>';
  }
}

async function createSchedule() {
  var task = document.getElementById('schedTask').value;
  var cron = _buildCron();
  if (!task || !cron) { toast('Preencha tarefa e frequência', true); return; }
  try {
    await api('POST', '/api/schedules', { task_name: task, cron: cron });
    toast('Agendamento criado');
    refreshSchedules();
  } catch (e) { toast('Erro: ' + e.message, true); }
}

async function toggleSchedule(id, enabled) {
  try {
    await api('PATCH', '/api/schedules/' + id, { enabled: enabled });
    refreshSchedules();
  } catch (e) { toast('Erro: ' + e.message, true); }
}

async function deleteSchedule(id) {
  try {
    await api('DELETE', '/api/schedules/' + id);
    toast('Agendamento removido');
    refreshSchedules();
  } catch (e) { toast('Erro: ' + e.message, true); }
}
