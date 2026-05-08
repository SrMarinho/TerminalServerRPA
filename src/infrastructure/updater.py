from dataclasses import dataclass
from pathlib import Path

import httpx

from src.infrastructure.logger import get_logger

log = get_logger("senior-rpa.updater")

REPO = "senior-rpa"
OWNER = "user"


@dataclass
class Release:
    tag_name: str
    html_url: str
    assets: list

    @property
    def version(self) -> str:
        return self.tag_name.lstrip("v")


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
        if release.version > current_version:
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
