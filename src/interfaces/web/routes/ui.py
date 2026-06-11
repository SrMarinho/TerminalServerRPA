"""UI shell, health/focus probes and the WebSocket endpoint (no-auth router;
the WS authenticates itself during the handshake)."""

import secrets
import time

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from src.infrastructure.logger import get_logger
from src.infrastructure.single_instance import get_or_create_token
from src.infrastructure.task_registry import TaskRegistry
from src.infrastructure.task_runner import get_pool
from src.interfaces.web.routes.deps import render_template
from src.interfaces.web.websocket import manager

router = APIRouter()
_log = get_logger("TerminalServerRPA.router")


@router.get("/", response_class=HTMLResponse)
async def index():
    html = render_template(
        "index.html",
        api_token=get_or_create_token(),
        cache_bust=int(time.time()),
    )
    return HTMLResponse(html)


@router.get("/_health")
async def health():
    return {"status": "ok"}


@router.get("/_focus")
async def focus(request: Request):
    window = getattr(request.app.state, "window", None)
    if window is not None:
        window.show()
    return {"status": "focused"}


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    token = ws.query_params.get("token", "")
    if not token or not secrets.compare_digest(token, get_or_create_token()):
        await ws.close(code=1008)  # policy violation
        return
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_json()
            cmd = data.get("type")
            if cmd == "run":
                task_name = data.get("task_name", "")
                if not task_name:
                    await ws.send_json({"type": "error", "message": "task_name required"})
                    continue
                TaskRegistry.auto_discover()
                if TaskRegistry.get(task_name) is None:
                    await ws.send_json({"type": "error", "message": f"Unknown task: {task_name}"})
                    continue
                try:
                    get_pool().start(task_name)
                except RuntimeError as e:
                    await ws.send_json({"type": "error", "message": str(e)})
            elif cmd == "screenshot:subscribe":
                exec_id = data.get("execution_id", "")
                # Validate the execution exists, otherwise the manager would
                # spin a polling loop for a bogus id until unsubscribe.
                if exec_id and get_pool().get(exec_id) is not None:
                    from src.infrastructure.task_runner import subscribe_screenshot

                    subscribe_screenshot(exec_id)
            elif cmd == "screenshot:unsubscribe":
                exec_id = data.get("execution_id", "")
                if exec_id:
                    from src.infrastructure.task_runner import unsubscribe_screenshot

                    unsubscribe_screenshot(exec_id)
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        _log.exception("ws.handler.error")
        manager.disconnect(ws)
