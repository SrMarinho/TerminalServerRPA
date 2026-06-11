import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from src.infrastructure.execution_manager import get_manager
from src.infrastructure.logger import get_logger
from src.infrastructure.single_instance import get_or_create_token
from src.infrastructure.task_config import load_config, save_config
from src.infrastructure.task_registry import TaskRegistry
from src.infrastructure.task_runner import TaskPool, get_pool
from src.infrastructure.vault import Vault, get_vault
from src.interfaces.web.schemas import BreakpointIn, CredentialIn, SnippetIn
from src.interfaces.web.websocket import manager

router = APIRouter()
_log = get_logger("TerminalServerRPA.router")

TEMPLATES_DIR = Path(__file__).parent / "templates"


def verify_token(authorization: str = Header(default="")):
    """Validate the Bearer token from the Authorization header.

    Header-only on REST: query strings leak into history/proxies/logs more
    easily. The WebSocket handshake still uses ?token= (browsers cannot set
    headers on WS connections). compare_digest avoids timing side-channels.
    """
    import secrets

    extracted = authorization.removeprefix("Bearer ")
    actual = get_or_create_token()
    if not extracted or not secrets.compare_digest(extracted, actual):
        raise HTTPException(401, "Unauthorized — invalid or missing API token")


# Separate router for /api/* routes with auth protection
api_router = APIRouter(prefix="", dependencies=[Depends(verify_token)])

# Dev-only routes — included by the server only when DEV_MODE is enabled,
# so the attack surface does not exist at all in production builds.
dev_router = APIRouter(prefix="", dependencies=[Depends(verify_token)])


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
    import secrets

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
        from src.infrastructure.logger import get_logger

        get_logger("TerminalServerRPA.router").exception("ws.handler.error")
        manager.disconnect(ws)


@api_router.get("/api/credentials")
async def list_credentials(vault: Vault = Depends(get_vault)):
    services = vault.list_services()
    result = []
    for svc in services:
        creds = vault.list_credentials(svc)
        result.append({"service": svc, "usernames": [c["username"] for c in creds]})
    return result


@api_router.post("/api/credentials")
async def save_credential(data: CredentialIn, vault: Vault = Depends(get_vault)):
    vault.set_password(data.service, data.username, data.password)
    return {"status": "ok"}


@api_router.get("/api/credentials/{service}")
async def get_credential(service: str, username: str = "", vault: Vault = Depends(get_vault)):
    if not username:
        raise HTTPException(400, "username query param required")
    password = vault.get_password(service, username)
    if password is None:
        raise HTTPException(404, "credential not found")
    # Never return the raw password over HTTP — the UI never reads it, and
    # exposing it turns the API into a credential exfiltration vector.
    # The task runner fetches passwords directly from the OS keyring at
    # execution time using the service + username pair.
    return {"service": service, "username": username, "password": "***"}


@api_router.delete("/api/credentials/{service}")
async def delete_credential(service: str, vault: Vault = Depends(get_vault)):
    vault.delete_password(service)
    return {"status": "deleted"}


@api_router.get("/api/tasks")
async def list_tasks():
    return {"available": TaskRegistry.list()}


@api_router.get("/api/tasks/running")
async def list_running(pool: TaskPool = Depends(get_pool)):
    return pool.list_all()


@api_router.delete("/api/tasks/running")
async def cleanup_running(pool: TaskPool = Depends(get_pool)):
    pool.cleanup_done()
    return {"status": "cleaned"}


@api_router.post("/api/run/{task_name}")
async def run_task(task_name: str, data: dict | None = None, pool: TaskPool = Depends(get_pool)):
    bps: list[str] = []
    params: dict | None = data
    if isinstance(data, dict) and "_breakpoints" in data:
        bps = data.pop("_breakpoints") or []
        params = data
    if params:
        save_config(task_name, params)
    try:
        task_id = pool.start(task_name, params or None, bps)
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    return {"status": "started", "task": task_name, "task_id": task_id}


@api_router.get("/api/executions")
async def list_executions():
    return get_manager().list_all()


