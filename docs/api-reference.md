# API reference

All endpoints are served by the local FastAPI server at `http://127.0.0.1:{port}`.

## Credentials

### List all services

```
GET /api/credentials
```

Returns an array of services with their usernames:

```json
[
  {"service": "erp-system", "usernames": ["admin", "backup"]}
]
```

### Save a credential

```
POST /api/credentials
Content-Type: application/json

{"service": "erp-system", "username": "admin", "password": "secret123"}
```

Returns `{"status": "ok"}` on success.

Returns `400` if `service`, `username`, or `password` is missing.

### Get a credential

```
GET /api/credentials/{service}?username={username}
```

Returns:

```json
{"service": "erp-system", "username": "admin", "password": "secret123"}
```

Returns `404` if credential not found.
Returns `400` if `username` query param is missing.

### Delete a credential

```
DELETE /api/credentials/{service}
```

Deletes all credentials for the given service. Returns `{"status": "deleted"}`.

## Tasks

### List available tasks

```
GET /api/tasks
```

```json
{"available": ["bulk-register-users"], "current_status": "idle"}
```

Status values: `idle`, `running`, `paused`, `completed`, `failed`, `cancelled`.

### Run a task

```
POST /api/run/{task_name}
```

Starts the task asynchronously. Returns `{"status": "started", "task": "bulk-register-users"}`.

Returns `409` if a task is already running.

### Pause task

```
POST /api/tasks/pause
```

Pauses the currently running task. No-op if no task is running.

### Resume task

```
POST /api/tasks/resume
```

Resumes a paused task. No-op if task is not paused.

### Cancel task

```
POST /api/tasks/cancel
```

Requests cancellation of the running or paused task.

## System

### Focus existing instance

```
GET /_focus
```

Brings the existing instance's browser tab to front. Used by the single-instance mutex protocol.

### Web interface

```
GET /
```

Serves the Tailwind CSS web UI (`index.html`).

## WebSocket

```
ws://127.0.0.1:{port}/ws
```

### Server → Client events

All events are JSON with a `type` field:

| Type | Payload | Description |
|------|---------|-------------|
| `log` | `{event, level, msg, timestamp}` | Structured log line |
| `status` | `{task_id, status, progress}` | Task state change |

### Client → Server commands

| Type | Payload | Action |
|------|---------|--------|
| `pause` | `{}` | Pause running task |
| `resume` | `{}` | Resume paused task |
| `cancel` | `{}` | Cancel task |
| `run` | `{task_name}` | Start a task |
