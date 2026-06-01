# Desenvolvimento

## Setup

```bash
# Clonar e instalar
git clone <repo-url>
cd TerminalServerRPA
uv sync

# Instalar o navegador do Playwright para tarefas RPA
uv run playwright install chromium
```

## Ferramental

| Ferramenta | Comando | Descrição |
|------------|---------|-----------|
| uv | `uv add <pkg>` | Adicionar dependência de produção |
|    | `uv add --dev <pkg>` | Adicionar dependência de dev |
|    | `uv sync` | Instalar todas as dependências |
|    | `uv run <cmd>` | Rodar comando no venv |
| ruff | `uv run ruff check` | Lint |
|      | `uv run ruff check --fix` | Auto-correção |
|      | `uv run ruff format` | Formatar código |
| pyright | `uv run pyright src` | Checagem de tipos |
| pytest | `uv run pytest` | Rodar todos os testes |
|        | `uv run pytest tests/unit/infrastructure/test_vault.py -v` | Arquivo de teste único |
|        | `uv run pytest -k "test_login"` | Filtrar por nome |
|        | `uv run pytest --cov=src` | Com cobertura |
| pyinstaller | `uv run pyinstaller main.spec` | Gerar .exe |

## Convenções do projeto

### Regras de camadas

```
interfaces → infrastructure → automation
use_cases → entities
tasks → pages
utils, config → módulos folha (importados por qualquer um)
Sem imports circulares. Sem pular camadas.
```

### Estilo de código

- Alvo Python 3.14 (`.python-version`)
- Ruff com as regras selecionadas: E, F, I, W, N, UP, B, SIM
- Aspas duplas para strings
- Comprimento de linha: 120
- Anotações de tipo em todas as funções públicas
- Usar `X | None` em vez de `Optional[X]` (UP045)

### Nomenclatura

```
Arquivos: snake_case.py
Classes: PascalCase
Funções: snake_case
Constantes: UPPER_SNAKE
Privados: _prefixo_underscore
```

### Estrutura de testes

```
tests/
├── unit/                    # Testes unitários (dependências mockadas)
│   ├── infrastructure/      # vault, task_runner, logger, updater, ...
│   ├── interfaces/          # web (router, server, websocket), cli
│   └── automation/          # pages, tasks
├── integration/             # Testes de integração (keyring real)
│   └── infrastructure/
└── e2e/                     # Ponta a ponta (CLI + cofre)
    └── test_vault_flow.py
```

- Mockar dependências externas (keyring, playwright, rede)
- Usar `@pytest.mark.asyncio` para testes assíncronos (`asyncio_mode = "auto"` já configurado)
- Priorizar cobertura dos caminhos de produção e de segurança

## Testando tarefas baseadas em Playwright

As tarefas em `src/automation/tasks/` abrem um Chromium real. Em testes:

- **Testes unitários:** mockar `Page` com `AsyncMock` (veja `tests/unit/automation/test_pages.py`)
- Mockar os Page Objects para validar a sequência de passos sem subir o navegador

## Build

```bash
# Executável principal
uv run pyinstaller main.spec

# Executável do atualizador (pequeno, standalone)
uv run pyinstaller updater.spec
```

Os arquivos `.spec` são versionados no git. O padrão `*.spec` está no `.gitignore`, então force a adição com `git add -f main.spec` ao modificá-los.

### Passos de release

1. Atualizar a versão em `pyproject.toml`
2. Rodar os testes: `uv run pytest`
3. Build: `uv run pyinstaller main.spec`
4. Testar o `.exe`: `dist/TerminalServerRPA.exe web`

## CI

Workflow do GitHub Actions (`.github/workflows/ci.yml`):

- Matriz: Python 3.10–3.13
- Passos: ruff check → pyright → pytest com cobertura
- Chromium do Playwright instalado para a suíte de testes
