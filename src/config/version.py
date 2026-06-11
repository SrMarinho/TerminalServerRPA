"""Current application version — read from pyproject.toml at import time.

Resolution order:
1. importlib.metadata (works when installed as a package, e.g. `uv run`)
2. pyproject.toml next to the PyInstaller _MEIPASS bundle root (frozen onedir)
3. pyproject.toml in the source tree (dev / CI without install)
4. Hardcoded fallback "0.0.0-dev"
"""

import sys
from pathlib import Path


def parse_version(v: str) -> tuple[int, ...]:
    """Parse '1.2.3rc1'-style strings into a comparable tuple (non-digits stripped)."""
    parts = []
    for chunk in v.split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _load_version() -> str:
    try:
        from importlib.metadata import version as _pkg_version

        return _pkg_version("terminalserverrpa")
    except Exception:
        pass

    # sys._MEIPASS is set by PyInstaller to the _internal/ dir in onedir builds.
    frozen_root = Path(getattr(sys, "_MEIPASS", "") or "")
    # When running from source, __file__ is src/config/version.py → repo root is 3 levels up.
    source_root = Path(__file__).resolve().parent.parent.parent

    for root in (frozen_root, source_root):
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            try:
                import tomllib

                with pyproject.open("rb") as f:
                    return tomllib.load(f)["project"]["version"]
            except Exception:
                pass

    return "0.0.0-dev"


VERSION: str = _load_version()
