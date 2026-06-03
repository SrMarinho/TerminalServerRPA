import os
from pathlib import Path

BASE_DIR = Path(__file__).parents[2]
ASSETS_DIR = BASE_DIR / "assets"
DEV_MODE: bool = os.getenv("TERMINALSERVERRPA_DEV", "").lower() in ("1", "true")

DOWNLOADS_BASE = Path.home() / ".local" / "downloads"
