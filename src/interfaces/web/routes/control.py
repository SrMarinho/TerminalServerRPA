"""Live execution control: pause / resume / skip / cancel / breakpoints."""

from fastapi import APIRouter, Depends, HTTPException

from src.infrastructure.task_runner import TaskPool, get_pool
from src.interfaces.web.schemas import BreakpointIn

router = APIRouter()


@router.post("/api/tasks/{task_id}/pause")
async def pause_task(task_id: str, pool: TaskPool = Depends(get_pool)):
    runner = pool.get(task_id)
    if not runner:
        raise HTTPException(404, "task not found")
    runner.pause()
    return {"status": "paused"}


@router.post("/api/tasks/{task_id}/resume")
async def resume_task(task_id: str, pool: TaskPool = Depends(get_pool)):
    runner = pool.get(task_id)
    if not runner:
        raise HTTPException(404, "task not found")
    runner.resume()
    return {"status": "resumed"}


@router.post("/api/tasks/{task_id}/skip")
async def skip_task_step(task_id: str, pool: TaskPool = Depends(get_pool)):
    runner = pool.get(task_id)
    if not runner:
        raise HTTPException(404, "task not found")
    runner.skip_step()
    return {"status": "skipped"}


@router.post("/api/executions/{exec_id}/breakpoint")
async def set_exec_breakpoint(exec_id: str, data: BreakpointIn):
    from src.infrastructure.execution_manager import get_breakpoints, set_breakpoint

    set_breakpoint(exec_id, data.step, data.enabled)
    return {"breakpoints": get_breakpoints(exec_id)}


@router.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str, pool: TaskPool = Depends(get_pool)):
    runner = pool.get(task_id)
    if not runner:
        raise HTTPException(404, "task not found")
    runner.cancel()
    return {"status": "cancelling"}
