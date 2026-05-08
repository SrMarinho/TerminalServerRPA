# Development

## Setup

```bash
# Clone and install
git clone <repo-url>
cd senior-rpa
uv sync

# Install Playwright browser for RPA tasks
uv run playwright install chromium
```

## Toolchain

| Tool | Command | Description |
|------|---------|-------------|
| uv | `uv add <pkg>` | Add production dependency |
|     | `uv add --dev <pkg>` | Add dev dependency |
|     | `uv sync` | Install all dependencies |
|     | `uv run <cmd>` | Run command in venv |
| ruff | `uv run ruff check` | Lint |
|      | `uv run ruff check --fix` | Auto-fix |
|      | `uv run ruff format` | Format code |
| pyright | `uv run pyright src` | Type check |
| pytest | `uv run pytest` | Run all tests |
|        | `uv run pytest tests/unit/password_vault/test_vault.py -v` | Single test file |
|        | `uv run pytest -k "test_login"` | Filter by name |
|        | `uv run pytest --cov=src` | With coverage |
| pyinstaller | `uv run pyinstaller main.spec` | Build .exe |

## Project conventions

### Layer rules

```
use_cases → entities
tasks → pages
utils, config → leaf modules (imported by any)
No circular imports. No layer skipping.
```

### Code style

- Target Python 3.14 (`.python-version`)
- Ruff with selected rules: E, F, I, W, N, UP, B, SIM
- Double quotes for strings
- Line length: 120
- Type annotations on all public functions
- Use `X | None` instead of `Optional[X]` (UP045)

### Naming

```
Files: snake_case.py
Classes: PascalCase
Functions: snake_case
Constants: UPPER_SNAKE
Private: _leading_underscore
```

### Test structure

```
tests/
├── unit/                    # Pure unit tests (mocked dependencies)
│   ├── password_vault/
│   ├── automation/
│   └── core/
├── integration/             # Integration tests (real keyring backend)
│   └── password_vault/
└── e2e/                     # End-to-end (CLI + vault)
    └── test_vault_flow.py
```

- Every module in `src/` must have a corresponding test file
- Use `@pytest.mark.asyncio` for async tests
- Mock external dependencies (keyring, playwright, network)
- Aim for 100% line coverage on core modules

## Testing Playwright-based tasks

The `_bulk_register_users` method in `task_runner.py` launches a real Chromium browser. In tests:

- **Unit tests**: mock `Page` with `AsyncMock` (see `tests/unit/automation/test_pages.py`)
- **Playwright dispatch**: task runner tests use `"noop-task"` to avoid hitting Playwright imports

## Building

```bash
# Main executable
uv run pyinstaller main.spec

# Updater executable (small, standalone)
uv run pyinstaller updater.spec
```

The `.spec` files are tracked in git. The `*.spec` pattern is in `.gitignore`, so force-add with `git add -f main.spec` when modifying.

### Previous build steps

1. Update version in `pyproject.toml`
2. Run tests: `uv run pytest`
3. Build: `uv run pyinstaller main.spec`
4. Test the `.exe`: `dist/senior-rpa.exe web`

## CI

GitHub Actions workflow (`.github/workflows/ci.yml`):

- Matrix: Python 3.10–3.13
- Steps: ruff check → pyright → pytest with coverage
- Playwright Chromium installed for test suite
