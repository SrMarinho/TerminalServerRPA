"""Task catalog, configuration and execution start."""

from fastapi import APIRouter, Depends

from src.infrastructure.task_config import load_config, save_config
from src.infrastructure.task_registry import TaskRegistry
from src.infrastructure.task_runner import TaskPool, get_pool
from src.infrastructure.vault import Vault, get_vault
from src.interfaces.web.routes.deps import render_template

router = APIRouter()


@router.get("/api/tasks")
async def list_tasks():
    return {"available": TaskRegistry.list()}


@router.get("/api/tasks/running")
async def list_running(pool: TaskPool = Depends(get_pool)):
    return pool.list_all()


@router.delete("/api/tasks/running")
async def cleanup_running(pool: TaskPool = Depends(get_pool)):
    pool.cleanup_done()
    return {"status": "cleaned"}


@router.post("/api/run/{task_name}")
async def run_task(task_name: str, data: dict | None = None, pool: TaskPool = Depends(get_pool)):
    bps: list[str] = []
    params: dict | None = data
    if isinstance(data, dict) and "_breakpoints" in data:
        bps = data.pop("_breakpoints") or []
        params = data
    if params:
        save_config(task_name, params)
    result = pool.start_or_enqueue(task_name, params or None, bps)
    if result["queued"]:
        return {"status": "queued", "task": task_name, "position": result["position"]}
    return {"status": "started", "task": task_name, "task_id": result["task_id"]}


@router.get("/api/tasks/queue")
async def list_queue(pool: TaskPool = Depends(get_pool)):
    return {"queue": pool.queue_info()}


@router.get("/api/tasks/{task_name}/config")
async def get_task_config(task_name: str):
    return load_config(task_name)


@router.get("/api/tasks/{task_name}/schema")
async def get_task_schema(task_name: str):
    return TaskRegistry.get_schema(task_name)


@router.get("/api/tasks/{task_name}/form")
async def get_task_form(task_name: str, wrap_class: str = "", panel: str = "", vault: Vault = Depends(get_vault)):
    schema = TaskRegistry.get_schema(task_name)
    if panel:
        schema = [f for f in schema if f.get("group_panel", "inline") == panel]
    config = load_config(task_name) or {}
    creds = [{"service": s} for s in vault.list_services()]
    html = render_template("form_fields.html", fields=schema, config=config, creds=creds, wrap_class=wrap_class)
    return {"html": html}


@router.post("/api/tasks/{task_name}/visibility")
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


@router.post("/api/tasks/{task_name}/config")
async def save_task_config(task_name: str, data: dict):
    save_config(task_name, data)
    return {"status": "saved"}
