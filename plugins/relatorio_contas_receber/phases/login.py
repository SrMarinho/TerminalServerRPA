from tsrpa import BrowserManager, SeniorLoginPage, SkipStep, TsApplicationsPage, TsLoginPage, get_logger

from ..steps import StepNames
from .base import PhaseBase

_log = get_logger("TerminalServerRPA.report-generation")


class TsLoginPhase(PhaseBase):
    async def execute(self, context, page, ts_creds: dict, base_url: str):
        remote_page = None
        try:
            await self._step(StepNames.LOGIN_TS)
            login_p = TsLoginPage(page, base_url)
            await login_p.navigate()
            async with context.expect_event("page", timeout=60000) as new_page_info:
                await login_p.login(ts_creds["username"], ts_creds["password"])
            remote_page = await new_page_info.value
            await remote_page.wait_for_load_state("load", timeout=60000)
        except SkipStep:
            return None
        screen_w, screen_h = BrowserManager.get_screen_size()
        await BrowserManager.maximize_cdp(context, remote_page, screen_w, screen_h)
        apps_page = TsApplicationsPage(remote_page, log=self._runner.log if self._runner else None)
        await apps_page.click_application("Gestão Empresarial", asset_folder="Senior")
        return remote_page


class SeniorLoadingPhase(PhaseBase):
    async def execute(self, remote_page, senior_creds: dict):
        if not remote_page:
            return None
        try:
            await self._step(StepNames.INICIANDO_SENIOR)
            senior_login = SeniorLoginPage(
                remote_page,
                log=self._runner.log if self._runner else None,
                checkpoint=self._runner.checkpoint if self._runner else None,
            )
            await senior_login.wait_for_iniciando()
            return senior_login
        except SkipStep:
            return None


class SeniorLoginPhase(PhaseBase):
    async def execute(self, remote_page, senior_login, senior_creds: dict) -> None:
        if not remote_page or not senior_login:
            await self._step(StepNames.LOGIN_SENIOR)
            return
        await self._step(StepNames.LOGIN_SENIOR, senior_login.wait_for_login_screen())
        try:
            await senior_login.fill_and_submit(senior_creds["username"], senior_creds["password"])
        except SkipStep:
            _log.warning("step.skipped.submit", step=StepNames.LOGIN_SENIOR)
