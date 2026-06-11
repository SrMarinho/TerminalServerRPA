# Roadmap do TerminalServerRPA

Marcos concluídos e trabalho planejado, ranqueado por valor÷custo. Decisões
arquiteturais em [decisions/](decisions/); histórico detalhado no
[CHANGELOG](../CHANGELOG.md).

## Concluído ✅

- **Logs estruturados** — structlog (JSON + console) com correlação de trace
  por `execution_id` via contextvars.
- **Task Runner** — máquina de estados (`IDLE → RUNNING ↔ PAUSED → COMPLETED |
  FAILED | CANCELLED`), checkpoints de pausa/cancel/skip, breakpoints por passo.
- **Persistência** — SQLite WAL com migrações versionadas (`PRAGMA
  user_version`), `ExecutionRepository` + `BreakpointStore`.
- **Event bus** — infra publica, web assina; zero import infra→interfaces.
- **Cofre de senhas** — keyring + Fernet; CLI + REST; senha nunca sai pela API.
- **Sistema de plugins** — SDK `tsrpa` (fronteira única), manifesto
  `plugin.toml`, hot reload via `POST /api/plugins/reload`.
- **Instância única** — mutex Windows + foco via socket + token no keyring.
- **Auto-atualização** — GitHub Releases com checksum fail-closed; release
  publicada automaticamente no repo `TerminalServerRPA-releases`.
- **Interface web** — SPA (Tailwind), WebSocket ao vivo, screenshots,
  devtools (snippets/OCR) em DEV_MODE.
- **Qualidade** — 250 testes (unit + integração real SQLite/event bus/runner),
  ruff, pyright, CI.

## Em andamento 🚧

1. **Fila de execução** — enfileirar quando ocupado em vez de rejeitar (409).
2. **Agendador de tarefas** — APScheduler + tabela `schedules`; execução
   recorrente (cron) com UI de agendamentos.
3. **Frontend offline-first** — vendorizar Tailwind/CodeMirror/fonts; zero
   dependência de CDN em runtime (rede corporativa fechada).

## Próximos 📋

4. **Dashboard de estatísticas** — execuções/dia, taxa de falha por task,
   duração média (`GET /api/stats` + painel; dados já existem no SQLite).
5. **Notificações de resultado** — webhook/e-mail/Teams ao completar/falhar;
   assina o event bus (`execution:status`).
6. **Retry/wait declarativo no SDK** — `wait_for_template(page, img, timeout)`
   no `tsrpa` (tenacity ou helper próprio); reduz flakiness dos plugins.
7. **OCR melhor** — avaliar `rapidocr-onnxruntime` no lugar do Tesseract
   (pip puro, sem binário externo, precisão superior em PT-BR); trocar atrás
   de `find_text`/`find_text_position` sem mudar plugins. Validar peso no
   bundle (~60 MB) e latência.
8. **E2E da UI web** — pytest-playwright contra o servidor real (task fake,
   steps/logs/screenshot via WS).
9. **Artefatos por execução** — vincular downloads à execução + "abrir pasta".
10. **Hot-reload de plugins em dev** — `watchfiles` (já é dep) observando
    `plugins/` em DEV_MODE.
11. **Settings tipado** — `pydantic-settings` no lugar de globals mutáveis
    (`DEV_MODE` mutado em runtime); fazer quando tocar em config.
12. **Backup/export do vault** — export cifrado por senha (PBKDF2 → Fernet).
13. **Assinatura Authenticode** — assinar o installer e validar no
    auto-update (requer certificado de code signing).

## Avaliado e rejeitado ❌

- **Alembic/ORM** — migrations próprias via `user_version` atendem; sem ORM
  não há autogenerate (o principal valor do Alembic).
- **OpenTelemetry** — overkill para desktop single-user; structlog +
  `execution_id` resolve.
- **Reescrita do frontend (React/Svelte)** — ~1,6k linhas de vanilla JS
  funcionais e testadas manualmente; reescrever não paga.
- **Multi-browser concorrente** — limite single-task é intencional (uma
  sessão de ERP por vez); a fila resolve a fricção.
- **aiosqlite** — `add_log` síncrono bloqueia o loop por ~ms; WAL+NORMAL
  mitiga. Refactor grande, ganho pequeno no perfil atual.
