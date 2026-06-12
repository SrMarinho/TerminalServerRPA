import asyncio

from tsrpa import HomePage, MatchThreshold, SidebarNavigator, SkipStep, find_template

from ..steps import StepNames
from .base import PhaseBase
from .constants import HOME_IMG, SIDEBAR_ITEMS


async def _wait_for_home(page, runner=None, timeout_s: float = 120) -> None:
    deadline = asyncio.get_event_loop().time() + timeout_s
    while True:
        screenshot = await page.screenshot()
        if find_template(screenshot, HOME_IMG, MatchThreshold.DEFAULT):
            return
        if asyncio.get_event_loop().time() >= deadline:
            return
        if runner:
            await runner.checkpoint()
        await asyncio.sleep(3)


class HomeSetupPhase(PhaseBase):
    async def execute(self, remote_page):
        home = None
        if remote_page:
            try:
                await self._step(StepNames.MAXIMIZANDO)
                home = HomePage(remote_page, log=self._runner.log if self._runner else None)
                await home.maximize()
            except SkipStep:
                pass
            await self._step(StepNames.CARREGANDO_SENIOR, _wait_for_home(remote_page, self._runner))
        else:
            await self._step(StepNames.MAXIMIZANDO)
            await self._step(StepNames.CARREGANDO_SENIOR)
        return home


class SidebarPhase(PhaseBase):
    async def execute(self, home) -> None:
        nav = SidebarNavigator()
        await nav.navigate(home, SIDEBAR_ITEMS, self._step)
