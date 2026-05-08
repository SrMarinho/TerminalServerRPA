# User guide

## Starting the web UI

```bash
# Default port 8080, opens browser automatically
python main.py web

# Custom port, no browser
python main.py web --port 9090 --no-browser
```

If port 8080 is busy, the app tries 8081, 8082, etc. until it finds a free port.

If the app is already running, the second instance focuses the existing browser tab instead of starting a second server.

## Managing credentials

### Via web UI

1. Open `http://127.0.0.1:PORT` in your browser
2. Under **Credentials**, fill in Service, Username, Password
3. Click **Save**
4. Saved credentials appear in the list below the form
5. Click **Delete** to remove a credential

### Via CLI

```bash
# Save a credential (password prompted securely)
python main.py vault set my-service -u admin

# Retrieve a credential
python main.py vault get my-service -u admin

# Delete all credentials for a service
python main.py vault delete my-service

# List all stored credentials
python main.py vault list
```

Credentials are encrypted with Fernet (AES-128-CBC) before being stored in the Windows Credential Manager via the `keyring` library. The encryption key is itself stored in the Credential Manager.

## Running RPA tasks

### Via web UI

1. In the **Tasks** section, click the task name (e.g. `bulk-register-users`)
2. The status badge indicates progress: running, paused, completed, failed
3. Use **Pause**, **Resume**, **Cancel** to control execution
4. Live log output appears in the **Log** panel

### Via CLI

```bash
# Execute a task
python main.py run bulk-register-users
```

## Viewing logs

All events are logged to `logs/senior-rpa.jsonl` in structured JSON format (one line per event).

```bash
# Show recent logs (tail)
python main.py logs

# Filter by level
python main.py logs --level error

# Filter by task
python main.py logs --task bulk-register-users

# Raw JSON output
python main.py logs --json
```

### Logged events

| Event | When it fires |
|-------|---------------|
| `system.startup` | Application starts |
| `system.shutdown` | Application stops |
| `system.update.available` | New GitHub release found |
| `system.update.downloaded` | Update download complete |
| `vault.credential.set` | Credential saved |
| `vault.credential.get` | Credential retrieved |
| `vault.credential.delete` | Credential deleted |
| `task.{name}.started` | Task begins |
| `task.{name}.completed` | Task finishes successfully |
| `task.{name}.failed` | Task encounters an error |
| `task.{name}.paused` | Task paused by user |
| `task.{name}.resumed` | Task resumed by user |
| `task.{name}.cancelled` | Task cancelled by user |
| `ws.connected` | Client connects via WebSocket |
| `ws.disconnected` | Client disconnects |
