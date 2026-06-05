# TerminalServerRPA

[![CI](https://github.com/SrMarinho/TerminalServerRPA/actions/workflows/ci.yml/badge.svg)](https://github.com/SrMarinho/TerminalServerRPA/actions/workflows/ci.yml)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Playwright](https://img.shields.io/badge/Playwright-45ba4b?logo=playwright&logoColor=white)](https://playwright.dev/)
[![Ruff](https://img.shields.io/badge/lint-ruff-orange)](https://github.com/astral-sh/ruff)
[![Pyright](https://img.shields.io/badge/types-pyright-yellow)](https://github.com/microsoft/pyright)
[![PyInstaller](https://img.shields.io/badge/build-PyInstaller-5C3D2E)](https://pyinstaller.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Automação RPA para ERPs legados rodando dentro de Terminal Server.**

Automatiza ERPs legados que rodam dentro de sessões de Terminal Server —
sem API, sem DOM acessível, sem integração moderna. A interface é renderizada
como bitmap, então a navegação é feita por visão computacional:

- **Playwright** + **OCR** (Tesseract) + **template matching** (OpenCV)
  para navegar por interfaces legadas renderizadas como bitmap
- **Janela nativa** via pywebview (EdgeWebView2) — sem dependência de navegador externo
- **FastAPI** local com **WebSocket** para execução e log ao vivo
- **Cofre criptografado** (Windows Keyring + criptografia simétrica Fernet)
- **Auto-atualização** via GitHub Releases com dialog de confirmação

> [!NOTE]
> Aplicação Windows nativa. O servidor escuta apenas em `127.0.0.1` —
> nunca exposto à rede.

## Funcionalidades

- **Janela nativa** — pywebview com EdgeWebView2, system tray ao fechar
- **Cofre de senhas** — credenciais criptografadas no Gerenciador de Credenciais do Windows
- **Interface web** — Tailwind SPA servida pelo FastAPI (localhost)
- **WebSocket ao vivo** — logs, screenshots, status da execução em tempo real
- **Executor de tarefas** — máquina de estados com pausar/retomar/cancelar/pular
- **CLI** — gerenciar cofre, executar tarefas, ver logs
- **Instância única** — mutex do Windows + foco na janela existente
- **Auto-atualização** — verifica GitHub Releases a cada 60s, aplica via installer silencioso
- **Fallback de porta** — encontra próxima porta livre se 8080 estiver ocupada

## Início rápido

```bash
# Instalar dependências
uv sync
uv run playwright install chromium

# Interface GUI (padrão)
uv run python main.py gui

# Interface web pura
uv run python main.py web

# Gerenciar credenciais
uv run python main.py vault set meu-servico -u meu-usuario
uv run python main.py vault list

# Executar uma tarefa RPA
uv run python main.py run "Relatório Contas Receber"
```

## Desenvolvimento

```bash
uv run pytest              # Testes
uv run ruff check          # Lint
uv run pyright src         # Checagem de tipos
uv run ruff format         # Formatação

# Build (onedir)
uv run pyinstaller main.spec --noconfirm

# Installer (requer Inno Setup)
ISCC installer.iss
```

## Arquitetura

Camadas dentro de um único processo Windows:

```
main.py                      Entrypoint Typer (padrão: gui)
src/
  interfaces/gui/            Janela pywebview + tray + auto-update
  interfaces/web/            FastAPI, WebSocket, UI estática
  interfaces/cli/            CLI Typer
  infrastructure/            Vault, TaskRunner, SQLite, Logger, Updater, PlaywrightSetup
  automation/pages/          Page Objects (Playwright + OCR)
  automation/tasks/          Tarefas RPA
  config/                    Configuração + versão
  utils/                     image_match, window_utils
```

## Segurança

- Servidor vinculado a `127.0.0.1` — sem exposição à rede
- Token Bearer (automático) em todas as rotas REST + WebSocket
- Credenciais cifradas via Fernet + Windows Keyring — **nunca em plaintext na API ou CLI**
- Pipeline CI executa lint + typecheck + testes a cada push

## Stack

| Categoria | Tecnologias |
|-----------|-------------|
| **Runtime** | Python 3.14, uv |
| **GUI** | pywebview (EdgeWebView2), pystray |
| **Web** | FastAPI, Uvicorn, WebSocket, Tailwind CSS |
| **RPA** | Playwright, OpenCV (template matching), Tesseract (OCR) |
| **Infra** | structlog, cryptography (Fernet), keyring (Windows), SQLite |
| **Build** | PyInstaller (onedir), Inno Setup, GitHub Actions |
| **Qualidade** | pytest, ruff, pyright |

## Documentação

| Público | Links |
|---------|-------|
| Usuários | [Instalação](docs/installation.md) · [Guia do usuário](docs/user-guide.md) · [CLI](docs/cli-reference.md) |
| Devs | [Arquitetura](docs/architecture.md) · [Desenvolvimento](docs/development.md) · [API](docs/api-reference.md) · [Segurança](docs/security.md) |
| Decisões | [ADRs](docs/decisions/) · [Roadmap](docs/roadmap.md) · [CHANGELOG](CHANGELOG.md) |

## Licença

MIT. Veja [LICENSE](LICENSE).
