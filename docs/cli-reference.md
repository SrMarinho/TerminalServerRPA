# Referência da CLI

O entrypoint da aplicação é um único comando Typer:

```
python main.py <comando> [opções]
```

## Opções globais

Nenhuma. Cada subcomando tem suas próprias opções.

## Comandos

### `web`

Inicia o servidor da interface web.

```
python main.py web [--port PORTA] [--no-browser]
```

| Opção | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `--port` | int | 8080 | Porta para vincular (faz fallback para a próxima livre) |
| `--browser` / `--no-browser` | bool | True | Abrir o navegador automaticamente ao iniciar |

### `vault`

Subcomandos de gerenciamento de credenciais.

```
python main.py vault <subcomando> [opções]
```

#### `vault set`

Salva ou atualiza uma credencial.

```
python main.py vault set <servico> -u <usuario>
```

Solicita a senha (entrada oculta).

#### `vault get`

Recupera uma credencial.

```
python main.py vault get <servico> -u <usuario>
```

Encerra com código 1 se a credencial não for encontrada.

#### `vault delete`

Exclui todas as credenciais de um serviço.

```
python main.py vault delete <servico>
```

#### `vault list`

Lista todos os serviços armazenados e seus usuários.

```
python main.py vault list
```

### `run`

Executa uma tarefa RPA.

```
python main.py run <nome_da_tarefa>
```

| Argumento | Descrição |
|-----------|-----------|
| `nome_da_tarefa` | Nome da tarefa registrada (ex.: `Relatório Contas Receber`) |

### `logs`

Visualiza os logs da aplicação.

```
python main.py logs [--level NÍVEL] [--since DESDE] [--task TAREFA] [--json]
```

| Opção | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `--level` | str | `info` | Nível mínimo de log (`debug`, `info`, `warning`, `error`) |
| `--since` | str | `""` | Mostrar logs desde uma duração (ex.: `1h`, `30m`) |
| `--task` | str | `""` | Filtrar por nome da tarefa |
| `--json` | bool | False | Saída em linhas JSON cruas em vez de formatada |

### `shutdown`

Encerra o servidor em execução (envia POST para `/api/shutdown` na instância ativa).

```
python main.py shutdown
```
