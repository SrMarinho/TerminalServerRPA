# Instalação

## A partir do código-fonte

### Pré-requisitos

- Python 3.10+ (desenvolvido em 3.14)
- Gerenciador de pacotes [uv](https://docs.astral.sh/uv/)

### Passos

```bash
# Clonar o repositório
git clone <repo-url>
cd TerminalServerRPA

# Criar o ambiente virtual e instalar dependências
uv sync

# Instalar o navegador do Playwright (necessário para tarefas RPA)
uv run playwright install chromium

# Rodar a aplicação
uv run python main.py web
```

## .exe portátil

Baixe o `TerminalServerRPA.exe` mais recente em [GitHub Releases](https://github.com/SrMarinho/TerminalServerRPA/releases). Não requer instalação — dê duplo clique para executar.

O executável é autocontido (empacota Python + dependências + Chromium via Playwright).

### Primeira execução

1. Inicie o `TerminalServerRPA.exe`
2. Seu navegador padrão abre em `http://127.0.0.1:8080`
3. Se a porta 8080 estiver ocupada, a aplicação seleciona automaticamente a próxima porta livre
4. Se a aplicação já estiver rodando, a instância existente recebe foco

### Atualização

Na inicialização, a aplicação verifica no GitHub se há releases mais recentes. Se houver atualização, ela baixa o novo `.exe` para um diretório temporário e propõe aplicá-la no próximo reinício.
