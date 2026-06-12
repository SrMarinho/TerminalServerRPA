import asyncio
from dataclasses import dataclass
from pathlib import Path

from .pages.reports.constants import FormatoArquivo

_EXT_MAP = {
    FormatoArquivo.EXCEL: ".xls",
    FormatoArquivo.EXCEL_OPENXML: ".xlsx",
    FormatoArquivo.CSV: ".csv",
    FormatoArquivo.EXPORTACAO_EXCEL: ".xls",
}
_DOWNLOAD_SUFFIXES = {".xls", ".xlsx", ".csv", ".pdf"}


@dataclass
class OutputConfig:
    downloads_path: Path
    nome_arquivo: str
    fmt: str

    @property
    def ext(self) -> str:
        return _EXT_MAP.get(self.fmt, ".xls")

    @property
    def dest(self) -> Path:
        return self.downloads_path / (self.nome_arquivo + self.ext)


class DownloadManager:
    def __init__(self, output: OutputConfig, log=None):
        self._output = output
        self._log = log or (lambda m: None)

    async def configure_cdp(self, context, page) -> None:
        cdp = await context.new_cdp_session(page)
        await cdp.send(
            "Browser.setDownloadBehavior", {"behavior": "allow", "downloadPath": str(self._output.downloads_path)}
        )
        await cdp.detach()

    async def wait_for_file(self, timeout_s: int = 600) -> Path:
        import time

        dest = self._output.dest
        # Chrome ignores CDP setDownloadBehavior for TS-proxied downloads;
        # files land in the OS default Downloads folder instead.
        chrome_downloads = Path.home() / "Downloads"
        search_dirs = [self._output.downloads_path, chrome_downloads]
        start_time = time.time()
        self._log(f"download.waiting: dest={dest!r} watching={[str(d) for d in search_dirs]}")

        for i in range(timeout_s):
            for search_dir in search_dirs:
                if not search_dir.exists():
                    continue
                candidates = [
                    p
                    for p in search_dir.iterdir()
                    if not p.name.endswith(".crdownload")
                    and not p.name.endswith(".tmp")
                    and p.is_file()
                    and p.stat().st_size > 0
                    and p.stat().st_mtime >= start_time - 5
                ]
                if candidates:
                    newest = max(candidates, key=lambda p: p.stat().st_mtime)
                    self._log(f"download.found: file={newest!r}")
                    self._output.downloads_path.mkdir(parents=True, exist_ok=True)
                    newest.rename(dest)
                    size = dest.stat().st_size if dest.exists() else -1
                    self._log(f"download.saved: path={dest!r} size={size}B")
                    return dest
            if i % 10 == 0:
                self._log(f"download.poll[{i}]: still waiting")
            await asyncio.sleep(1)

        size = dest.stat().st_size if dest.exists() else -1
        self._log(f"download.timeout: path={dest!r} size={size}B")
        return dest
