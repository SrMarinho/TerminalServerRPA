# Changelog

Todas as mudanças notáveis deste projeto são documentadas aqui. O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), e o projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não lançado]

### Adicionado
- Testes para a tarefa de produção `GeracaoRelatorio` (schema, fases de passos e
  resolução de credenciais do cofre).

### Removido
- Camada `core` órfã (`entities`/`use_cases`) que nenhuma parte da aplicação usava
  (ver [ADR-0003](docs/decisions/ADR-0003-remove-orphan-core-layer.md)).

### Alterado
- O cofre (`Vault`) e o pool de tarefas deixam de ser singletons criados no import
  do router; passam a ser injetados via `Depends` (`get_vault`/`get_pool`), tornando
  os endpoints testáveis com `app.dependency_overrides`.
- `TaskRegistry.auto_discover` agora é idempotente (varre o filesystem uma vez por
  processo); a descoberta roda no startup do servidor em vez de a cada requisição.
- Validação de corpo de requisição via Pydantic (`CredentialIn`, `BreakpointIn`,
  `SnippetIn`); corpos inválidos retornam 422.
- Projeto renomeado de `senior-rpa` para **TerminalServerRPA** em todos os identificadores (diretório de dados, serviços do keyring, mutex do Windows, nomes de logger, arquivo de log, chaves de storage da UI, variável de ambiente, nome de distribuição). As referências ao produto ERP "Senior" permanecem inalteradas.

### Segurança
- O WebSocket `/ws` agora exige o token de API no handshake e rejeita conexões não autenticadas com código de fechamento `1008`. Antes, o WebSocket era aberto enquanto a API REST era protegida.
- `verify_token` passa a ler o cabeçalho `Authorization` de fato (via `Header(...)`); antes era tratado como parâmetro de query, quebrando a autenticação por Bearer em todas as rotas `/api/*`.
- O endpoint `/api/shutdown` faz shutdown gracioso (`uvicorn.Server.should_exit`) com cleanup de tarefas e do banco, no lugar de `os._exit(0)`.
- O endpoint `/snippet` (execução de código arbitrário) só é registrado quando `DEV_MODE` está ligado — a rota não existe em produção.
- O token de API é armazenado no keyring do SO em vez de um arquivo `token.txt` em texto puro (o arquivo legado é removido).
- `Vault.set_password` valida a entrada (rejeita serviço/usuário vazios).
- Adicionada a [documentação de segurança](docs/security.md) com o modelo de ameaça e as limitações conhecidas.

## [0.1.0]

### Adicionado
- Cofre de credenciais criptografado (Fernet + Gerenciador de Credenciais do Windows).
- Interface web FastAPI e CLI Typer sobre uma camada de infraestrutura compartilhada.
- Executor de tarefas com máquina de estados pausar/retomar/cancelar/pular e streaming de log ao vivo via WebSocket.
- Automação RPA baseada em Playwright para o ERP Senior (Page Object Model).
- Coordenação de instância única (mutex do Windows + arquivo de porta + foco da existente).
- Auto-atualização via GitHub Releases.
- Logging estruturado em JSON, fallback automático de porta.
- CI no GitHub Actions (Python 3.10–3.13), lint com `ruff`, checagem de tipos com `pyright`, `pytest` com cobertura, hooks de pre-commit.
