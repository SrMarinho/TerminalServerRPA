"""Route aggregator: composes the domain routers from routes/ into the three
routers the server mounts. Auth is applied once here (per router), so the
domain modules stay dependency-free.

Public surface (imported by server.py and tests):
  router      — unauthenticated shell (/, /_health, /_focus, /ws)
  api_router  — /api/* behind bearer auth
  dev_router  — dev-only /api/* (registered only when DEV_MODE is on)
"""

from fastapi import APIRouter, Depends

from src.infrastructure.task_runner import get_pool  # noqa: F401 — re-export for dependency overrides
from src.infrastructure.vault import get_vault  # noqa: F401 — re-export for dependency overrides
from src.interfaces.web.routes import control, credentials, dev, executions, resolvers, system, tasks, ui
from src.interfaces.web.routes.deps import verify_token

router = APIRouter()
router.include_router(ui.router)

api_router = APIRouter(dependencies=[Depends(verify_token)])
for _mod in (credentials, tasks, executions, control, resolvers, system):
    api_router.include_router(_mod.router)

dev_router = APIRouter(dependencies=[Depends(verify_token)])
dev_router.include_router(dev.router)
