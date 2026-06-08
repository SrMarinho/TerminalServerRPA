# Plano de Melhoria — Plugins & Memória

## Contexto

Revisão geral do código focada em (1) arquitetura de plugins e (2) uso de memória
do instalador e da execução. Objetivo: tornar o sistema de plugins desacoplado e
versionável, reduzir o tamanho do instalador e cortar o churn de CPU/memória
durante a execução das automações.

Arquivos revisados: `plugin_loader.py`, `task_registry.py`,
`plugins/relatorio_contas_receber/*`, `tsrpa/__init__.py`, `main.spec`,
`installer.iss`, `utils/image_match.py`, `infrastructure/task_runner.py`
(loop de screenshot), `automation/browser/browser_manager.py`,
`infrastructure/playwright_setup.py`, `pyproject.toml`.

---

## A. Plugins (arquitetura)

### A1 — Fronteira vazada (🔴)
`plugins/.../task.py:5-10` e os page objects do plugin importam direto de
`src.automation.pages.*`, `src.config.settings`, `src.utils.image_match`,
`src.utils.window_utils`. Plugin acoplado a internals → refactor em `src/` quebra plugin.

**Ação:** `tsrpa/__init__.py` passa a exportar TUDO que plugin usa. Hoje exporta
`register, SkipStep, BrowserManager, MatchThreshold, find_template, maximize_window, Vault`.
Adicionar: `find_text_position`, `find_text`, `ASSETS_DIR`, `DOWNLOADS_BASE`,
`HomePage`, `SeniorLoginPage`, `SidebarNavigator`, `TsApplicationsPage`, `TsLoginPage`.
Reescrever imports do plugin (`task.py`, `pages/*.py`, `pages/reports/*.py`) p/ usar só `tsrpa`.

### A2 — Sem manifesto/versionamento (🔴)
`plugin_loader.py` faz `import_module(entry.name)` sem versão nem compat-check.

**Ação:** `plugin.toml` por plugin (`name, version, min_app_version, entrypoint`).
Loader lê o toml, compara `min_app_version` com `src.config.version.VERSION`
(reusar `updater._parse_version`), recusa+loga incompatível antes de importar.

### A3 — Sem validação de contrato (🟡)
`register` confia que a classe tem `execute/get_schema/get_steps`.

**Ação:** validar no `TaskRegistry.register` (`task_registry.py:15`) que a classe
tem `execute` async; logar/recusar se faltar.

### A4 — Isolamento de falha + colisão de nome (🟡)
Import já tem try/except. Falta namespacing por plugin (colisão de nome de task).

**Ação:** prefixar task name com nome do plugin no registro vindo do loader.
Manter captura de exceção do `execute` (já existe no TaskRunner → FAILED).

### A5 — `__pycache__` no bundle (🟡)
`main.spec` bundle `("plugins","plugins")` inteiro → leva `.pyc` (3.11+3.14) +
órfão `rot_conciliacao_703.cpython-314.pyc`.

**Ação:** filtrar `__pycache__/*.pyc/*.pyo` do `a.datas` no `main.spec` (FEITO).
gitignore já cobre `__pycache__/` e `*.py[cod]`.

### A6 — Duplicação no task.py (🟢)
Branches "no remote_page" (`task.py:209-220, 286-291`) replicam listas de steps.

**Ação:** helper `_replay_steps(names)`.

---

## B. Memória — Instalador

### B1 — `pyautogui` é dep morta (🔴, FEITO)
Não importado em nenhum `.py` (só `uv.lock`). Arrasta pyscreeze/pygetwindow/
pymsgbox/pytweening/mouseinfo. Removido de `pyproject.toml`.

### B2 — `opencv-python` → `opencv-python-headless` (🔴, FEITO)
Full opencv traz Qt/HighGUI; `main.spec` stripava Qt na mão. Headless já vem sem.
Trocado dep + removido strip manual.

### B3 — Screenshots stray no bundle (🟢)
`assets/Senior/components/startup_interface/Captura de tela *.png` (2 arquivos,
~debug) não referenciados. Remover via `git rm`.

### B4 — Bundle exclui pyc/test (🟢, FEITO no main.spec)
Filtro `_JUNK` em `a.datas`.

> Chromium NÃO está no instalador (download runtime — `playwright_setup`). Manter.
> Compressão lzma+solid+UPX já ok.

---

## C. Memória — Execução (runtime)

### C1 — `find_template` re-decodifica template a cada poll (🔴)
`image_match.py:88` faz `np.fromfile + imdecode` do PNG needle TODA chamada.
Loops `_wait_loading`/`_wait_for_home` pollam 0.3-3s → re-decode constante.

**Ação:** cache LRU por `(path, mtime)` dos templates decodificados em `image_match.py`.

### C2 — Screenshot full-res decodificado a cada poll (🟡)
Loops fazem `page.screenshot()` (PNG tela cheia) + `imdecode` a cada 0.3s.

**Ação (conservadora):** não mexer em timing das automações (risco de quebrar
reconhecimento). Avaliar só `cv2.setNumThreads` (C4). Deixar C2 como observação.

### C3 — Cache de screenshot não liberado no fim (🟡)
`task_runner.py:184` `_screenshot_last`/`_screenshot_last_hash` por exec_id limpos
só no unsubscribe.

**Ação:** limpar ambos quando a execução termina (no fim de `TaskPool._run` e/ou
em `_prune_finished`).

### C4 — `cv2.setNumThreads` (🟢)
opencv abre threads por padrão; matchTemplate pequeno desperdiça.

**Ação:** `cv2.setNumThreads(1)` no import de `image_match.py`.

---

## Ordem de execução
1. **Grupo 1 — instalador/limpeza:** B1, B2, B4 (feitos), B3, A5 → commit.
2. **Grupo 2 — runtime mem:** C1 (cache template), C3, C4 → commit.
3. **Grupo 3 — plugins:** A1 (facade), A2 (manifesto), A3, A4, A6 → commit.

## Verificação
- `uv lock` ok; `uv run ruff check` + `uv run pyright src` limpos.
- `uv run pytest tests/ -q` verde (157+).
- Import sanity: `uv run python -c "import tsrpa; ..."` exporta tudo.
- Plugin carrega: `uv run python -c "from src.infrastructure.task_registry import TaskRegistry; TaskRegistry.auto_discover(); print('Relatório Contas Receber' in TaskRegistry.list())"`.
- Build local opcional: `uv run pyinstaller main.spec --noconfirm` + checar tamanho dist/.
- Release de teste (bump + tag) p/ validar instalador menor + plugin funcionando.
