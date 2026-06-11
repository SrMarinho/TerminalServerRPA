from enum import Enum


class StepNames(str, Enum):
    LOGIN_TS = "Login TS"
    INICIANDO_SENIOR = "Iniciando Senior"
    LOGIN_SENIOR = "Login Senior"
    MAXIMIZANDO = "Maximizando"
    CARREGANDO_SENIOR = "Carregando Senior"
    GESTAO_EMPRESARIAL = "Gestão Empresarial"
    FINANCAS = "Finanças"
    GESTAO_CONTAS_RECEBER = "Gestão Contas Receber"
    CONTAS_RECEBER = "Contas Receber"
    RELATORIOS = "Relatórios"
    MAXIMIZANDO_RELATORIO = "Maximizando Relatório"
    DIGITANDO_RELATORIO = "Digitando Relatório"
    MAXIMIZANDO_VALORES = "Maximizando Valores"
    PREENCHENDO_ENTRADA = "Preenchendo Entrada"
    PREENCHENDO_SAIDA = "Preenchendo Saída"
    GERANDO_RELATORIO = "Gerando Relatório"
    SELECIONANDO_INFORMACOES = "Selecionando Informações"
    AGUARDANDO_SOLICITACAO = "Aguardando Solicitação"
    CONCLUIDO = "Concluido"

    def __str__(self) -> str:
        return self.value
