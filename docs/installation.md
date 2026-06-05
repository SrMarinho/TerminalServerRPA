# Instalação

## Instalador (recomendado)

Baixe `TerminalServerRPA_Setup.exe` em [GitHub Releases](https://github.com/SrMarinho/TerminalServerRPA/releases).

- Instala em `%LocalAppData%\TerminalServerRPA\` (sem privilégio de administrador)
- Cria atalho no desktop e no menu iniciar
- Abre automaticamente após a instalação

### Primeira execução

1. Dê duplo clique no atalho ou em `TerminalServerRPA.exe`
2. Na primeira execução, o app baixa o driver do Playwright automaticamente (~90MB)
3. A janela abre em `http://127.0.0.1:8080`
4. Se a porta 8080 estiver ocupada, a aplicação seleciona automaticamente a próxima livre
5. Se a aplicação já estiver rodando, a instância existente recebe foco

### Atualização automática

Ao abrir e a cada 60 segundos, o app verifica se há nova versão no GitHub.
Se houver, um dialog aparece pedindo confirmação. Ao aceitar:

1. Baixa o novo installer em segundo plano
2. Fecha o app
3. Roda o installer silenciosamente (`/VERYSILENT`)
4. Reinicia na nova versão

### System tray

Fechar a janela minimiza para o system tray. Clique duplo no ícone para restaurar. Menu "Sair" encerra completamente.

---

## A partir do código-fonte

### Pré-requisitos

- Python 3.10+ (desenvolvido em 3.14)
- Gerenciador de pacotes [uv](https://docs.astral.sh/uv/)

### Passos

```bash
git clone <repo-url>
cd TerminalServerRPA

uv sync

# Instalar o navegador do Playwright (necessário para tarefas RPA)
uv run playwright install chromium

# Rodar a interface GUI
uv run python main.py gui

# Ou interface web pura (abre no navegador padrão)
uv run python main.py web
```
