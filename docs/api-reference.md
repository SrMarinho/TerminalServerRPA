# Referência da API

Todos os endpoints são servidos pelo servidor FastAPI local em `http://127.0.0.1:{porta}`.

## Autenticação

Um token de API por processo é gerado na inicialização e injetado na página servida como `<meta name="api-token">`.

- **REST:** toda rota `/api/*` exige o token, via cabeçalho `Authorization: Bearer <token>` ou parâmetro de query `?token=<token>`. Sem token válido → `401`.
- **WebSocket:** o token é validado no handshake a partir do parâmetro `?token=<token>`. Token inválido/ausente → conexão fechada com código `1008` antes de ser aceita.

## Credenciais

### Listar todos os serviços

```
GET /api/credentials
```

Retorna um array de serviços com seus usuários:

```json
[
  {"service": "erp-system", "usernames": ["admin", "backup"]}
]
```

### Salvar uma credencial

```
POST /api/credentials
Content-Type: application/json

{"service": "erp-system", "username": "admin", "password": "secret123"}
```

Retorna `{"status": "ok"}` em caso de sucesso. Retorna `400` se faltar `service`, `username` ou `password`.

### Obter uma credencial

```
GET /api/credentials/{service}?username={username}
```

Retorna `{"service": ..., "username": ..., "password": ...}`. Retorna `404` se não encontrada; `400` se faltar o parâmetro `username`.

### Excluir uma credencial

```
DELETE /api/credentials/{service}
```

Exclui todas as credenciais do serviço informado. Retorna `{"status": "deleted"}`.

## Tarefas

### Listar tarefas disponíveis

```
GET /api/tasks
```

Retorna a lista de tarefas registradas (descobertas automaticamente).

### Schema e configuração de uma tarefa

```
GET  /api/tasks/{task_name}/schema      # campos do formulário da tarefa
GET  /api/tasks/{task_name}/config      # parâmetros salvos
POST /api/tasks/{task_name}/config      # salva parâmetros
GET  /api/tasks/{task_name}/form        # schema + valores resolvidos para render
POST /api/tasks/{task_name}/visibility  # avalia condições when/visibility dos campos
```

### Recarregar plugins

```
POST /api/plugins/reload
```

Recarrega os plugins de `plugins/` sem reiniciar o servidor (purga `sys.modules` +
re-registra as tarefas). Retorna a lista de plugins recarregados.

### Resolvers de fórmula

```
GET  /api/resolvers                     # metadados dos resolvers (date.today, concat, …)
POST /api/resolvers/preview             # avalia uma fórmula e retorna o valor resolvido
```

### Executar uma tarefa

```
POST /api/run/{task_name}
Content-Type: application/json

{ ...parâmetros opcionais... }
```

Inicia a tarefa de forma assíncrona e retorna o `execution_id` criado.

### Tarefas em execução

```
GET    /api/tasks/running               # lista execuções ativas
DELETE /api/tasks/running               # remove da memória as execuções finalizadas
```

### Controle de execução

```
POST /api/tasks/{task_id}/pause         # pausa a tarefa
POST /api/tasks/{task_id}/resume        # retoma a tarefa
POST /api/tasks/{task_id}/skip          # pula o passo atual
POST /api/tasks/{task_id}/cancel        # cancela a tarefa
POST /api/executions/{exec_id}/breakpoint   # define um breakpoint em um passo
```

## Execuções

```
GET /api/executions                     # histórico de execuções
GET /api/executions/{execution_id}      # detalhe de uma execução (passos, logs)
```

## Sistema

### Modo de desenvolvimento

```
GET /api/dev
```

Retorna `{"dev": true|false}`. Habilita recursos de desenvolvimento na UI.

### Health check

```
GET /_health
```

Retorna `{"status": "ok"}`. Não requer token.

### Aplicar atualização

```
POST /api/update
```

Dispara a verificação/aplicação de atualização sob demanda.

### Encerrar o servidor

```
POST /api/shutdown
```

Encerra o processo do servidor (graceful, com cleanup de tarefas e banco).

### Focar instância existente

```
GET /_focus
```

Traz a aba do navegador da instância existente para frente. Usado pelo protocolo de mutex de instância única.

### Interface web

```
GET /
```

Serve a UI web (`index.html`) com o token de API injetado.

### Rotas dev-only

Registradas apenas quando `DEV_MODE` está ligado — não existem em produção.

```
POST   /api/dev/snippet                      # executa snippet sem execução ativa (page=None)
DELETE /api/dev/snippet                       # cancela o snippet standalone
POST   /api/executions/{exec_id}/snippet      # executa snippet contra a página Playwright ativa
DELETE /api/executions/{exec_id}/snippet      # cancela o snippet da execução
POST   /api/executions/{exec_id}/ocr          # roda OCR contra a página ativa (debug)
```

> **Aviso:** snippets executam código Python arbitrário no processo. Disponível
> só em `DEV_MODE`. Veja [security.md](security.md).

## WebSocket

```
ws://127.0.0.1:{porta}/ws?token=<token>
```

### Eventos Servidor → Cliente

Todos os eventos são JSON com um campo `type`:

| Type | Descrição |
|------|-----------|
| `pool:update` | Mudança no conjunto de tarefas em execução |
| `execution:step` | Mudança de status de um passo (running→completed, etc.) |
| `execution:status` | Mudança de status da execução (paused/running/completed/failed/cancelled) |
| `execution:log` | Nova linha de log de uma execução |
| `execution:screenshot` | Novo screenshot de uma execução |

### Comandos Cliente → Servidor

| Type | Payload | Ação |
|------|---------|------|
| `run` | `{task_name}` | Inicia uma tarefa |
| `screenshot:subscribe` | `{execution_id}` | Assina o stream de screenshots de uma execução |
