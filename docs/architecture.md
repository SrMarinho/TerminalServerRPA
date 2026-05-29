# Arquitetura

## Visão geral

O TerminalServerRPA é uma aplicação RPA nativa de Windows com interface web local, armazenamento de credenciais criptografado e um motor de automação. A arquitetura segue camadas de Clean Architecture dentro de um único processo, servida via FastAPI.

```
Usuário (navegador) ←→ FastAPI (localhost) ←→ Task Runner ←→ Playwright (Chromium)
                          ↕                          ↕
                    Cofre (keyring)         structlog → arquivo JSON / WS
```

## Mapa de módulos

```
main.py                                 Entrypoint Typer
├── web                                 Inicia o servidor FastAPI (uvicorn)
├── vault                               Delega aos comandos de cofre da CLI
├── run                                 Executa uma tarefa RPA
├── logs                                Lê o arquivo de log filtrado
└── shutdown                            Encerra o servidor em execução

src/interfaces/web/                     Adaptador da interface web
├── server.py                           Fábrica do app FastAPI + runner uvicorn
│   ├── find_free_port()                Descoberta de porta via socket
│   ├── lifespan                        Inicia o consumidor de broadcast do WebSocket
│   └── run_server()                    Checagem de instância única + start
├── router.py                           Rotas FastAPI: credenciais, tarefas, execuções, WS
│   └── verify_token()                  Autenticação por token (Bearer/query) nas rotas /api/*
├── websocket.py                        ConnectionManager + broadcast fila→WS
├── static/js/                          UI single-page (Tailwind CSS) em JS vanilla
└── templates/index.html               Casca HTML da UI

src/interfaces/cli/                     Adaptador da CLI
└── cli.py                              Comandos de cofre, run, logs, shutdown

src/infrastructure/                     Infraestrutura
├── vault.py                            Cofre de credenciais criptografado
│   ├── keyring                         Gerenciador de Credenciais do Windows
│   ├── Fernet (cryptography)           Criptografia simétrica
│   └── índice criptografado            Mapeia serviço→usuários
├── task_runner.py                      Máquina de estados assíncrona
│   ├── TaskStatus                      idle→running↔paused→completed|failed|cancelled
│   ├── report_step()                   Reporta passo, checa breakpoints/skip
│   └── TaskPool                        Gerencia execuções concorrentes
├── execution_manager.py               Persistência de execuções e passos (SQLite) + eventos
├── task_registry.py                    Registro de tarefas + auto-descoberta
├── task_config.py                      Persistência de parâmetros das tarefas
├── logger.py                           Configuração do structlog
│   ├── RotatingFileHandler             Arquivo rotativo (JSON)
│   ├── handler de console              Saída colorida para dev
│   └── ponte para fila assíncrona      Empurra eventos para broadcast no WebSocket
├── single_instance.py                  Mutex do Windows + foco via socket + token de API
└── updater.py                          Verificação e download de releases do GitHub

src/automation/pages/                   Page Objects do Playwright (telas do ERP Senior)
├── ts_login_page.py                    Login no Terminal Server
├── senior_login_page.py               Login no ERP Senior (template matching + OCR)
├── home_page.py                        Navegação na sidebar (template matching)
└── ...                                 Demais telas (seleção de modelos, valores de entrada)

src/automation/tasks/                   Fluxos orquestrados
└── report_generation.py               Tarefa "Relatório Contas Receber"

src/core/entities/  +  src/core/use_cases/   Camada de domínio (entidades e casos de uso)
src/config/settings.py                  Configuração de runtime (ASSETS_DIR, DEV_MODE)
src/utils/                              Auxiliares (image_match, window_utils)
```

## Fluxo de dados (execução de tarefa)

```
1. Usuário clica em "Executar" no navegador
2. POST /api/run/{task_name} → router.py
3. router chama TaskPool.start(task_name, params) → cria execução + Task assíncrona
4. TaskRunner.run() define status=RUNNING e chama o handler da tarefa
5. A tarefa abre o Chromium via Playwright e percorre os Page Objects
6. A cada passo: report_step() persiste o status e checa pausa/cancelamento/skip
7. Eventos (passo, log, screenshot) são transmitidos por WebSocket aos clientes
8. Ao concluir: status=COMPLETED (ou FAILED/CANCELLED); o navegador é fechado no finally
```

## Fallback de porta

```
run_server(port=8080)
  → find_free_port(8080)
    → socket.connect_ex(("127.0.0.1", 8080))
      → 0 (ocupada) → tenta 8081 → ... → encontra porta livre
    → retorna actual_port
  → save_port(actual_port) em %LOCALAPPDATA%/TerminalServerRPA/port.txt
  → webbrowser.open(f"http://127.0.0.1:{actual_port}")
  → uvicorn.run(port=actual_port)
```

## Protocolo de instância única

```
Primeira instância:
  → CreateMutex("TerminalServerRPA-{dirhash}") tem sucesso
  → Inicia o servidor, salva a porta
  → Escuta requisições HTTP em /_focus

Segunda instância:
  → CreateMutex falha (ERROR_ALREADY_EXISTS)
  → Lê a porta de %LOCALAPPDATA%/TerminalServerRPA/port.txt
  → GET http://127.0.0.1:{port}/_focus
  → Encerra

Instância existente:
  → /_focus traz a aba do navegador para frente
```

## Sistema de logs

```
Código da aplicação → structlog (síncrono)
                       ├── RotatingFileHandler → logs/TerminalServerRPA.jsonl
                       ├── StreamHandler → stderr (console de dev)
                       └── fila assíncrona → broadcast no WebSocket
```

A ponte de fila assíncrona em `logger.py` (`_ws_processor`) empurra cada evento de log para uma `asyncio.Queue`. A corrotina `broadcast_from_queue` em `websocket.py` drena essa fila e transmite a todos os clientes WebSocket conectados.
