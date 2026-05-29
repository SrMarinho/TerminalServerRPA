# Roadmap do TerminalServerRPA

Marcos concluídos e trabalho em andamento. As decisões arquiteturais são registradas em [decisions/](decisions/).

## Concluído ✅

### Logs estruturados
- `src/infrastructure/logger.py` — configuração do structlog
- Saída em arquivo JSON + console
- Ponte para WebSocket (feed ao vivo)

### Task Runner (máquina de estados)
- `src/infrastructure/task_runner.py`
- Estados: `IDLE → RUNNING ↔ PAUSED → COMPLETED | FAILED | CANCELLED`
- Sistema de passos: pontos de checagem para pausa/cancelamento/skip
- `TaskPool` para execuções concorrentes; `execution_manager.py` persiste em SQLite

### Cofre de senhas
- `src/infrastructure/vault.py` — keyring + cryptography (Fernet)
- `src/interfaces/cli/cli.py` — comandos Typer: set / get / delete / list
- `src/interfaces/web/router.py` — endpoints REST FastAPI
- `src/interfaces/web/server.py` — runner FastAPI + uvicorn

### Instância única
- `src/infrastructure/single_instance.py`
- Mutex do Windows + foco via socket + token de API

### Auto-atualização (GitHub Releases)
- `src/infrastructure/updater.py`
- Verifica a última release na inicialização; baixa e aplica via `updater.exe`

### Interface web & visão ao vivo
- `src/interfaces/web/` — UI single-page (Tailwind CSS)
- WebSocket para logs + status em tempo real
- Controles de pausar / retomar / cancelar / pular

### Tarefas RPA (Playwright)
- `src/automation/pages/` — Page Objects do ERP Senior (Terminal Server)
- `src/automation/tasks/report_generation.py` — tarefa "Relatório Contas Receber"

## Em andamento 🚧

Veja o roadmap de segurança + manutenibilidade (foco SOLID/modular):

1. **Segurança** — auth do WebSocket (✅), shutdown gracioso (substituir `os._exit`), restringir o endpoint `/snippet`, mover o token de API para o keyring, hardening do cofre.
2. **Validação com Pydantic** — schemas nos endpoints no lugar de `dict.get()`.
3. **SOLID / modularidade** — injeção de dependências (eliminar singletons globais), `auto_discover` uma única vez, framework de passos, decisão sobre a camada `core` órfã.
4. **Testes** — cobertura para `report_generation` e Page Objects de produção; job de CI no Windows.
5. **Manutenibilidade visível** — ADRs, CHANGELOG, badges.

## Futuro 💡

- Migração do frontend (JS vanilla → Svelte), se a complexidade justificar.
- Workflow de release no GitHub Actions (build do `.exe` + publicação).
