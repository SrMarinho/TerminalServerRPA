# ADR-0003: Remover a camada `core` órfã

## Status

Aceito — 2026-06-01.

## Contexto

A pasta `src/core/` continha uma camada de domínio (`entities/user.py` e
`use_cases/register_users_use_case.py`) que **nenhuma** parte da aplicação usava.
Apenas os próprios testes da camada a referenciavam. Era um resquício de um exemplo
inicial (cadastro de usuários em massa) que foi substituído pela automação real de
geração de relatórios no ERP Senior.

Código não usado é pior do que código ausente: um revisor o lê como "arquitetura de
fachada", aumenta a superfície de manutenção e sugere acoplamento que não existe.

## Decisão

Remover `src/core/` e os testes correspondentes (`tests/unit/core/`). A abstração de
entidades/casos de uso será reintroduzida apenas quando houver uma segunda tarefa que
justifique compartilhar regra de domínio — seguindo YAGNI.

## Consequências

- Menos código morto; a estrutura passa a refletir o que realmente roda
  (`interfaces → infrastructure → automation`).
- Quando uma nova regra de negócio compartilhada surgir, a camada será recriada de
  forma orientada por uma necessidade concreta, não especulativa.
- Documentação de arquitetura atualizada para não mais listar a camada `core`.
