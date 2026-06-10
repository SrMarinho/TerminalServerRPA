# Desenvolvimento

## Setup

```bash
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
|        | `uv run pytest tests/unit/infrastructure/test_vault.py -v` | Arquivo único |
|        | `uv run pytest -k "test_login"` | Filtrar por nome |
|        | `uv run pytest --cov=src` | Com cobertura |
| pyinstaller | `uv run pyinstaller main.spec --noconfirm` | Gerar bundle |

## Convenções do projeto

### Regras de camadas

```
interfaces → infrastructure → automation
tasks → pages
utils, config → módulos folha (importados por qualquer um)
infrastructure NUNCA importa de interfaces (desacoplado via events.py)
plugins/ importa SOMENTE de tsrpa (nunca src.*)
Sem imports circulares. Sem pular camadas.
```

Para criar plugins, veja [plugins.md](plugins.md).

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
│   ├── infrastructure/
│   ├── interfaces/
│   ├── automation/
│   └── config/
├── integration/             # Testes de integração (SQLite + event bus + keyring reais)
│   └── infrastructure/      # persistência, event bus, execução de tarefas, cofre
└── e2e/
    └── test_vault_flow.py
```

Os testes de integração exercitam o wiring real (sem mock): `ExecutionManager` +
`ExecutionRepository` + `BreakpointStore` + `migrations` contra um SQLite em
arquivo temporário, o event bus e o ciclo `TaskPool`/`TaskRunner`.

## Build

```bash
# Limpar build anterior e gerar bundle onedir
rm -rf dist/TerminalServerRPA dist/TerminalServerRPA.exe
uv run pyinstaller main.spec --noconfirm
```

Gera `dist/TerminalServerRPA/` com:
- `TerminalServerRPA.exe` — bootloader + bytecode
- `_internal/` — Python runtime, DLLs, extensões

O driver do Playwright **não** é incluído no bundle — é baixado automaticamente na primeira execução.

### Gerar installer (Inno Setup)

Requer [Inno Setup](https://jrsoftware.org/isinfo.php) instalado:

```bash
ISCC installer.iss
```

Gera `dist/TerminalServerRPA_Setup.exe`.

### Passos de release

1. Atualizar versão em `src/config/version.py` e `pyproject.toml`
2. Rodar testes: `uv run pytest`
3. Build: `uv run pyinstaller main.spec --noconfirm`
4. Testar: `dist\TerminalServerRPA\TerminalServerRPA.exe gui`
5. Build installer: `ISCC installer.iss`
6. Publicar release no GitHub com os assets:
   - `TerminalServerRPA_Setup.exe` — para instalação inicial
   - `TerminalServerRPA_Setup.exe.sha256` — checksum (opcional, valida integridade no auto-update)

## GitHub Token (repo privado)

O auto-update usa um PAT fine-grained com permissão `Contents: Read-only`.
Configurar em `src/infrastructure/updater.py`:

```python
GITHUB_TOKEN = "github_pat_..."
```

## CI

Workflow do GitHub Actions (`.github/workflows/ci.yml`):

- Passos: ruff check → pyright → pytest com cobertura
- Chromium do Playwright instalado para a suíte de testes
