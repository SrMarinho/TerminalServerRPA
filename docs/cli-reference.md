# Referência da CLI

```
python main.py <comando> [opções]
# ou, no EXE instalado:
TerminalServerRPA.exe <comando> [opções]
```

Duplo clique no EXE (sem argumentos) executa `gui` automaticamente.

## Comandos

### `gui` (padrão)

Inicia a interface em janela nativa (pywebview + EdgeWebView2).

```
python main.py gui [--port PORTA] [--dev]
```

| Opção | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `--port` | int | 8080 | Porta para vincular (faz fallback para a próxima livre) |
| `--dev` | bool | False | Ativa modo desenvolvimento (DEV_MODE) |

Fechar a janela minimiza para o system tray. Use "Sair" no tray para encerrar completamente.

### `web`

Inicia o servidor FastAPI e abre no navegador padrão.

```
python main.py web [--port PORTA] [--no-browser] [--dev]
```

| Opção | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `--port` | int | 8080 | Porta para vincular |
| `--browser` / `--no-browser` | bool | True | Abrir o navegador automaticamente |
| `--dev` | bool | False | Ativa modo desenvolvimento |

### `vault`

Subcomandos de gerenciamento de credenciais.

```
python main.py vault <subcomando> [opções]
```

#### `vault set`

```
python main.py vault set <servico> -u <usuario>
```

Solicita a senha (entrada oculta).

#### `vault get`

```
python main.py vault get <servico> -u <usuario>
```

Encerra com código 1 se a credencial não for encontrada.

#### `vault delete`

```
python main.py vault delete <servico>
```

#### `vault list`

```
python main.py vault list
```

### `run`

Executa uma tarefa RPA.

```
python main.py run <nome_da_tarefa>
```

### `logs`

```
python main.py logs [--level NÍVEL] [--since DESDE] [--task TAREFA] [--json]
```

| Opção | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `--level` | str | `info` | Nível mínimo (`debug`, `info`, `warning`, `error`) |
| `--since` | str | `""` | Desde uma duração (ex.: `1h`, `30m`) |
| `--task` | str | `""` | Filtrar por nome da tarefa |
| `--json` | bool | False | Saída em JSON cru |

### `shutdown`

Encerra o servidor em execução.

```
python main.py shutdown
```
