# Guia do usuário

## Iniciando a interface web

```bash
# Porta padrão 8080, abre o navegador automaticamente
python main.py web

# Porta customizada, sem navegador
python main.py web --port 9090 --no-browser
```

Se a porta 8080 estiver ocupada, a aplicação tenta 8081, 8082, etc. até encontrar uma porta livre.

Se a aplicação já estiver rodando, a segunda instância foca a aba existente do navegador em vez de iniciar um segundo servidor.

## Gerenciando credenciais

### Pela interface web

1. Abra `http://127.0.0.1:PORTA` no navegador
2. Em **Credenciais**, preencha Serviço, Usuário e Senha
3. Clique em **Salvar**
4. As credenciais salvas aparecem na lista abaixo do formulário
5. Clique em **Excluir** para remover uma credencial

### Pela CLI

```bash
# Salvar uma credencial (a senha é solicitada de forma segura)
python main.py vault set meu-servico -u admin

# Recuperar uma credencial
python main.py vault get meu-servico -u admin

# Excluir todas as credenciais de um serviço
python main.py vault delete meu-servico

# Listar todas as credenciais armazenadas
python main.py vault list
```

As credenciais são criptografadas com Fernet antes de serem armazenadas no Gerenciador de Credenciais do Windows via a biblioteca `keyring`. A chave de criptografia é, ela própria, armazenada no Gerenciador de Credenciais.

## Executando tarefas RPA

### Pela interface web

1. Na seção **Tarefas**, clique no nome da tarefa (ex.: `Relatório Contas Receber`)
2. Preencha os campos do formulário da tarefa, se houver
3. O selo de status indica o progresso: em execução, pausada, concluída, falhou
4. Use **Pausar**, **Retomar**, **Cancelar** e **Pular** para controlar a execução
5. O log ao vivo aparece no painel de **Execução**

### Pela CLI

```bash
# Executar uma tarefa
python main.py run "Relatório Contas Receber"
```

## Visualizando logs

Todos os eventos são registrados em `logs/TerminalServerRPA.jsonl` no formato JSON estruturado (uma linha por evento).

```bash
# Mostrar logs recentes
python main.py logs

# Filtrar por nível
python main.py logs --level error

# Filtrar por tarefa
python main.py logs --task "Relatório Contas Receber"

# Saída JSON crua
python main.py logs --json
```
