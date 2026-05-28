async function loadCredentials() {
  try {
    const data = await api('GET', '/api/credentials');
    document.getElementById('credCount').textContent = String(data.length).padStart(2, '0') + ' / ' + String(data.length).padStart(2, '0');
    document.getElementById('credList').innerHTML = data.length
      ? data.map((c, i) => '<div class="cred-row fade-up" style="animation-delay:' + (i * 0.03) + 's"><div class="flex items-center gap-4 min-w-0"><div class="text-[10px] tabular-nums" style="color:var(--text-3)">' + String(i + 1).padStart(2, '0') + '</div><div class="min-w-0"><div class="text-sm font-medium truncate" style="color:var(--text-0)">' + esc(c.service) + '</div><div class="text-[11px] truncate" style="color:var(--text-2)">' + esc(c.usernames.join(' · ')) + '</div></div></div><div class="flex gap-2"><button class="btn" style="padding:6px 12px;font-size:11px" onclick="editCred(\'' + esc(c.service) + '\',\'' + esc(c.usernames[0] || '') + '\')">editar</button><button class="btn btn-danger" style="padding:6px 12px;font-size:11px" onclick="deleteCred(\'' + esc(c.service) + '\')"><svg width="10" height="10" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>remover</button></div></div>').join('')
      : '<div class="card p-8 text-center" style="border-style:dashed"><div class="text-sm mb-1" style="color:var(--text-1)">Nenhuma credencial salva</div><div class="text-xs" style="color:var(--text-3)">Adicione sua primeira entrada acima para começar</div></div>';
  } catch (e) { toast('Falha ao carregar credenciais', true); }
}

function editCred(service, username) {
  document.getElementById('service').value = service;
  document.getElementById('username').value = username;
  document.getElementById('password').value = '';
  document.getElementById('password').focus();
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
