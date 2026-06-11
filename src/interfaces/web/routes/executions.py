"""Execution history endpoints."""

from fastapi import APIRouter, HTTPException

from src.infrastructure.execution_manager import get_manager

router = APIRouter()


@router.get("/api/executions")
async def list_executions():
    return get_manager().list_all()


@router.get("/api/executions/{execution_id}")
async def get_execution(execution_id: str):
    from src.automation.param_resolvers import resolve_params
    from src.infrastructure.execution_manager import get_breakpoints

    exec_data = get_manager().get(execution_id)
    if exec_data is None:
        raise HTTPException(404, "execution not found")
    exec_data.params_display = resolve_params(exec_data.params)
    result = exec_data.model_dump()
    result["breakpoints"] = get_breakpoints(execution_id)
    return result
