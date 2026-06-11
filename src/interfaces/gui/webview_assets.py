"""Loaders for the static HTML/JS shipped with the GUI adapter.

Keeps frontend markup out of Python: the files live in gui/assets/ and Python
only substitutes placeholders. Path is __file__-relative — the same pattern the
web templates use, which already works in frozen (PyInstaller) builds.
"""

from functools import lru_cache
from pathlib import Path

_ASSETS_DIR = Path(__file__).parent / "assets"


@lru_cache
def load_asset(name: str) -> str:
    return (_ASSETS_DIR / name).read_text(encoding="utf-8")


def js_escape(s: str) -> str:
    """Escape a string for embedding inside a single-quoted JS literal."""
    return s.replace("\\", "\\\\").replace("'", "\\'").replace("\r", "").replace("\n", "\\n")