@api_router.get("/api/executions/{execution_id}")
async def get_execution(execution_id: str):
    from src.automation.param_resolvers import resolve_params

    exec_data = get_manager().get(execution_id)
    if exec_data is None:
        raise HTTPException(404, "execution not found")
    exec_data.params_display = resolve_params(exec_data.params)
    return exec_data


@api_router.get("/api/tasks/{task_name}/config")
async def get_task_config(task_name: str):
    return load_config(task_name)


@api_router.get("/api/tasks/{task_name}/schema")
async def get_task_schema(task_name: str):
    return TaskRegistry.get_schema(task_name)


@api_router.get("/api/resolvers")
async def get_resolvers():
    from src.automation.param_resolvers import resolver_meta

    return resolver_meta()


@api_router.post("/api/resolvers/preview")
async def preview_formula(data: dict):
    from src.automation.param_resolvers import _parse_formula

    formula = data.get("formula", "")
    result = _parse_formula(formula)
    return {"result": result}


@api_router.get("/api/tasks/{task_name}/form")
async def get_task_form(task_name: str, wrap_class: str = "", vault: Vault = Depends(get_vault)):
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    schema = TaskRegistry.get_schema(task_name)
    config = load_config(task_name) or {}
    creds = [{"service": s} for s in vault.list_services()]
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    html = env.get_template("form_fields.html").render(fields=schema, config=config, creds=creds, wrap_class=wrap_class)
    return {"html": html}


@api_router.post("/api/tasks/{task_name}/visibility")
async def get_field_visibility(task_name: str, data: dict):
    params = data.get("params", {})
    schema = TaskRegistry.get_schema(task_name)
    result = {}
    for field in schema:
        if "when" in field:
            conditions = field["when"]
            visible = all(str(params.get(k, "")) == str(v) for k, v in conditions.items())
            result[field["name"]] = visible
    return result


@api_router.post("/api/tasks/{task_name}/config")
async def save_task_config(task_name: str, data: dict):
    save_config(task_name, data)
    return {"status": "saved"}


@api_router.post("/api/tasks/{task_id}/pause")
async def pause_task(task_id: str, pool: TaskPool = Depends(get_pool)):
    runner = pool.get(task_id)
    if not runner:
        raise HTTPException(404, "task not found")
    runner.pause()
    return {"status": "paused"}


@api_router.post("/api/tasks/{task_id}/resume")
async def resume_task(task_id: str, pool: TaskPool = Depends(get_pool)):
    runner = pool.get(task_id)
    if not runner:
        raise HTTPException(404, "task not found")
    runner.resume()
    return {"status": "resumed"}


@api_router.post("/api/tasks/{task_id}/skip")
async def skip_task_step(task_id: str, pool: TaskPool = Depends(get_pool)):
    runner = pool.get(task_id)
    if not runner:
        raise HTTPException(404, "task not found")
    runner.skip_step()
    return {"status": "skipped"}


@api_router.post("/api/executions/{exec_id}/breakpoint")
async def set_exec_breakpoint(exec_id: str, data: BreakpointIn):
    from src.infrastructure.execution_manager import get_breakpoints, set_breakpoint

    set_breakpoint(exec_id, data.step, data.enabled)
    return {"breakpoints": get_breakpoints(exec_id)}


@api_router.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str, pool: TaskPool = Depends(get_pool)):
    runner = pool.get(task_id)
    if not runner:
        raise HTTPException(404, "task not found")
    runner.cancel()
    return {"status": "cancelling"}


@api_router.post("/api/shutdown")
async def shutdown(request: Request):
    _log.info("server.shutdown.requested")
    server = getattr(request.app.state, "server", None)
    if server is not None:
        server.should_exit = True  # triggers graceful uvicorn shutdown (lifespan cleanup)
        return {"status": "shutting down"}
    # Fallback when no uvicorn server is attached (e.g. tests)
    raise HTTPException(503, "server reference unavailable")


