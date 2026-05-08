# Execution Manager + Step-by-step Log + History

## Motivation

Tasks have multiple steps. Users need to see each step in real-time and browse execution history.

## 1. ExecutionManager

**File:** `src/infrastructure/execution_manager.py`

```python
@dataclass
class Step:
    name: str
    status: str  # pending | running | completed | failed
    timestamp: str

@dataclass
class Execution:
    id: str
    task_name: str
    status: str       # running | paused | completed | failed | cancelled
    started_at: str
    finished_at: str | None
    steps: list[Step]
    params: dict
    result: dict | None

class ExecutionManager:
    def create(task_name, params) -> str       # returns execution_id
    def get_step(execution_id, step_name, status)
    def complete(execution_id, result)
    def fail(execution_id, error)
    def cancel(execution_id)
    def list() -> list[Execution]
    def get(id) -> Execution | None
```

Persistence: `.local/executions/{id}.json` (one file per execution).

Limit: keep last 100 executions, auto-prune oldest.

## 2. TaskRunner

Add to TaskRunner:
- `report_step(name)` — calls `ExecutionManager.set_step(current_exec_id, name, "running")`
- `_execute()` creates execution via `ExecutionManager.create()`
- On complete/fail/cancel, calls manager.complete/fail/cancel

## 3. Tasks call report_step

```python
# BulkUserRegistrationTask.execute():
await self._runner.report_step("login")
await login_p.navigate()
await login_p.login(...)

await self._runner.report_step("validate")
result = use_case.execute(users)

for user in result.success:
    await self._runner.report_step(f"register:{user.username}")
    await reg_p.register(...)
```

## 4. WebSocket events (server → client)

| Event | Payload |
|-------|---------|
| `execution:created` | `{id, task_name, status, started_at}` |
| `execution:step` | `{id, step: {name, status, timestamp}}` |
| `execution:status` | `{id, status, finished_at, result}` |

## 5. Router

`GET /api/executions` → returns all executions (descending order)

## 6. Frontend

- Sidebar: **Tarefas** 01 | **Histórico** 02 | **Credenciais** 03
- History panel: execution cards, most recent first
- Each card: task name, status badge, duration, clickable steps list
- Step icons: ● running ✓ ok ✗ failed ○ pending
- WebSocket updates in real-time

## Files changed

| File | Action |
|------|--------|
| `src/infrastructure/execution_manager.py` | new |
| `src/infrastructure/task_runner.py` | add report_step(), integrate manager |
| `src/interfaces/web/router.py` | + GET /api/executions |
| `src/interfaces/web/websocket.py` | broadcast execution events |
| `src/interfaces/web/templates/index.html` | sidebar + history panel + WS listener |
| `src/automation/tasks/bulk_user_registration_task.py` | add report_step() calls |
| `.gitignore` | + `.local/executions/` |
| `tests/...` | tests for ExecutionManager |

## Questions

- Persistence limit: keep 100 most recent?
- Step icons: ● running ✓ ok ✗ failed ○ pending — ok?
- Auto-prune on startup or on each new execution?
