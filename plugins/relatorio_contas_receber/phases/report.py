import asyncio

from tsrpa import SkipStep, get_logger, maximize_window

from ..download import OutputConfig
from ..pages.reports.constants import CsvRemoverEspacos, FormatoArquivo
from ..pages.selecao_modelos_para_execucao_page import SelecaoModelosParaExecucaoPage
from ..pages.valores_entrada_modelo_page import ValoresEntradaModeloPage
from ..steps import StepNames
from .base import PhaseBase
from .constants import IMG_AGUARDANDO, IMG_SELECIONANDO, REPORT_TITLE_IMG

_log = get_logger("TerminalServerRPA.report-generation")


class MaximizeReportPhase(PhaseBase):
    async def execute(self, remote_page) -> None:
        await self._step(
            StepNames.MAXIMIZANDO_RELATORIO,
            maximize_window(
                remote_page,
                self._runner.log if self._runner else None,
                title_img=REPORT_TITLE_IMG,
            ),
        )
        await asyncio.sleep(1)


class OpenReportPhase(PhaseBase):
    async def execute(self, remote_page, report) -> tuple:
        await self._step(StepNames.DIGITANDO_RELATORIO)
        selecao = SelecaoModelosParaExecucaoPage(remote_page, log=self._runner.log if self._runner else None)
        valores = None
        try:
            valores = await selecao.open_report(report)
        except SkipStep:
            _log.warning("step.skipped.open_report", step=StepNames.DIGITANDO_RELATORIO)
        if valores is None:
            valores = ValoresEntradaModeloPage(remote_page, log=self._runner.log if self._runner else None)
        return selecao, valores


class FillEntradaPhase(PhaseBase):
    async def execute(self, valores, report, params: dict) -> None:
        await self._step(StepNames.MAXIMIZANDO_VALORES, valores.maximize())
        await self._step(StepNames.PREENCHENDO_ENTRADA, valores.fill(report, params))


class FillSaidaPhase(PhaseBase):
    async def execute(self, valores, output_config: OutputConfig, params: dict) -> None:
        await self._step(StepNames.PREENCHENDO_SAIDA)
        await asyncio.sleep(0.5)
        await valores.click_saida_tab()
        await asyncio.sleep(0.5)
        await valores.select_arquivo_checkbox()
        await asyncio.sleep(0.3)
        await valores.select_formato_arquivo(params.get("formato_arquivo", FormatoArquivo.EXCEL))
        await asyncio.sleep(0.3)
        await valores.fill_saida_label_field("Caminho", r"\\tsclient\WebFile")
        await asyncio.sleep(0.2)
        await valores.fill_saida_label_field("Nome", output_config.nome_arquivo)
        await asyncio.sleep(0.2)
        if params.get("formato_arquivo") == FormatoArquivo.CSV:
            await valores.fill_saida_label_field("Separador", params.get("csv_separador", ","))
            await asyncio.sleep(0.2)
            await valores.fill_saida_label_field("Delimitador", params.get("csv_delimitador", '"'))
            await asyncio.sleep(0.2)
            if params.get("csv_remover_espacos") == CsvRemoverEspacos.SIM:
                await valores.click_ocr_label("Remover")
                await asyncio.sleep(0.2)
        await asyncio.sleep(0.3)


class GenerateDownloadPhase(PhaseBase):
    async def execute(self, context, remote_page, valores, selecao, output_config: OutputConfig) -> str | None:
        await self._step(StepNames.GERANDO_RELATORIO)
        log = self._runner.log if self._runner else (lambda m: None)

        if context is not None:
            download_future: asyncio.Future = asyncio.get_running_loop().create_future()

            def _on_download(dl):
                if not download_future.done():
                    download_future.set_result(dl)

            context.on("download", _on_download)
            remote_page.on("download", _on_download)
            try:
                await valores.click_ok()
                await self._wait_loading(
                    remote_page, IMG_SELECIONANDO, StepNames.SELECIONANDO_INFORMACOES, next_img_path=IMG_AGUARDANDO
                )
                await self._step(StepNames.AGUARDANDO_SOLICITACAO)
                await self._step(StepNames.SALVANDO_ARQUIVO)
                dl = await download_future
            finally:
                context.remove_listener("download", _on_download)
                remote_page.remove_listener("download", _on_download)

            log(f"download.intercepted: suggested_filename={dl.suggested_filename!r}")
            dest = output_config.dest
            output_config.downloads_path.mkdir(parents=True, exist_ok=True)
            await dl.save_as(dest)
            size = dest.stat().st_size if dest.exists() else -1
            log(f"download.saved: path={dest!r} size={size}B")
            await selecao.close()
            return str(dest)
        else:
            await valores.click_ok()
            await self._wait_loading(
                remote_page, IMG_SELECIONANDO, StepNames.SELECIONANDO_INFORMACOES, next_img_path=IMG_AGUARDANDO
            )
            await self._step(StepNames.AGUARDANDO_SOLICITACAO)
            await selecao.close()
            return output_config.nome_arquivo
