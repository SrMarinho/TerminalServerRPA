# ADR-0002: Renomear o projeto para TerminalServerRPA

## Status

Aceito — 2026-05-29.

## Contexto

O projeto se chamava originalmente `senior-rpa`. O nome era ambíguo (parecia pertencer à "Senior", a fornecedora do ERP) e não correspondia ao repositório no GitHub, `SrMarinho/TerminalServerRPA`. A automação, na verdade, atua sobre o ERP Senior através de uma sessão de **Terminal Server**, o que o novo nome reflete.

## Decisão

Renomear o projeto para **TerminalServerRPA** em todos os lugares que identificam a aplicação: diretório de dados, nomes de serviço do keyring, mutex do Windows, prefixos de logger, nome do arquivo de log, chaves de storage da UI, variável de ambiente `DEV_MODE` e nome do executável. O nome de distribuição Python usa a forma normalizada em minúsculas `terminalserverrpa`.

Referências ao **produto ERP Senior** (`assets/Senior/`, `senior_login_page.py`, rótulos de tela do ERP) **não** são renomeadas — elas nomeiam o sistema de terceiros que está sendo automatizado, não este projeto.

## Consequências

- A identidade fica consistente entre código, repositório e artefatos de runtime.
- O estado de runtime criado sob o nome antigo fica órfão: credenciais e a chave Fernet no keyring sob o serviço `senior-rpa`, e `%LOCALAPPDATA%/senior-rpa` (token, porta). Usuários existentes precisam reinserir as credenciais após a atualização. Aceito como custo único.
- Nenhum caminho de migração de dados é fornecido; o nome anterior é totalmente aposentado.
