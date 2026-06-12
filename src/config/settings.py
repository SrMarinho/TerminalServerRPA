import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parents[2]
ASSETS_DIR = BASE_DIR / "assets"
DEV_MODE: bool = os.getenv("TERMINALSERVERRPA_DEV", "").lower() in ("1", "true")
HEADLESS: bool = os.getenv("TERMINALSERVERRPA_HEADLESS", "1").lower() not in ("0", "false")

DOWNLOADS_BASE = Path.home() / "downloads"

APP_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "TerminalServerRPA"

# Single source of truth for the SQLite DB (execution history + task configs).
# Lives under APP_DATA_DIR so a packaged build never tries to write next to the
# read-only install dir, and the location is stable regardless of the CWD.
DB_PATH = APP_DATA_DIR / "executions.db"

if getattr(sys, "frozen", False):
    # frozen: bundled plugins ship inside _internal/plugins/, user plugins in LOCALAPPDATA
    PLUGINS_DIRS: list[Path] = [Path(sys._MEIPASS) / "plugins", APP_DATA_DIR / "plugins"]  # type: ignore[attr-defined]
else:
    PLUGINS_DIRS = [BASE_DIR / "plugins"]
