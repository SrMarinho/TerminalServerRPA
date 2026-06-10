from abc import ABC, abstractmethod

from src.automation.browser.browser_manager import BrowserManager
from src.automation.pages.home_page import HomePage
from src.automation.pages.senior_login_page import SeniorLoginPage
from src.automation.pages.sidebar_navigator import SidebarNavigator
from src.automation.pages.ts_applications_page import TsApplicationsPage
from src.automation.pages.ts_login_page import TsLoginPage
from src.config.settings import ASSETS_DIR, DOWNLOADS_BASE
from src.infrastructure.logger import get_logger
from src.infrastructure.task_registry import TaskRegistry
from src.infrastructure.task_runner import SkipStep
from src.infrastructure.vault import Vault
from src.utils.image_match import MatchThreshold, find_template, find_text, find_text_position
from src.utils.window_utils import maximize_window

register = TaskRegistry.register


class TaskBase(ABC):
    """Stable contract every plugin task implements. Formalises the duck-typed protocol.

    The host instantiates tasks as ``task_cls(runner=<TaskRunner>, vault=<Vault>)``.
    """

    def __init__(self, runner=None, vault=None):
        self._runner = runner
        self._vault = vault or Vault()

    @abstractmethod
    async def execute(self, params: dict) -> dict: ...

    @staticmethod
    def get_schema() -> list:
        return []

    @staticmethod
    def get_steps():
        return {}


__all__ = [
    "register",
    "TaskBase",
    "SkipStep",
    "BrowserManager",
    "MatchThreshold",
    "find_template",
    "find_text",
    "find_text_position",
    "maximize_window",
    "get_logger",
    "Vault",
    "ASSETS_DIR",
    "DOWNLOADS_BASE",
    "HomePage",
    "SeniorLoginPage",
    "SidebarNavigator",
    "TsApplicationsPage",
    "TsLoginPage",
]
