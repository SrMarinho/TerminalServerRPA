# CLI reference

The application entrypoint is a single Typer command:

```
python main.py <command> [options]
```

## Global options

None. Each subcommand has its own options.

## Commands

### `web`

Start the web UI server.

```
python main.py web [--port PORT] [--no-browser]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--port` | int | 8080 | Port to bind (falls back on next free port) |
| `--browser` / `--no-browser` | bool | True | Auto-open browser on start |

### `vault`

Credential management subcommands.

```
python main.py vault <subcommand> [options]
```

#### `vault set`

Save or update a credential.

```
python main.py vault set <service> -u <username>
```

Prompts for password (hidden input).

#### `vault get`

Retrieve a credential.

```
python main.py vault get <service> -u <username>
```

Exits with code 1 if credential not found.

#### `vault delete`

Delete all credentials for a service.

```
python main.py vault delete <service>
```

#### `vault list`

List all stored services and their usernames.

```
python main.py vault list
```

### `run`

Execute an RPA task.

```
python main.py run <task_name>
```

| Argument | Description |
|----------|-------------|
| `task_name` | Name of the registered task (e.g. `bulk-register-users`) |

### `logs`

View application logs.

```
python main.py logs [--level LEVEL] [--since SINCE] [--task TASK] [--json]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--level` | str | `info` | Minimum log level (`debug`, `info`, `warning`, `error`) |
| `--since` | str | `""` | Show logs since duration (e.g. `1h`, `30m`) |
| `--task` | str | `""` | Filter by task name |
| `--json` | bool | False | Output raw JSON lines instead of formatted |
