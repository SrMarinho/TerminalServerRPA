# Arquitetura

## Visão geral

O TerminalServerRPA é uma aplicação RPA nativa de Windows com interface web local servida dentro de uma janela pywebview (EdgeWebView2), armazenamento de credenciais criptografado e um motor de automação. A arquitetura segue camadas de Clean Architecture dentro de um único processo.

```
Usuário (pywebview) ←→ FastAPI (localhost) ←→ Task Runner ←→ Playwright (Chromium)
                           ↕                         ↕
                     Cofre (keyring)        structlog → arquivo JSON / WS
```

## Modos de execução

| Comando | Descrição |
|---------|-----------|
| `gui` (padrão) | Janela nativa pywebview + tray ao fechar + auto-update |
| `web` | Servidor FastAPI puro, abre navegador padrão |

## Mapa de módulos

```
main.py                                 Entrypoint Typer (padrão: gui ao clicar no EXE)
├── gui                                 Inicia GuiServer (pywebview)
├── web                                 Inicia WebServer (FastAPI + navegador)
├── vault                               Delega aos comandos de cofre da CLI
├── run                                 Executa uma tarefa RPA
├── logs                                Lê o arquivo de log filtrado
└── shutdown                            Encerra o servidor em execução

src/interfaces/base_server.py           BaseServer (ABC)
├── find_free_port()                    Descoberta de porta via socket
├── _setup()                            Instância única + logger + porta
└── _enable_dev_mode()                  Ativa DEV_MODE em settings

src/interfaces/gui/                     Adaptador da interface GUI (pywebview)
└── server.py                           GuiServer(BaseServer)
    ├── start()                         Garante playwright + inicia web + cria janela
    ├── _check_and_prompt_update()      Loop 60s: verifica release → dialog nativo
    ├── _on_closing()                   Minimiza para system tray ao fechar
    ├── _start_tray()                   Ícone pystray com Abrir/Sair
    └── _install_ctrl_c_handler()       SetConsoleCtrlHandler (Ctrl+C no terminal)

src/interfaces/web/                     Adaptador da interface web
├── server.py                           WebServer(BaseServer)
│   ├── start()                         Servidor standalone com navegador
│   ├── build_app()                     Fábrica FastAPI (usado pelo GuiServer)
│   ├── start_in_thread()               Uvicorn em thread daemon
│   └── _check_for_update()             Só loga — sem dialog (mode web)
├── router.py                           Rotas FastAPI: credenciais, tarefas, execuções, WS
│   └── verify_token()                  Autenticação Bearer/query nas rotas /api/*
├── websocket.py                        ConnectionManager + broadcast fila→WS
├── static/js/                          UI single-page (Tailwind CSS) em JS vanilla
└── templates/index.html               Casca HTML da UI

src/interfaces/cli/                     Adaptador da CLI
└── cli.py                              Comandos de cofre, run, logs, shutdown

src/infrastructure/                     Infraestrutura
├── vault.py                            Cofre de credenciais criptografado
├── task_runner.py                      Máquina de estados assíncrona
├── execution_manager.py               Persistência de execuções (SQLite) + eventos
├── task_registry.py                    Registro de tarefas + auto-descoberta
├── task_config.py                      Persistência de parâmetros das tarefas
├── logger.py                           Configuração do structlog
├── single_instance.py                  Mutex do Windows + foco via socket + token de API
├── updater.py                          Verificação (GitHub API + auth) + download + hot-swap
│   ├── check_for_update()              Consulta releases/latest (suporta repo privado via PAT)
│   ├── _verify_checksum()              Verifica SHA256 se asset .sha256 existir
│   └── apply_update()                  Baixa Setup.exe → batch hot-swap via Inno Setup silencioso
└── playwright_setup.py                 Garante driver playwright em disco
    └── ensure_playwright_driver()      Baixa da CDN se ausente ou versão diferente

src/automation/pages/                   Page Objects do Playwright (telas do ERP Senior)
src/automation/tasks/                   Fluxos orquestrados

src/config/settings.py                  Configuração de runtime (ASSETS_DIR, DEV_MODE, DOWNLOADS_BASE)
src/utils/                              Auxiliares (image_match, window_utils)
```

## Fluxo de dados (execução de tarefa)

```
1. Usuário clica em "Executar" na janela pywebview
2. POST /api/run/{task_name} → router.py
3. router chama TaskPool.start(task_name, params) → cria execução + Task assíncrona
4. TaskRunner.run() define status=RUNNING e chama o handler da tarefa
5. A tarefa abre o Chromium via Playwright e percorre os Page Objects
6. A cada passo: report_step() persiste o status e checa pausa/cancelamento/skip
7. Eventos (passo, log, screenshot) são transmitidos por WebSocket
8. Ao concluir: status=COMPLETED (ou FAILED/CANCELLED); o navegador é fechado no finally
```

## Auto-update (modo GUI)

```
GuiServer.start()
  → thread daemon: _check_and_prompt_update()
    → sleep 3s
    → loop a cada 60s:
        check_for_update(VERSION) [GitHub API + PAT]
          → versão maior encontrada?
            → create_confirmation_dialog() [dialog nativo pywebview]
              → confirmado: apply_update(release)
                → baixa TerminalServerRPA_Setup.exe da release
                → _verify_checksum() [opcional]
                → batch: aguarda processo fechar → /VERYSILENT installer → restart
              → recusado: last_rejected = version (não pergunta de novo pra mesma versão)
```

## System tray

```
Usuário fecha janela (botão X)
  → _on_closing(): _tray_started=True (guard), window.hide()
  → thread: _start_tray() → pystray.Icon com menu Abrir/Sair
    → Abrir: tray.stop() + window.show()
    → Sair: tray.stop() + window.destroy() + os._exit(0)
Ctrl+C no terminal:
  → SetConsoleCtrlHandler → os._exit(0)
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
  → GET http://127.0.0.1:{port}/_focus → Encerra
```

## Sistema de logs

```
Código da aplicação → structlog (síncrono)
                       ├── RotatingFileHandler → logs/TerminalServerRPA.jsonl
                       ├── StreamHandler → stderr (console de dev)
                       └── fila assíncrona → broadcast no WebSocket
```
