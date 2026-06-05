from src.automation.browser.browser_manager import BrowserManager
from src.infrastructure.task_registry import TaskRegistry
from src.infrastructure.task_runner import SkipStep
from src.infrastructure.vault import Vault
from src.utils.image_match import MatchThreshold, find_template
from src.utils.window_utils import maximize_window

register = TaskRegistry.register

__all__ = [
    "register",
    "SkipStep",
    "BrowserManager",
    "MatchThreshold",
    "find_template",
    "maximize_window",
    "Vault",
]
