import hashlib
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx

from src.config.version import parse_version as _parse_version
from src.infrastructure.logger import get_logger

log = get_logger("TerminalServerRPA.updater")

# Public releases-only repo (source stays in the private repo). Being public,
# the GitHub API and asset downloads need no auth token — nothing to embed or
# leak in the shipped binary. Integrity is enforced via the .sha256 checksum.
OWNER = "SrMarinho"
REPO = "TerminalServerRPA-releases"


@dataclass
class Release:
    tag_name: str
    html_url: str
    assets: list

    @property
    def version(self) -> str:
        return self.tag_name.lstrip("v")


def check_for_update(current_version: str) -> Release | None:
    if os.environ.get("TSRPA_FAKE_UPDATE"):
        log.info("update.fake_mode")
        return Release(tag_name="v99.0.0", html_url="", assets=[])
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
    try:
        resp = httpx.get(url, timeout=10)
        if resp.status_code == 404:
            log.debug("update.no_releases")
            return None
        resp.raise_for_status()
        data = resp.json()
        release = Release(
            tag_name=data["tag_name"],
            html_url=data["html_url"],
            assets=data.get("assets", []),
        )
        if _parse_version(release.version) > _parse_version(current_version):
            log.info("update.available", current=current_version, latest=release.version)
            return release
        log.info("update.up_to_date", version=current_version)
    except Exception as e:
        log.warning("update.check_failed", error=str(e))
    return None


def _download_asset(
    asset: dict,
    dest: Path,
    progress_cb: Callable[[int, int], None] | None = None,
) -> Path | None:
    headers = {"Accept": "application/octet-stream"}
    try:
        with httpx.stream("GET", asset["url"], headers=headers, follow_redirects=True, timeout=120) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            dest.parent.mkdir(parents=True, exist_ok=True)
            downloaded = 0
            with open(dest, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb:
                        progress_cb(downloaded, total)
        log.info("update.downloaded", path=str(dest))
        return dest
    except Exception as e:
        log.error("update.download_failed", asset=asset.get("name"), error=str(e))
    return None


def _verify_checksum(file: Path, release: Release) -> bool:
    # Fail closed: a missing or undownloadable checksum aborts the update.
    # NOTE: the .sha256 ships in the same release as the EXE, so this proves
    # download integrity only — NOT release authenticity (an attacker who can
    # publish a release controls both files). Real authenticity requires
    # Authenticode-signing the installer and verifying the signature here.
    exe_name = file.name
    checksum_asset = next((a for a in release.assets if a["name"] == f"{exe_name}.sha256"), None)
    if checksum_asset is None:
        log.error("update.checksum_missing", expected=f"{exe_name}.sha256")
        return False

    tmp = file.parent / f"{exe_name}.sha256_tmp"
    downloaded = _download_asset(checksum_asset, tmp)
    if downloaded is None:
        log.error("update.checksum_download_failed")
        return False

    try:
        expected = downloaded.read_text(encoding="utf-8").split()[0].strip()
        actual = hashlib.sha256(file.read_bytes()).hexdigest()
        if actual != expected:
            log.error("update.checksum_mismatch", expected=expected, actual=actual)
            return False
        log.info("update.checksum_ok")
        return True
    finally:
        tmp.unlink(missing_ok=True)


def apply_update(
    release: Release,
    progress_cb: Callable[[int, int], None] | None = None,
) -> None:
    if os.environ.get("TSRPA_FAKE_UPDATE"):
        log.info("update.fake_apply", version=release.version)
        import time

        time.sleep(3)
        log.info("update.fake_exit")
        os._exit(0)

    current_exe = Path(sys.executable)
    setup_name = "TerminalServerRPA_Setup.exe"

    asset = next((a for a in release.assets if a["name"] == setup_name), None)
    if asset is None:
        log.error("update.asset_not_found", expected=setup_name, available=[a["name"] for a in release.assets])
        return

    dest = _download_asset(asset, current_exe.parent / setup_name, progress_cb)
    if dest is None:
        return

    if not _verify_checksum(dest, release):
        dest.unlink(missing_ok=True)
        log.error("update.aborted", reason="checksum_mismatch")
        return

    pid = os.getpid()
    batch = current_exe.parent / "_update.bat"
    batch.write_text(
        f"""@echo off
:wait
tasklist /FI "PID eq {pid}" 2>nul | find "{pid}" >nul
if not errorlevel 1 (
    timeout /t 2 /nobreak >nul
    goto wait
)
start /wait "" "{dest}" /SILENT
del /q "{dest}" 2>nul
del /q "%~f0"
start "" "{current_exe}" gui
""",
        encoding="utf-8",
    )

    log.info("update.scheduled", version=release.version, batch=str(batch))
    subprocess.Popen(
        ["cmd.exe", "/c", str(batch)],
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    os._exit(0)
