# TerminalServerRPA

[![CI](https://github.com/SrMarinho/TerminalServerRPA/actions/workflows/ci.yml/badge.svg)](https://github.com/SrMarinho/TerminalServerRPA/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Lint: ruff](https://img.shields.io/badge/lint-ruff-orange.svg)](https://github.com/astral-sh/ruff)

Aplicação RPA que automatiza o ERP Senior (via Terminal Server) — interface web local, cofre de credenciais criptografado, executor de tarefas com progresso ao vivo e auto-atualização. Nativa de Windows, processo único, servida via FastAPI.

## Funcionalidades

- **Cofre de senhas** — credenciais criptografadas com Fernet, armazenadas no Gerenciador de Credenciais do Windows (keyring)
- **Interface web** — frontend Tailwind CSS servido pelo FastAPI (somente localhost)
- **CLI** — interface de linha de comando (Typer) para gerenciar o cofre e executar tarefas
- **Executor de tarefas** — máquina de estados com pausar/retomar/cancelar/pular e streaming de log ao vivo via WebSocket
- **Instância única** — mutex do Windows impede processos duplicados; foca a instância existente ao reabrir
- **Auto-atualização** — verifica e baixa releases do GitHub
- **Fallback de porta** — seleciona automaticamente a próxima porta livre se a 8080 estiver ocupada

## Início rápido

```bash
# Instalar dependências
uv sync

# Rodar a interface web
uv run python main.py web

# Gerenciar credenciais (CLI)
uv run python main.py vault set meu-servico -u meu-usuario
uv run python main.py vault get meu-servico
uv run python main.py vault list

# Ver logs
uv run python main.py logs --level error

# Executar uma tarefa RPA
uv run python main.py run "Relatório Contas Receber"
```

## Desenvolvimento

```bash
# Testes
uv run pytest

# Lint
uv run ruff check

# Checagem de tipos
uv run pyright src

# Formatação
uv run ruff format

# Gerar executável
uv run pyinstaller main.spec
```

## Arquitetura

Camadas de Clean Architecture dentro de um único processo. A interface web e a CLI são adaptadores sobre a mesma camada de infraestrutura e o mesmo motor de automação.

```
main.py                      Entrypoint Typer (web | vault | run | logs | shutdown)
src/
  interfaces/
    web/                     Router FastAPI, WebSocket, servidor, UI estática (JS)
    cli/                     Subcomandos Typer
  infrastructure/            vault, task_runner, execution_manager, logger,
                             single_instance, updater, task_registry
  automation/
    pages/                   Page Objects do Playwright (telas do ERP Senior)
    tasks/                   Tarefas RPA (ex.: geração de relatório)
  config/                    Configuração de runtime
  utils/                     Auxiliares compartilhados (image matching, window utils)
```

Veja [docs/architecture.md](docs/architecture.md) para o mapa completo de módulos e fluxo de dados.

## Segurança

- Interface web local vinculada apenas a `127.0.0.1`; nunca exposta à rede.
- Todos os endpoints REST **e** o WebSocket exigem um token Bearer por processo (gerado automaticamente e injetado na página).
- Credenciais são armazenadas criptografadas (Fernet) no Gerenciador de Credenciais do Windows (keyring) — nunca em texto puro no disco.

Modelo de ameaça completo e riscos aceitos: [docs/security.md](docs/security.md).

## Documentação

| Público | Comece por |
|---------|-----------|
| Usuários | [Instalação](docs/installation.md) · [Guia do usuário](docs/user-guide.md) · [Referência da CLI](docs/cli-reference.md) |
| Desenvolvedores | [Arquitetura](docs/architecture.md) · [Desenvolvimento](docs/development.md) · [Referência da API](docs/api-reference.md) · [Segurança](docs/security.md) |
| Decisões | [ADRs](docs/decisions/) · [Roadmap](docs/roadmap.md) · [Changelog](CHANGELOG.md) |

## Status do projeto

Implementado: cofre criptografado, CLI, interface web, executor de tarefas (pausar/retomar/cancelar/pular), coordenação de instância única, auto-atualização, logging estruturado, fallback de porta, CI (GitHub Actions, Python 3.10–3.13), checagem de tipos (pyright), lint (ruff), automação RPA com Playwright.

Em andamento: hardening de segurança (auth do WebSocket concluída, shutdown gracioso), validação de requisições com Pydantic, injeção de dependências no lugar de singletons globais, cobertura de testes para a tarefa de relatório em produção. Veja o [Roadmap](docs/roadmap.md).
