# Segurança

Este documento descreve o modelo de segurança do TerminalServerRPA, os controles em vigor e as ameaças explicitamente consideradas (incluindo riscos aceitos e hardening planejado).

## Modelo de ameaça

O TerminalServerRPA roda localmente em uma estação Windows e automatiza o ERP Senior através de uma sessão de Terminal Server. Como manipula **credenciais do ERP**, os principais ativos a proteger são:

1. Credenciais armazenadas (usuários/senhas do ERP).
2. A superfície de controle local (UI web + API REST + WebSocket) que pode disparar automação e ler dados de execução.

Fronteira de confiança assumida: um único usuário interativo confiável na estação. A aplicação **não** foi projetada para ser multiusuário nem exposta à rede.

| Ameaça | Mitigação |
|--------|-----------|
| Atacante de rede alcançando a API | O servidor vincula apenas a `127.0.0.1`; sem interface externa. |
| Processo local chamando a API sem autorização | Token Bearer por processo exigido em todo endpoint REST **e** no WebSocket. |
| Credenciais legíveis em disco | Credenciais são criptografadas com Fernet e armazenadas no Gerenciador de Credenciais do Windows (keyring), não em arquivos. |
| Duas instâncias concorrendo / sequestro de porta | Mutex nomeado do Windows garante instância única; a porta é registrada para foco da existente. |

## Controles

### Exposição de rede
O `uvicorn` é iniciado com `host="127.0.0.1"` (veja `src/interfaces/web/server.py`). A UI e a API são inacessíveis a partir de outras máquinas.

### Autenticação
- Um token de API por processo é gerado com `secrets.token_hex(32)` (`src/infrastructure/single_instance.py:get_or_create_token`).
- O token é injetado na página servida como tag `<meta name="api-token">`.
- REST: toda rota `/api/*` depende de `verify_token` (cabeçalho Bearer ou `?token=`).
- WebSocket `/ws`: o token é validado a partir do parâmetro `?token=` no handshake; tokens inválidos/ausentes são rejeitados com código de fechamento `1008` (violação de política) **antes** de a conexão ser aceita.

### Armazenamento de credenciais e token
- Uma chave Fernet fica no Gerenciador de Credenciais do Windows sob o serviço `TerminalServerRPA` (`src/infrastructure/vault.py`).
- Cada credencial é criptografada com essa chave e armazenada no keyring; um índice criptografado rastreia serviços/usuários. Nada é gravado em disco em texto puro.
- O **token de API** também fica no keyring (`single_instance.get_or_create_token`); o arquivo legado `token.txt` é removido na primeira execução.
- `set_password` valida a entrada (rejeita serviço/usuário vazios); `_decrypt` encadeia exceções (`raise ... from e`).

### Endpoint de desenvolvimento
- `/api/executions/{id}/snippet` executa Python arbitrário contra a página Playwright. A rota só é **registrada** quando `DEV_MODE` está ligado (via `dev_router`), além de um guard interno — em produção a rota não existe.

### Shutdown
- `/api/shutdown` dispara o shutdown gracioso do uvicorn (`Server.should_exit`), que roda o cleanup do lifespan (cancela tarefas ativas, fecha a conexão do banco). Não há mais `os._exit(0)`.

## Limitações conhecidas e hardening planejado

| Item | Status |
|------|--------|
| Validação de entrada nos endpoints ainda parcialmente manual (`dict.get()`). | Em migração para schemas Pydantic (Fase 2). |
| Singletons globais de infraestrutura dificultam o mock em testes. | Em migração para injeção de dependência (Fase 3). |

## Reporte

Esta é uma ferramenta interna. Reporte questões de segurança ao mantenedor (`SrMarinho/TerminalServerRPA`).
