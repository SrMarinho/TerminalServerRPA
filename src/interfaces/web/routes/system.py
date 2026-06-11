"""Server lifecycle: shutdown, plugin reload, dev flag, on-demand update."""

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from src.infrastructure.logger import get_logger
from src.infrastructure.task_registry import TaskRegistry

router = APIRouter()
_log = get_logger("TerminalServerRPA.router")


@router.get("/api/fs/dirs")
async def list_dirs(prefix: str = ""):
    """Return subdirectories of a path prefix for autocomplete."""
    try:
        prefix = prefix.strip()
        if not prefix:
            # Return drive roots on Windows, home on others
            if os.name == "nt":
                import string

                drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
                return {"dirs": drives}
            return {"dirs": [str(Path.home())]}

        p = Path(prefix)
        # If prefix ends with separator (or is exact dir), list children
        if prefix.endswith(("\\", "/")) or p.is_dir():
            base = p if p.is_dir() else p.parent
            partial = ""
        else:
            base = p.parent
            partial = p.name.lower()

        if not base.exists():
            return {"dirs": []}

        entries = []
        try:
            for child in sorted(base.iterdir()):
                if not child.is_dir():
                    continue
                if child.name.startswith("."):
                    continue
                if partial and not child.name.lower().startswith(partial):
                    continue
                entries.append(str(child))
                if len(entries) >= 20:
                    break
        except PermissionError:
            pass

        return {"dirs": entries}
    except Exception:
        return {"dirs": []}


@router.post("/api/shutdown")
async def shutdown(request: Request):
    _log.info("server.shutdown.requested")
    server = getattr(request.app.state, "server", None)
    if server is not None:
        server.should_exit = True  # triggers graceful uvicorn shutdown (lifespan cleanup)
        return {"status": "shutting down"}
    # Fallback when no uvicorn server is attached (e.g. tests)
    raise HTTPException(503, "server reference unavailable")


@router.post("/api/plugins/reload")
async def reload_plugins_endpoint():
    from src.infrastructure.plugin_loader import reload_plugins

    reloaded = reload_plugins()
    return {"reloaded": reloaded, "tasks": TaskRegistry.list()}


@router.get("/api/dev")
async def dev_mode():
    from src.config.settings import DEV_MODE

    return {"dev": DEV_MODE}


@router.post("/api/update")
async def trigger_update():
    """Download and apply the latest release, then restart."""
    import sys
    from pathlib import Path

    from src.config.version import VERSION
    from src.infrastructure.updater import apply_update, check_for_update

    release = check_for_update(VERSION)
    if release is None:
        return {"status": "up_to_date", "version": VERSION}

    current_exe = Path(sys.executable)
    if current_exe.suffix != ".exe" or "TerminalServerRPA" not in current_exe.name:
        return {"status": "skipped", "reason": "not a packaged build (dev mode)"}

    apply_update(release)
    # apply_update calls sys.exit(0) — never reaches here
    return {"status": "restarting"}