@api_router.post("/api/plugins/reload")
async def reload_plugins_endpoint():
    from src.infrastructure.plugin_loader import reload_plugins

    reloaded = reload_plugins()
    return {"reloaded": reloaded, "tasks": TaskRegistry.list()}


@api_router.get("/api/dev")
async def dev_mode():
    from src.config.settings import DEV_MODE

    return {"dev": DEV_MODE}


@api_router.post("/api/update")
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


_snippet_tasks: dict[str, asyncio.Task] = {}
_STANDALONE_SNIPPET_KEY = "__standalone__"


def _require_dev_mode() -> None:
    from src.config.settings import DEV_MODE

    if not DEV_MODE:  # defense in depth; dev_router is also unregistered in prod
        raise HTTPException(403, "only available in dev mode")


async def _exec_snippet(code: str, page, task_key: str) -> dict:
    """Compile and run a user snippet in a sandbox-ish namespace, tracking the task for cancellation."""
    import traceback
    from pathlib import Path as _Path

    import cv2 as _cv2  # type: ignore[import-untyped]
    import numpy as _np  # type: ignore[import-untyped]
    import pytesseract as _pytesseract  # type: ignore[import-untyped]

    from src.config.settings import ASSETS_DIR as _ASSETS_DIR
    from src.utils.image_match import find_template as _find_template
    from src.utils.image_match import find_text as _find_text

    output: list[str] = []
    globs: dict = {
        "page": page,
        "asyncio": asyncio,
        "cv2": _cv2,
        "np": _np,
        "numpy": _np,
        "pytesseract": _pytesseract,
        "find_text": _find_text,
        "find_template": _find_template,
        "ASSETS_DIR": _ASSETS_DIR,
        "Path": _Path,
        "print": lambda *a, **_: output.append(" ".join(str(x) for x in a)),
    }
    try:
        wrapped = "async def _snippet_main():\n" + "\n".join("    " + line for line in code.splitlines()) + "\n"
        exec(compile(wrapped, "<snippet>", "exec"), globs)  # noqa: S102
        task = asyncio.create_task(globs["_snippet_main"]())
        _snippet_tasks[task_key] = task
        try:
            await task
        except asyncio.CancelledError:
            return {"ok": False, "error": "abortado", "output": output}
    except Exception:
        return {"ok": False, "error": traceback.format_exc(), "output": output}
    finally:
        _snippet_tasks.pop(task_key, None)
    return {"ok": True, "output": output}


def _cancel_snippet(task_key: str) -> None:
    task = _snippet_tasks.get(task_key)
    if task and not task.done():
        task.cancel()


@dev_router.post("/api/dev/snippet")
async def run_standalone_snippet(data: SnippetIn):
    _require_dev_mode()
    return await _exec_snippet(data.code, None, _STANDALONE_SNIPPET_KEY)


@dev_router.delete("/api/dev/snippet", status_code=204)
async def cancel_standalone_snippet():
    _cancel_snippet(_STANDALONE_SNIPPET_KEY)


@dev_router.delete("/api/executions/{exec_id}/snippet", status_code=204)
async def cancel_snippet(exec_id: str):
    _cancel_snippet(exec_id)


@dev_router.post("/api/executions/{exec_id}/snippet")
async def run_snippet(exec_id: str, data: SnippetIn, pool: TaskPool = Depends(get_pool)):
    _require_dev_mode()
    runner = pool.get(exec_id)
    if not runner or not runner.page:
        raise HTTPException(404, "execution not running or page not available")
    return await _exec_snippet(data.code, runner.page, exec_id)


@dev_router.post("/api/executions/{exec_id}/ocr")
async def run_ocr(exec_id: str, pool: TaskPool = Depends(get_pool)):
    import io

    import pytesseract as _pytesseract  # type: ignore[import-untyped]
    from PIL import Image

    _require_dev_mode()
    runner = pool.get(exec_id)
    if not runner or not runner.page:
        raise HTTPException(404, "execution not running or page not available")
    raw = await runner.page.screenshot()
    img = Image.open(io.BytesIO(raw))
    text = _pytesseract.image_to_string(img, lang="por")
    return {"text": text}
