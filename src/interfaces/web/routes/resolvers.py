"""Formula resolver metadata + preview."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/resolvers")
async def get_resolvers():
    from src.automation.param_resolvers import resolver_meta

    return resolver_meta()


@router.post("/api/resolvers/preview")
async def preview_formula(data: dict):
    from src.automation.param_resolvers import _parse_formula

    formula = data.get("formula", "")
    result = _parse_formula(formula)
    return {"result": result}
