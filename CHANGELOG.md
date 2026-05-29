# Changelog

Todas as mudanças notáveis deste projeto são documentadas aqui. O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), e o projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não lançado]

### Alterado
- Projeto renomeado de `senior-rpa` para **TerminalServerRPA** em todos os identificadores (diretório de dados, serviços do keyring, mutex do Windows, nomes de logger, arquivo de log, chaves de storage da UI, variável de ambiente, nome de distribuição). As referências ao produto ERP "Senior" permanecem inalteradas.

### Segurança
- O WebSocket `/ws` agora exige o token de API no handshake e rejeita conexões não autenticadas com código de fechamento `1008`. Antes, o WebSocket era aberto enquanto a API REST era protegida.
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
