"""Current application version — read from pyproject.toml at build time.

Kept in a separate file so updater.py and startup code can import it
without pulling in the rest of the app.
"""

from importlib.metadata import version as _pkg_version

try:
    VERSION: str = _pkg_version("terminalserverrpa")
except Exception:
    # Fallback when not installed as a package (dev mode, CI without install).
    import tomllib
    from pathlib import Path

    _pyproject = Path(__file__).resolve().parent.parent.parent.parent / "pyproject.toml"
    if _pyproject.exists():
        with _pyproject.open("rb") as _f:
            VERSION = tomllib.load(_f)["project"]["version"]
    else:
        VERSION = "0.0.0-dev"
