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

### Armazenamento de credenciais
- Uma chave Fernet fica no Gerenciador de Credenciais do Windows sob o serviço `TerminalServerRPA` (`src/infrastructure/vault.py`).
- Cada credencial é criptografada com essa chave e armazenada no keyring; um índice criptografado rastreia serviços/usuários. Nada é gravado em disco em texto puro.

## Limitações conhecidas e hardening planejado

Itens rastreados no [roadmap](roadmap.md). Documentados aqui por honestidade e para delimitar expectativas.

| Item | Status |
|------|--------|
| **Token de API em texto puro** em `%LOCALAPPDATA%/TerminalServerRPA/token.txt` (legível pelo usuário local). | Planejado: mover para o keyring / restringir ACL. |
| **`/api/executions/{id}/snippet`** executa Python arbitrário (`exec`) contra a página Playwright ativa. | Protegido por `DEV_MODE` (desligado em builds de produção). Planejado: registrar a rota apenas quando `DEV_MODE` para eliminar a superfície de ataque. |
| **Shutdown via `os._exit(0)`** pula o cleanup (processos do browser/Playwright podem ficar órfãos). | Planejado: shutdown gracioso via o lifespan do app. |
| **`verify_token` lê `authorization` como parâmetro de query** em vez do cabeçalho HTTP no trabalho em andamento. | A corrigir: vincular como `Header(...)`. |

## Reporte

Esta é uma ferramenta interna. Reporte questões de segurança ao mantenedor (`SrMarinho/TerminalServerRPA`).
