import os
import subprocess
import sys
import zipfile
from pathlib import Path

import httpx

from src.infrastructure.logger import get_logger

log = get_logger("TerminalServerRPA.playwright_setup")


def _driver_dir() -> Path:
    if getattr(sys, "frozen", False):
        from src.config.settings import APP_DATA_DIR

        return APP_DATA_DIR / "playwright" / "driver"
    from playwright._impl._driver import compute_driver_executable

    return Path(compute_driver_executable()[0]).parent


def _driver_exe() -> Path:
    return _driver_dir() / "node.exe"


def _version_file() -> Path:
    return _driver_dir() / ".installed_version"


def _playwright_version() -> str:
    from importlib.metadata import version

    return version("playwright")


def _installed_version() -> str:
    vf = _version_file()
    return vf.read_text(encoding="utf-8").strip() if vf.exists() else ""


def _download_url(version: str) -> str:
    return f"https://playwright.azureedge.net/builds/driver/playwright-{version}-win32_x64.zip"


def _browsers_dir() -> Path:
    from src.config.settings import APP_DATA_DIR

    return APP_DATA_DIR / "playwright-browsers"


def configure_playwright_env() -> None:
    if not getattr(sys, "frozen", False):
        return
    from src.config.settings import APP_DATA_DIR

    os.environ["PLAYWRIGHT_NODEJS_PATH"] = str(APP_DATA_DIR / "playwright" / "driver" / "node.exe")
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(APP_DATA_DIR / "playwright-browsers")


def ensure_playwright_driver() -> None:
    version = _playwright_version()

    if _driver_exe().exists() and _installed_version() == version:
        return

    log.info("playwright.driver_setup", version=version, action="downloading")
    driver_dir = _driver_dir()
    driver_dir.mkdir(parents=True, exist_ok=True)

    zip_path = driver_dir.parent / "playwright-driver.zip"
    try:
        with httpx.stream("GET", _download_url(version), follow_redirects=True, timeout=300) as resp:
            resp.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)

        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(driver_dir)

        log.info("playwright.browser_installing", version=version)
        node = str(_driver_exe())
        cli = str(driver_dir / "package" / "cli.js")
        env = {**os.environ, "PLAYWRIGHT_BROWSERS_PATH": str(_browsers_dir())}
        subprocess.run([node, cli, "install", "chromium"], check=True, env=env, cwd=str(driver_dir))

        _version_file().write_text(version, encoding="utf-8")
        log.info("playwright.driver_installed", version=version, path=str(driver_dir))
    except Exception as e:
        log.error("playwright.driver_download_failed", version=version, error=str(e))
        raise
    finally:
        zip_path.unlink(missing_ok=True)
