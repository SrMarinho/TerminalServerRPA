# ADR-0001: Autenticar o WebSocket com o token de API

## Status

Aceito — 2026-05-29.

## Contexto

A API REST (`/api/*`) era protegida por um token Bearer por processo via a dependência `verify_token`, mas o endpoint WebSocket `/ws` aceitava qualquer conexão. Qualquer processo local podia assinar o stream de eventos — logs de execução, atualizações de passos e screenshots — e podia enviar `{"type": "run"}` para disparar tarefas, sem autorização.

Handshakes de WebSocket não carregam um cabeçalho `Authorization` a partir de clientes de navegador, então a abordagem REST (Bearer no cabeçalho) não se transfere diretamente.

## Decisão

Validar o token de API existente a partir do parâmetro de query `?token=` durante o handshake do WebSocket, antes de aceitar a conexão. Com token ausente ou inválido, fechar com o código `1008` (violação de política) e não registrar a conexão. O cliente de navegador adiciona `?token=` (codificado em URL) à URL do WebSocket, reutilizando o mesmo token já injetado na página.

## Consequências

- O WebSocket passa a ter a mesma garantia de autorização da API REST; o stream de eventos e o disparo de tarefas deixam de estar abertos a chamadores locais não autenticados.
- O token aparece na URL do WebSocket. Aceitável porque o servidor é vinculado a `127.0.0.1` e o token é por processo e de curta duração; ele não é logado pela aplicação (logs de acesso do uvicorn estão desabilitados).
- A lógica de tratamento do token fica duplicada entre a dependência REST e o handler do WebSocket. Um refactor futuro pode extrair um validador compartilhado.
