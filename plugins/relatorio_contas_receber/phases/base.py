import asyncio

from tsrpa import MatchThreshold, SkipStep, find_template, get_logger

_log = get_logger("TerminalServerRPA.report-generation")


class PhaseBase:
    def __init__(self, runner=None):
        self._runner = runner

    @property
    def _log(self):
        return self._runner.log if self._runner else (lambda m, **kw: None)

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

    async def _wait_loading(self, page, img_path, step_name, appear_timeout: float = 5.0, next_img_path=None) -> None:
        await self._step(step_name)
        deadline_appear = asyncio.get_event_loop().time() + appear_timeout
        while asyncio.get_event_loop().time() < deadline_appear:
            shot = await page.screenshot()
            if find_template(shot, img_path, MatchThreshold.DEFAULT):
                break
            await asyncio.sleep(0.3)
        while True:
            shot = await page.screenshot()
            if not find_template(shot, img_path, MatchThreshold.DEFAULT):
                return
            if next_img_path and find_template(shot, next_img_path, MatchThreshold.DEFAULT):
                return
            await asyncio.sleep(0.5)
