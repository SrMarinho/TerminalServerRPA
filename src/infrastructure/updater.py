from dataclasses import dataclass
from pathlib import Path

import httpx

from src.infrastructure.logger import get_logger

log = get_logger("TerminalServerRPA.updater")

REPO = "TerminalServerRPA"
OWNER = "SrMarinho"


@dataclass
class Release:
    tag_name: str
    html_url: str
    assets: list

    @property
    def version(self) -> str:
        return self.tag_name.lstrip("v")


def _parse_version(v: str) -> tuple[int, ...]:
    parts = []
    for chunk in v.split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def check_for_update(current_version: str) -> Release | None:
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
    try:
        resp = httpx.get(url, timeout=10)
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


def download_asset(asset_name: str, dest_dir: Path) -> Path | None:
    url = f"https://github.com/{OWNER}/{REPO}/releases/latest/download/{asset_name}"
    dest = dest_dir / asset_name
    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=120) as resp:
            resp.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)
        log.info("update.downloaded", path=str(dest))
        return dest
    except Exception as e:
        log.error("update.download_failed", error=str(e))
    return None


def apply_update(current_exe: Path, new_exe: Path) -> None:
    """Download the latest release and schedule a hot-swap via the updater executable.

    1. Download the new EXE into the parent directory of the running EXE.
    2. Write a one-shot batch script that waits for the parent process to
       exit, replaces the EXE, restarts it, then self-destructs.
    3. Launch the batch script detached so it survives this process exit.
    """
    import os
    import subprocess
    import sys

    dest = download_asset(current_exe.name, current_exe.parent)
    if dest is None:
        return

    batch = current_exe.parent / "_update.bat"
    batch.write_text(
        f"""@echo off
rem Wait for the parent process to exit (up to 30s).
:wait
tasklist /FI "PID eq {os.getpid()}" 2>nul | find "{os.getpid()}" >nul
if not errorlevel 1 (
    timeout /t 2 /nobreak >nul
    goto wait
)
rem Replace the running EXE with the downloaded one.
copy /y "{dest}" "{current_exe}" >nul
rem Restart.
start "" "{current_exe}"
rem Clean up.
del /q "{dest}" "%~f0"
""",
        encoding="utf-8",
    )

    log.info("update.scheduled", batch=str(batch))
    subprocess.Popen(
        ["cmd.exe", "/c", str(batch)],
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    sys.exit(0)
