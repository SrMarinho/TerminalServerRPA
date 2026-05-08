import asyncio
import os
import webbrowser
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from src.infrastructure.logger import get_logger
from src.infrastructure.task_runner import TaskStatus, get_runner
from src.infrastructure.vault import Vault
from src.interfaces.web.websocket import manager

router = APIRouter()
_vault = Vault()
_runner = get_runner()
_log = get_logger("senior-rpa.router")

TEMPLATES_DIR = Path(__file__).parent / "templates"


@router.get("/", response_class=HTMLResponse)
async def index():
    html = (TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@router.get("/_focus")
async def focus():
    webbrowser.open("http://127.0.0.1:8080")
    return {"status": "focused"}


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_json()
            cmd = data.get("type")
            if cmd == "pause":
                _runner.pause()
            elif cmd == "resume":
                _runner.resume()
            elif cmd == "cancel":
                _runner.cancel()
            elif cmd == "run":
                task_name = data.get("task_name", "")
                if _runner.status != TaskStatus.RUNNING:
                    asyncio.create_task(_runner.run(task_name))
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
    if not service or not username or not password:
        raise HTTPException(400, "service, username, password required")
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
    return {
        "available": ["bulk-register-users"],
        "current_status": _runner.status.value,
    }


@router.post("/api/run/{task_name}")
async def run_task(task_name: str):
    if _runner.status == TaskStatus.RUNNING:
        raise HTTPException(409, "task already running")
    asyncio.create_task(_runner.run(task_name))
    return {"status": "started", "task": task_name}


@router.post("/api/tasks/pause")
async def pause_task():
    _runner.pause()
    return {"status": "paused"}


@router.post("/api/tasks/resume")
async def resume_task():
    _runner.resume()
    return {"status": "resumed"}


@router.post("/api/tasks/cancel")
async def cancel_task():
    _runner.cancel()
    return {"status": "cancelling"}


@router.post("/api/shutdown")
async def shutdown():
    _log.info("server.shutdown.requested")
    os._exit(0)
