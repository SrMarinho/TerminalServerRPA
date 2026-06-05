import importlib
import sys
from pathlib import Path

from src.infrastructure.logger import get_logger

log = get_logger("TerminalServerRPA.plugins")


def _scan_dir(plugins_dir: Path) -> None:
    if not plugins_dir.exists():
        plugins_dir.mkdir(parents=True, exist_ok=True)
        return
    root = str(plugins_dir)
    if root not in sys.path:
        sys.path.insert(0, root)
    for entry in plugins_dir.iterdir():
        if not entry.is_dir() or not (entry / "__init__.py").exists():
            continue
        try:
            importlib.import_module(entry.name)
            log.info("plugin.loaded", name=entry.name)
        except Exception:
            log.exception("plugin.load_failed", name=entry.name)


def load_plugins() -> None:
    from src.config.settings import PLUGINS_DIRS

    for d in PLUGINS_DIRS:
        _scan_dir(d)
