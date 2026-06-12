from pathlib import Path

from tsrpa import ASSETS_DIR

from ..steps import StepNames

_PLUGIN_ASSETS = Path(__file__).parent.parent / "assets"
HOME_IMG = ASSETS_DIR / "Senior" / "components" / "sidebar" / "home" / "index.png"
REPORT_TITLE_IMG = _PLUGIN_ASSETS / "selecao_modelos_para_execucao" / "window_title.png"
_OUTPUT_LOADING_DIR = _PLUGIN_ASSETS / "selecao_modelos_para_execucao" / "valores_entrada_modelo" / "output_loading"
IMG_SELECIONANDO = _OUTPUT_LOADING_DIR / "selecionando_informacoes.png"
IMG_AGUARDANDO = _OUTPUT_LOADING_DIR / "aguarde_preparando_solicitacao.png"

SIDEBAR_ITEMS = [
    (StepNames.GESTAO_EMPRESARIAL, "gestao_empresarial/index.png"),
    (StepNames.FINANCAS, "gestao_empresarial/financas/index.png"),
    (StepNames.GESTAO_CONTAS_RECEBER, "gestao_empresarial/financas/gestao_contas_receber/index.png"),
    (StepNames.CONTAS_RECEBER, "gestao_empresarial/financas/gestao_contas_receber/contas_receber/index.png"),
    (StepNames.RELATORIOS, "gestao_empresarial/financas/gestao_contas_receber/contas_receber/relatorios/index.png"),
]
