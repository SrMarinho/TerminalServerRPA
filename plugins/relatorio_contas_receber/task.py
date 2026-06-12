from pathlib import Path

from tsrpa import DOWNLOADS_BASE, BrowserManager, SkipStep, TaskBase, get_logger, register

from .download import OutputConfig
from .pages.reports import REPORTS, REPORTS_BY_CODE
from .pages.reports.constants import FormatoArquivo
from .phases import (
    FillEntradaPhase,
    FillSaidaPhase,
    GenerateDownloadPhase,
    HomeSetupPhase,
    MaximizeReportPhase,
    OpenReportPhase,
    SeniorLoadingPhase,
    SeniorLoginPhase,
    SidebarPhase,
    TsLoginPhase,
)
from .steps import StepNames
from .template import TEMPLATE_VARS, render_template

_log = get_logger("TerminalServerRPA.report-generation")


@register("Relatório Contas Receber")
class GeracaoRelatorio(TaskBase):
    @staticmethod
    def get_schema():
        return [
            {
                "name": "base_url",
                "label": "URL Base",
                "type": "string",
                "default": "https://sistema.nazaria.com.br/",
                "group": "Conexão",
                "group_panel": "inline",
            },
            {
                "name": "TS Credenciais",
                "label": "TS Credenciais",
                "type": "credential",
                "group": "Conexão",
                "group_panel": "inline",
                "required": True,
            },
            {
                "name": "Senior Credenciais",
                "label": "Senior Credenciais",
                "type": "credential",
                "group": "Conexão",
                "group_panel": "inline",
                "required": True,
            },
            {
                "name": "relatorio",
                "label": "Relatório",
                "type": "select",
                "options": [{"value": r.code, "label": r.label} for r in REPORTS],
                "group_panel": "inline",
            },
            *[
                {
                    **field,
                    "when": {**field.get("when", {}), "relatorio": r.code},
                    "group": "Parâmetros",
                    "group_panel": "modal",
                }
                for r in REPORTS
                for field in r.get_fields()
            ],
            {
                "name": "output_dir",
                "label": "Pasta de destino",
                "type": "template",
                "default": str(DOWNLOADS_BASE / "{report_code}"),
                "placeholder": r"Ex: C:\Relatorios\{report_code}\{year}\{month}",
                "is_path": True,
                "template_vars": TEMPLATE_VARS,
                "group": "Saída de Arquivo",
                "group_panel": "inline",
                "group_open": True,
            },
            {
                "name": "output_name",
                "label": "Nome do arquivo",
                "type": "template",
                "default": "rel_{report_code}_{now}",
                "placeholder": "Ex: rel_{report_code}_{now:%Y%m%d_%H%M%S}",
                "template_vars": TEMPLATE_VARS,
                "group": "Saída de Arquivo",
                "group_panel": "inline",
            },
        ]

    @staticmethod
    def get_steps():
        return {
            "Login": [StepNames.LOGIN_TS, StepNames.INICIANDO_SENIOR, StepNames.LOGIN_SENIOR],
            "Processamento": [
                StepNames.MAXIMIZANDO,
                StepNames.CARREGANDO_SENIOR,
                StepNames.GESTAO_EMPRESARIAL,
                StepNames.FINANCAS,
                StepNames.GESTAO_CONTAS_RECEBER,
                StepNames.CONTAS_RECEBER,
                StepNames.RELATORIOS,
                StepNames.MAXIMIZANDO_RELATORIO,
                StepNames.DIGITANDO_RELATORIO,
                StepNames.MAXIMIZANDO_VALORES,
                StepNames.PREENCHENDO_ENTRADA,
                StepNames.PREENCHENDO_SAIDA,
                StepNames.GERANDO_RELATORIO,
                StepNames.SELECIONANDO_INFORMACOES,
                StepNames.AGUARDANDO_SOLICITACAO,
                StepNames.SALVANDO_ARQUIVO,
            ],
            "Finalização": [StepNames.CONCLUIDO],
        }

    def _resolve_creds(self, params: dict, key: str = "credentials") -> dict:
        raw = params.get(key, {})
        if isinstance(raw, dict) and "service" in raw:
            svc = raw["service"]
            users = self._vault.list_credentials(svc)
            if users:
                username = users[0]["username"]
                password = self._vault.get_password(svc, username)
                return {"username": username, "password": password or ""}
        return raw if isinstance(raw, dict) else {}

    def _attach_page(self, page) -> None:
        if self._runner:
            self._runner.page = page

    async def _step(self, name: str, coro=None) -> None:
        try:
            if self._runner:
                await self._runner.report_step(name)
            if coro is not None:
                await coro
        except SkipStep:
            _log.warning("step.skipped", step=name)

    async def _replay_steps(self, *names: str) -> None:
        for name in names:
            await self._step(name)

    def _phases(self):
        return {
            "ts_login": TsLoginPhase(self._runner),
            "senior_loading": SeniorLoadingPhase(self._runner),
            "senior_login": SeniorLoginPhase(self._runner),
            "home_setup": HomeSetupPhase(self._runner),
            "sidebar": SidebarPhase(self._runner),
            "maximize_report": MaximizeReportPhase(self._runner),
            "open_report": OpenReportPhase(self._runner),
            "fill_entrada": FillEntradaPhase(self._runner),
            "fill_saida": FillSaidaPhase(self._runner),
            "generate_download": GenerateDownloadPhase(self._runner),
        }

    async def _phase_report_actions(self, remote_page, relatorio_code: str, params: dict, context=None) -> str | None:
        ph = self._phases()
        if not remote_page:
            await self._replay_steps(
                StepNames.MAXIMIZANDO_RELATORIO,
                StepNames.DIGITANDO_RELATORIO,
                StepNames.MAXIMIZANDO_VALORES,
                StepNames.PREENCHENDO_ENTRADA,
                StepNames.PREENCHENDO_SAIDA,
                StepNames.SELECIONANDO_INFORMACOES,
                StepNames.AGUARDANDO_SOLICITACAO,
            )
            return None

        await ph["maximize_report"].execute(remote_page)

        report = REPORTS_BY_CODE.get(relatorio_code)
        if not report:
            await self._replay_steps(
                StepNames.DIGITANDO_RELATORIO,
                StepNames.MAXIMIZANDO_VALORES,
                StepNames.PREENCHENDO_ENTRADA,
                StepNames.PREENCHENDO_SAIDA,
            )
            return None

        selecao, valores = await ph["open_report"].execute(remote_page, report)
        await ph["fill_entrada"].execute(valores, report, params)

        tpl_ctx = {
            "report_code": relatorio_code,
            "report_desc": report.description,
            **{k: v for k, v in params.items() if isinstance(v, str | int | float)},
        }
        output_dir_tpl = params.get("output_dir") or str(DOWNLOADS_BASE / "{report_code}")
        output_name_tpl = params.get("output_name") or "rel_{report_code}_{now}"
        nome_arquivo = render_template(output_name_tpl, tpl_ctx)
        downloads_path = Path(render_template(output_dir_tpl, tpl_ctx, is_path=True)).expanduser()
        downloads_path.mkdir(parents=True, exist_ok=True)

        output_config = OutputConfig(
            downloads_path=downloads_path,
            nome_arquivo=nome_arquivo,
            fmt=params.get("formato_arquivo", FormatoArquivo.EXCEL),
        )

        await ph["fill_saida"].execute(valores, output_config, params)
        return await ph["generate_download"].execute(context, remote_page, valores, selecao, output_config)

    async def execute(self, params: dict) -> dict:
        from playwright.async_api import async_playwright

        ts_creds = self._resolve_creds(params, "TS Credenciais")
        senior_creds = self._resolve_creds(params, "Senior Credenciais")
        base_url = params.get("base_url", "")
        relatorio_code = params.get("relatorio", "")
        ph = self._phases()

        async with async_playwright() as p:
            browser, context, page, _w, _h = await BrowserManager.launch(p)
            try:
                self._attach_page(page)
                remote = await ph["ts_login"].execute(context, page, ts_creds, base_url)
                self._attach_page(remote)
                sl = await ph["senior_loading"].execute(remote, senior_creds)
                await ph["senior_login"].execute(remote, sl, senior_creds)
                home = await ph["home_setup"].execute(remote)
                await ph["sidebar"].execute(home)
                arquivo = await self._phase_report_actions(remote, relatorio_code, params, context=context)
                await self._step(StepNames.CONCLUIDO)
                return {"status": "ok", **({"arquivo": arquivo} if arquivo else {})}
            finally:
                if self._runner:
                    self._runner.page = None
                await context.close()
                await browser.close()
