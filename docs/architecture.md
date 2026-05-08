# Architecture

## Overview

senior-rpa is a Windows-native RPA application with a local web UI, encrypted credential storage, and an automation engine. The architecture follows clean architecture layers within a single process, served via FastAPI.

```
User (browser) ←→ FastAPI (localhost) ←→ Task Runner ←→ Playwright (Chromium)
                     ↕                            ↕
                 Keyring vault              structlog → JSON file / WS
```

## Module map

```
main.py                                 Typer entrypoint
├── web                                 Start FastAPI server (uvicorn)
├── vault                               Delegate to CLI vault commands
├── run                                 Execute an RPA task
└── logs                                Read filtered log file

src/password_vault/                     Backend core
├── server.py                           FastAPI app factory + uvicorn runner
│   ├── find_free_port()                Socket-based port discovery
│   ├── is_first_instance()             Windows mutex check
│   ├── save_port() / read_port()       Port persistence for IPC
│   └── focus_existing_instance()       HTTP request to running instance
├── router.py                           FastAPI router: credentials, tasks, WS, /_focus
├── vault.py                            Encrypted credential store
│   ├── keyring                         Windows Credential Manager (backend-agnostic)
│   ├── Fernet (cryptography)           AES-128-CBC encryption
│   └── encrypted index                 Tracks service→username mappings
├── cli.py                              Typer vault commands + log reader
├── task_runner.py                      Async state machine
│   ├── TaskStatus                      idle→running↔paused→completed|failed|cancelled
│   ├── checkpoint()                    Yields control for pause/cancel
│   └── _execute()                      Dispatches to registered task handlers
├── websocket.py                        ConnectionManager + async queue→WS broadcast
├── logger.py                           structlog configuration
│   ├── JSON file handler               Rotating file (10MB, 5 backups)
│   ├── console handler                 Colorized dev output
│   └── async queue processor           Pushes events to WebSocket broadcast
├── single_instance.py                  Windows mutex + socket-based focus IPC
├── updater.py                          GitHub Releases check + asset download
└── templates/index.html                Tailwind CSS single-page UI

src/core/entities/                      Domain models
└── user.py                             User dataclass with validation

src/core/use_cases/                     Business logic
└── register_users_use_case.py          User registration pipeline + duplicate detection

src/automation/pages/                   Playwright Page Objects
├── login_page.py                       Login form interaction
└── user_registration_page.py           Registration form interaction

src/automation/tasks/                   Orchestrated workflows
└── bulk_user_registration_task.py      Login → validate → register each user
```

## Data flow (task execution)

```
1. User clicks "Run" in browser
2. POST /api/run/bulk-register-users → router.py
3. router calls asyncio.create_task(runner.run("bulk-register-users"))
4. TaskRunner.run() sets status=RUNNING, calls _execute()
5. _execute dispatches to _bulk_register_users()
6. Playwright launches headless Chromium
7. LoginPage.navigate() → LoginPage.login()
8. UseCase validates users
9. For each valid user: UserRegistrationPage.register()
10. On complete: status=COMPLETED
11. All checkpoints yield to event loop for pause/cancel
```

## Port fallback

```
run_server(port=8080)
  → find_free_port(8080)
    → socket.connect_ex(("127.0.0.1", 8080))
      → 0 (busy) → try 8081 → ... → find free port
    → returns actual_port
  → save_port(actual_port) to %LOCALAPPDATA%/senior-rpa/port.txt
  → webbrowser.open(f"http://127.0.0.1:{actual_port}")
  → uvicorn.run(port=actual_port)
```

## Single instance protocol

```
First instance:
  → CreateMutex("SeniorRPA-{dirhash}") succeeds
  → Start server, save port
  → Listen for HTTP requests on /_focus

Second instance:
  → CreateMutex fails (ERROR_ALREADY_EXISTS)
  → Read port from %LOCALAPPDATA%/senior-rpa/port.txt
  → GET http://127.0.0.1:{port}/_focus
  → Exit

Existing instance:
  → /_focus calls webbrowser.open(url) to bring tab to front
```

## Log system

```
Application code → structlog (sync)
                    ├── RotatingFileHandler → logs/senior-rpa.jsonl
                    ├── StreamHandler → stderr (dev console)
                    └── Async queue → WebSocket broadcast
```

The async queue bridge in `logger.py` (`_ws_processor`) pushes every log event into an `asyncio.Queue`. The `websocket.py` `broadcast_from_queue` coroutine drains this queue and broadcasts to all connected WebSocket clients.
