# senior-rpa Roadmap

## 1. Logs Estruturados ✅

- `src/password_vault/logger.py` — structlog config
- JSON file + console output
- WebSocket bridge for live feed
- Event schema: `{event, level, timestamp, session_id, task_id, user_action, fallback, error}`

### Events tracked

```
system.startup | system.shutdown
vault.credential.set | get | delete | not_found | decrypt.failed
task.{name}.started | paused | resumed | cancelled | completed | failed | fallback
ui.button.clicked | form.submitted
ws.connected | disconnected | message
```

### CLI debug: `python main.py logs [--level] [--since] [--task] [--json]`

---

## 2. Task Runner (State Machine)

- Module: `src/password_vault/task_runner.py`
- States: `IDLE → RUNNING ↔ PAUSED → COMPLETED | FAILED | CANCELLED`
- Checkpoint system: periodic yield points check pause/cancel
- `TaskRunner.run(pause, resume, cancel)` via asyncio.Event

---

## 3. Password Vault

- `src/password_vault/vault.py` — keyring + cryptography (Fernet)
- `src/password_vault/cli.py` — Typer commands: set / get / delete / list
- `src/password_vault/router.py` — FastAPI REST endpoints
- `src/password_vault/server.py` — FastAPI + uvicorn runner

---

## 4. Single Instance

- `src/password_vault/single_instance.py`
- Windows mutex (win32event.CreateMutex)
- Named pipe IPC for second instance commands (focus / open-tab / run)
- Dep: pywin32

---

## 5. Auto-update (GitHub Releases)

- `src/password_vault/updater.py`
- Check GitHub API latest release on startup
- Download to %TEMP%, spawn updater.exe, replace, restart
- Separate `updater.py` compiled as small standalone .exe

---

## 6. Web UI & Pipeline Live View

- `src/password_vault/templates/index.html`
- WebSocket for real-time logs + status
- Pause / Resume / Cancel controls
- Token-based auth in URL

---

## 7. RPA Tasks (Playwright)

- `src/automation/pages/login_page.py`
- `src/automation/pages/user_registration_page.py`
- `src/automation/tasks/bulk_user_registration_task.py`
- `src/core/entities/user.py`
- `src/core/use_cases/register_users_use_case.py`

---

## 8. Build & Release

```
uv run pyinstaller --onefile main.py
uv run pyinstaller --onefile updater.py
```

Publish to GitHub Releases with tag vX.Y.Z.

---

## Dependencies

```
uv add fastapi uvicorn typer keyring cryptography httpx semver structlog
uv pip install pyinstaller pywin32
```
