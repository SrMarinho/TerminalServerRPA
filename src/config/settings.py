import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parents[2]
ASSETS_DIR = BASE_DIR / "assets"
DEV_MODE: bool = os.getenv("TERMINALSERVERRPA_DEV", "").lower() in ("1", "true")

DOWNLOADS_BASE = Path.home() / ".local" / "downloads"

APP_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "TerminalServerRPA"

if getattr(sys, "frozen", False):
    # frozen: bundled plugins ship inside _internal/plugins/, user plugins in LOCALAPPDATA
    PLUGINS_DIRS: list[Path] = [Path(sys._MEIPASS) / "plugins", APP_DATA_DIR / "plugins"]  # type: ignore[attr-defined]
else:
    PLUGINS_DIRS = [BASE_DIR / "plugins"]
