# senior-rpa

RPA application with local web UI, encrypted credential vault, task runner, and auto-update.

## Features

- **Password vault** — AES-encrypted credentials via Windows Credential Manager (keyring + Fernet)
- **Web UI** — Tailwind CSS frontend served by FastAPI (localhost)
- **CLI** — Typer-based interface for vault management and task execution
- **Task runner** — State machine with pause/resume/cancel, WebSocket live log streaming
- **Single instance** — Windows mutex prevents duplicate processes; focus existing on re-launch
- **Auto-update** — GitHub release check + download
- **Port fallback** — auto-selects next available port if 8080 is busy

## Quick start

```bash
# Install dependencies
uv sync

# Run web UI
uv run python main.py web

# Manage credentials (CLI)
uv run python main.py vault set my-service -u my-user
uv run python main.py vault get my-service
uv run python main.py vault list

# View logs
uv run python main.py logs --level error

# Run RPA task
uv run python main.py run bulk-register-users
```

## Development

```bash
# Tests
uv run pytest

# Lint
uv run ruff check

# Type check
uv run pyright src

# Format
uv run ruff format

# Build executable
uv run pyinstaller main.spec
```

## Architecture

```
main.py — Typer entrypoint (web | vault | run | logs)
src/
  password_vault/   Web server, vault, CLI, task runner, updater
  automation/       Playwright Page Objects and RPA tasks
  core/             Domain entities and use cases
  config/           Runtime configuration
  utils/            Shared helpers
```

## Project status

Implemented: vault, CLI, web UI, task runner, single instance, auto-updater, structured logging, port fallback, CI (GitHub Actions), type checking (pyright), linting (ruff), Playwright RPA tasks.

Next: release workflow, Playwright-based end-to-end tests, type coverage improvements.
