import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from src.infrastructure.execution_manager import get_manager
from src.infrastructure.logger import get_logger
from src.infrastructure.task_config import load_config, save_config
from src.infrastructure.task_registry import TaskRegistry
from src.infrastructure.task_runner import get_pool
from src.infrastructure.vault import Vault
from src.interfaces.web.websocket import manager

router = APIRouter()
_vault = Vault()
_pool = get_pool()
_log = get_logger("senior-rpa.router")

TEMPLATES_DIR = Path(__file__).parent / "templates"


@router.get("/", response_class=HTMLResponse)
async def index():
    import time
    html = (TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")
    html = html.replace("?v=AUTO", f"?v={int(time.time())}")
    return HTMLResponse(html)


@router.get("/_focus")
async def focus():
    return {"status": "focused"}


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
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


@router.get("/api/credentials")
async def list_credentials():
    services = _vault.list_services()
    result = []
    for svc in services:
        creds = _vault.list_credentials(svc)
        result.append({"service": svc, "usernames": [c["username"] for c in creds]})
    return result


@router.post("/api/credentials")
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


@router.get("/api/credentials/{service}")
async def get_credential(service: str, username: str = ""):
    if not username:
        raise HTTPException(400, "username query param required")
    password = _vault.get_password(service, username)
    if password is None:
        raise HTTPException(404, "credential not found")
    return {"service": service, "username": username, "password": password}


@router.delete("/api/credentials/{service}")
async def delete_credential(service: str):
    _vault.delete_password(service)
    return {"status": "deleted"}


@router.get("/api/tasks")
async def list_tasks():
    TaskRegistry.auto_discover()
    return {"available": TaskRegistry.list()}


@router.get("/api/tasks/running")
async def list_running():
    return _pool.list_all()


@router.delete("/api/tasks/running")
async def cleanup_running():
    _pool.cleanup_done()
    return {"status": "cleaned"}


@router.post("/api/run/{task_name}")
async def run_task(task_name: str, data: dict | None = None):
    if data:
        save_config(task_name, data)
    task_id = _pool.start(task_name, data or None)
    return {"status": "started", "task": task_name, "task_id": task_id}


@router.get("/api/executions")
async def list_executions():
    return get_manager().list_all()


@router.get("/api/executions/{execution_id}")
async def get_execution(execution_id: str):
    exec_data = get_manager().get(execution_id)
    if exec_data is None:
        raise HTTPException(404, "execution not found")
    return exec_data
@router.get("/api/tasks/{task_name}/config")
async def get_task_config(task_name: str):
    return load_config(task_name)


@router.get("/api/tasks/{task_name}/schema")
async def get_task_schema(task_name: str):
    TaskRegistry.auto_discover()
    return TaskRegistry.get_schema(task_name)


@router.post("/api/tasks/{task_name}/config")
async def save_task_config(task_name: str, data: dict):
    save_config(task_name, data)
    return {"status": "saved"}


@router.post("/api/tasks/{task_id}/pause")
async def pause_task(task_id: str):
    runner = _pool.get(task_id)
    if not runner:
        raise HTTPException(404, "task not found")
    runner.pause()
    return {"status": "paused"}


@router.post("/api/tasks/{task_id}/resume")
async def resume_task(task_id: str):
    runner = _pool.get(task_id)
    if not runner:
        raise HTTPException(404, "task not found")
    runner.resume()
    return {"status": "resumed"}


@router.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    runner = _pool.get(task_id)
    if not runner:
        raise HTTPException(404, "task not found")
    runner.cancel()
    return {"status": "cancelling"}


@router.post("/api/shutdown")
async def shutdown():
    _log.info("server.shutdown.requested")
    os._exit(0)
