"""Recurring schedule endpoints (cron per task)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.infrastructure.schedule_manager import get_schedule_manager
from src.infrastructure.task_registry import TaskRegistry

router = APIRouter()


class ScheduleIn(BaseModel):
    task_name: str = Field(min_length=1)
    cron: str = Field(min_length=9)  # shortest valid crontab: "* * * * *"


class ScheduleToggle(BaseModel):
    enabled: bool


@router.get("/api/schedules")
async def list_schedules():
    return get_schedule_manager().list_all()


@router.post("/api/schedules")
async def create_schedule(data: ScheduleIn):
    if TaskRegistry.get(data.task_name) is None:
        raise HTTPException(404, f"Unknown task: {data.task_name}")
    try:
        return get_schedule_manager().create(data.task_name, data.cron)
    except ValueError as e:
        raise HTTPException(422, f"invalid cron expression: {e}")


@router.delete("/api/schedules/{schedule_id}", status_code=204)
async def delete_schedule(schedule_id: int):
    if not get_schedule_manager().delete(schedule_id):
        raise HTTPException(404, "schedule not found")


@router.patch("/api/schedules/{schedule_id}")
async def toggle_schedule(schedule_id: int, data: ScheduleToggle):
    if not get_schedule_manager().set_enabled(schedule_id, data.enabled):
        raise HTTPException(404, "schedule not found")
    return {"id": schedule_id, "enabled": data.enabled}
