import hashlib
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx

from src.infrastructure.logger import get_logger

log = get_logger("TerminalServerRPA.updater")

REPO = "TerminalServerRPA"
OWNER = "SrMarinho"
GITHUB_TOKEN = ""  # Fine-grained PAT: Contents: Read-only


@dataclass
class Release:
    tag_name: str
    html_url: str
    assets: list

    @property
    def version(self) -> str:
        return self.tag_name.lstrip("v")


def _auth_headers() -> dict:
    if not GITHUB_TOKEN:
        return {}
    return {"Authorization": f"Bearer {GITHUB_TOKEN}"}


def _parse_version(v: str) -> tuple[int, ...]:
    parts = []
    for chunk in v.split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def check_for_update(current_version: str) -> Release | None:
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
    try:
        resp = httpx.get(url, headers=_auth_headers(), timeout=10)
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


def _download_asset(asset: dict, dest: Path) -> Path | None:
    headers = {**_auth_headers(), "Accept": "application/octet-stream"}
    try:
        with httpx.stream("GET", asset["url"], headers=headers, follow_redirects=True, timeout=120) as resp:
            resp.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)
        log.info("update.downloaded", path=str(dest))
        return dest
    except Exception as e:
        log.error("update.download_failed", asset=asset.get("name"), error=str(e))
    return None


def _verify_checksum(file: Path, release: Release) -> bool:
    exe_name = file.name
    checksum_asset = next((a for a in release.assets if a["name"] == f"{exe_name}.sha256"), None)
    if checksum_asset is None:
        return True  # no checksum asset → skip

    tmp = file.parent / f"{exe_name}.sha256_tmp"
    downloaded = _download_asset(checksum_asset, tmp)
    if downloaded is None:
        return True  # can't download checksum → skip

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


def apply_update(release: Release) -> None:
    current_exe = Path(sys.executable)
    setup_name = "TerminalServerRPA_Setup.exe"

    asset = next((a for a in release.assets if a["name"] == setup_name), None)
    if asset is None:
        log.error("update.asset_not_found", expected=setup_name, available=[a["name"] for a in release.assets])
        return

    dest = _download_asset(asset, current_exe.parent / setup_name)
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
start /wait "" "{dest}" /VERYSILENT /SUPPRESSMSGBOXES
del /q "{dest}" 2>nul
del /q "%~f0"
""",
        encoding="utf-8",
    )

    log.info("update.scheduled", version=release.version, batch=str(batch))
    subprocess.Popen(
        ["cmd.exe", "/c", str(batch)],
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    sys.exit(0)
