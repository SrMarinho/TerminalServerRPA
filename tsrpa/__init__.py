from src.automation.browser.browser_manager import BrowserManager
from src.automation.pages.home_page import HomePage
from src.automation.pages.senior_login_page import SeniorLoginPage
from src.automation.pages.sidebar_navigator import SidebarNavigator
from src.automation.pages.ts_applications_page import TsApplicationsPage
from src.automation.pages.ts_login_page import TsLoginPage
from src.config.settings import ASSETS_DIR, DOWNLOADS_BASE
from src.infrastructure.task_registry import TaskRegistry
from src.infrastructure.task_runner import SkipStep
from src.infrastructure.vault import Vault
from src.utils.image_match import MatchThreshold, find_template, find_text, find_text_position
from src.utils.window_utils import maximize_window

register = TaskRegistry.register

__all__ = [
    "register",
    "SkipStep",
    "BrowserManager",
    "MatchThreshold",
    "find_template",
    "find_text",
    "find_text_position",
    "maximize_window",
    "Vault",
    "ASSETS_DIR",
    "DOWNLOADS_BASE",
    "HomePage",
    "SeniorLoginPage",
    "SidebarNavigator",
    "TsApplicationsPage",
    "TsLoginPage",
]
