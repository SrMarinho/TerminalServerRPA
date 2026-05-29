import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from src.infrastructure.execution_manager import get_manager
from src.infrastructure.logger import get_logger
from src.infrastructure.single_instance import get_or_create_token
from src.infrastructure.task_config import load_config, save_config
from src.infrastructure.task_registry import TaskRegistry
from src.infrastructure.task_runner import get_pool
from src.infrastructure.vault import Vault
from src.interfaces.web.websocket import manager

router = APIRouter()
_vault = Vault()
_pool = get_pool()
_log = get_logger("TerminalServerRPA.router")

TEMPLATES_DIR = Path(__file__).parent / "templates"


def verify_token(authorization: str = "", token: str = ""):
    """Validate Bearer token from Authorization header or ?token= query param."""
    extracted = authorization.removeprefix("Bearer ")
    if not extracted:
        extracted = token
    actual = get_or_create_token()
    if not extracted or extracted != actual:
        raise HTTPException(401, "Unauthorized — invalid or missing API token")


# Separate router for /api/* routes with auth protection
api_router = APIRouter(prefix="", dependencies=[Depends(verify_token)])


@router.get("/", response_class=HTMLResponse)
async def index():
    import time

    token = get_or_create_token()
    html = (TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")
    html = html.replace("?v=AUTO", f"?v={int(time.time())}")
    html = html.replace(
        "</head>",
        f'<meta name="api-token" content="{token}">\n</head>',
    )
    return HTMLResponse(html)


@router.get("/_focus")
async def focus():
    return {"status": "focused"}


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    token = ws.query_params.get("token", "")
    if not token or token != get_or_create_token():
        await ws.close(code=1008)  # policy violation
        return
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_json()
            cmd = data.get("type")
            if cmd == "run":
                task_name = data.get("task_name", "")
                _pool.start(task_name)
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)


@api_router.get("/api/credentials")
async def list_credentials():
    services = _vault.list_services()
    result = []
    for svc in services:
        creds = _vault.list_credentials(svc)
        result.append({"service": svc, "usernames": [c["username"] for c in creds]})
    return result


@api_router.post("/api/credentials")
async def save_credential(data: dict):
    service: str = data.get("service") or ""
    username: str = data.get("username") or ""
    password: str = data.get("password") or ""
    if not service:
        raise HTTPException(400, "service required")
    if not username and not password:
        raise HTTPException(400, "username or password required")
    _vault.set_password(service, username, password)
    return {"status": "ok"}


@api_router.get("/api/credentials/{service}")
async def get_credential(service: str, username: str = ""):
    if not username:
        raise HTTPException(400, "username query param required")
    password = _vault.get_password(service, username)
    if password is None:
        raise HTTPException(404, "credential not found")
    return {"service": service, "username": username, "password": password}


@api_router.delete("/api/credentials/{service}")
async def delete_credential(service: str):
    _vault.delete_password(service)
    return {"status": "deleted"}


@api_router.get("/api/tasks")
async def list_tasks():
    TaskRegistry.auto_discover()
    return {"available": TaskRegistry.list()}


@api_router.get("/api/tasks/running")
async def list_running():
    return _pool.list_all()


@api_router.delete("/api/tasks/running")
async def cleanup_running():
    _pool.cleanup_done()
    return {"status": "cleaned"}


@api_router.post("/api/run/{task_name}")
async def run_task(task_name: str, data: dict | None = None):

    bps: list[str] = []
    params: dict | None = data
    if isinstance(data, dict) and "_breakpoints" in data:
        bps = data.pop("_breakpoints") or []
        params = data
    if params:
        save_config(task_name, params)
    try:
        task_id = _pool.start(task_name, params or None, bps)
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    return {"status": "started", "task": task_name, "task_id": task_id}


@api_router.get("/api/executions")
async def list_executions():
    return get_manager().list_all()


@api_router.get("/api/executions/{execution_id}")
async def get_execution(execution_id: str):
    exec_data = get_manager().get(execution_id)
    if exec_data is None:
        raise HTTPException(404, "execution not found")
    return exec_data


@api_router.get("/api/tasks/{task_name}/config")
async def get_task_config(task_name: str):
    return load_config(task_name)


@api_router.get("/api/tasks/{task_name}/schema")
async def get_task_schema(task_name: str):
    TaskRegistry.auto_discover()
    return TaskRegistry.get_schema(task_name)


@api_router.post("/api/tasks/{task_name}/config")
async def save_task_config(task_name: str, data: dict):
    save_config(task_name, data)
    return {"status": "saved"}


@api_router.post("/api/tasks/{task_id}/pause")
async def pause_task(task_id: str):
    runner = _pool.get(task_id)
    if not runner:
        raise HTTPException(404, "task not found")
    runner.pause()
    return {"status": "paused"}


@api_router.post("/api/tasks/{task_id}/resume")
async def resume_task(task_id: str):
    runner = _pool.get(task_id)
    if not runner:
        raise HTTPException(404, "task not found")
    runner.resume()
    return {"status": "resumed"}


@api_router.post("/api/tasks/{task_id}/skip")
async def skip_task_step(task_id: str):
    runner = _pool.get(task_id)
    if not runner:
        raise HTTPException(404, "task not found")
    runner.skip_step()
    return {"status": "skipped"}


@api_router.post("/api/executions/{exec_id}/breakpoint")
async def set_exec_breakpoint(exec_id: str, data: dict):
    from src.infrastructure.execution_manager import get_breakpoints, set_breakpoint

    set_breakpoint(exec_id, data["step"], data["enabled"])
    return {"breakpoints": get_breakpoints(exec_id)}


@api_router.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    runner = _pool.get(task_id)
    if not runner:
        raise HTTPException(404, "task not found")
    runner.cancel()
    return {"status": "cancelling"}


@api_router.post("/api/shutdown")
async def shutdown():
    _log.info("server.shutdown.requested")
    os._exit(0)


@api_router.get("/api/dev")
async def dev_mode():
    from src.config.settings import DEV_MODE

    return {"dev": DEV_MODE}


@api_router.post("/api/executions/{exec_id}/snippet")
async def run_snippet(exec_id: str, data: dict):
    import asyncio as _asyncio
    import traceback

    from src.config.settings import DEV_MODE

    if not DEV_MODE:
        raise HTTPException(403, "only available in dev mode")
    runner = _pool.get(exec_id)
    if not runner or not runner._page:
        raise HTTPException(404, "execution not running or page not available")
    code = data.get("code", "")
    output: list[str] = []
    import cv2 as _cv2  # type: ignore[import-untyped]
    import numpy as _np  # type: ignore[import-untyped]
    import pytesseract as _pytesseract  # type: ignore[import-untyped]

    from src.utils.image_match import find_text as _find_text

    globs: dict = {
        "page": runner._page,
        "asyncio": _asyncio,
        "cv2": _cv2,
        "np": _np,
        "numpy": _np,
        "pytesseract": _pytesseract,
        "find_text": _find_text,
        "print": lambda *a, **_: output.append(" ".join(str(x) for x in a)),
    }
    try:
        wrapped = "async def _snippet_main():\n" + "\n".join("    " + line for line in code.splitlines()) + "\n"
        exec(compile(wrapped, "<snippet>", "exec"), globs)  # noqa: S102
        await globs["_snippet_main"]()
    except Exception:
        return {"ok": False, "error": traceback.format_exc(), "output": output}
    return {"ok": True, "output": output}
