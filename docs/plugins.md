# Plugins

Plugins adicionam tarefas RPA sem alterar o core. Cada plugin é um pacote Python
autocontido em `plugins/<nome>/` (ou em `%LOCALAPPDATA%/TerminalServerRPA/plugins`
no build empacotado), com seus próprios Page Objects e tarefas.

## Regra de fronteira

> Código de plugin importa **somente** de `tsrpa` — nunca de `src.*`.

`tsrpa` é o SDK estável: a única superfície que o host garante. Importar de `src.*`
quebra o isolamento e pode parar de funcionar entre versões.

## Estrutura mínima

```
plugins/meu_plugin/
├── plugin.toml          # manifesto (opcional, mas recomendado)
├── __init__.py          # importa a(s) task(s) para registrá-las
├── task.py              # a tarefa (herda tsrpa.TaskBase)
└── pages/               # Page Objects próprios (opcional)
```

### `plugin.toml`

```toml
[plugin]
name = "meu_plugin"          # namespace das tarefas → "meu_plugin:<task>"
version = "0.1.0"
min_app_version = "0.1.0"    # plugin é ignorado se a versão do app for menor
entrypoint = "meu_plugin"
```

Sem manifesto, o nome do diretório vira o namespace.

### `__init__.py`

```python
from .task import MinhaTask

__all__ = ["MinhaTask"]
```

### `task.py`

```python
from tsrpa import TaskBase, register


@register("Meu Relatório")
class MinhaTask(TaskBase):
    @staticmethod
    def get_schema() -> list:
        # campos do formulário na UI (type, validação, refs de credencial)
        return [{"name": "data", "type": "date", "label": "Data"}]

    @staticmethod
    def get_steps() -> dict:
        # fases → passos, exibidos como progresso na UI
        return {"Login": ["Login TS"], "Processamento": ["Gerar"]}

    async def execute(self, params: dict) -> dict:
        await self._runner.report_step("Login TS")
        # ... navega pelos Page Objects ...
        return {"ok": True}
```

`TaskBase.__init__` recebe `runner` (o `TaskRunner`) e `vault` (o cofre). O host
instancia como `task_cls(runner=..., vault=...)`.

## SDK `tsrpa`

| Exporta | Uso |
|---------|-----|
| `register` | Decorator que registra a tarefa (`@register("Nome")`) |
| `TaskBase` | Classe base do contrato (`execute`/`get_schema`/`get_steps`) |
| `SkipStep` | Exceção para pular um passo |
| `BrowserManager` | Controle do Chromium via Playwright |
| `find_template`, `find_text`, `find_text_position`, `MatchThreshold` | Template matching + OCR |
| `maximize_window` | Maximiza a janela ativa |
| `get_logger` | Logger structlog (já correlaciona `execution_id`) |
| `Vault` | Cofre de credenciais |
| `ASSETS_DIR`, `DOWNLOADS_BASE` | Caminhos base |
| `HomePage`, `SeniorLoginPage`, `SidebarNavigator`, `TsApplicationsPage`, `TsLoginPage` | Page Objects reutilizáveis do ERP Senior |

## Ciclo de vida

- **Descoberta**: no startup, `plugin_loader` varre os diretórios de plugins,
  valida `min_app_version`, importa o pacote e dá namespace às tarefas
  (`<plugin>:<task>`) para evitar colisões.
- **Hot reload**: `POST /api/plugins/reload` (ou o botão "↺ plugins" no DEV_MODE)
  purga os módulos do plugin de `sys.modules` e re-registra as tarefas — sem
  reiniciar o servidor.

## Referência

Veja `plugins/relatorio_contas_receber/` como implementação de referência.
