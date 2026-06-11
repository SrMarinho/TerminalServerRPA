"""Dev-only endpoints: Python snippets against the live Playwright page + OCR.

Registered by the server only when DEV_MODE is on — the attack surface does
not exist in production builds.
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from src.infrastructure.task_runner import TaskPool, get_pool
from src.interfaces.web.schemas import SnippetIn

router = APIRouter()

_snippet_tasks: dict[str, asyncio.Task] = {}
_STANDALONE_SNIPPET_KEY = "__standalone__"


def _require_dev_mode() -> None:
    from src.config.settings import DEV_MODE

    if not DEV_MODE:  # defense in depth; dev router is also unregistered in prod
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


@router.post("/api/dev/snippet")
async def run_standalone_snippet(data: SnippetIn):
    _require_dev_mode()
    return await _exec_snippet(data.code, None, _STANDALONE_SNIPPET_KEY)


@router.delete("/api/dev/snippet", status_code=204)
async def cancel_standalone_snippet():
    _cancel_snippet(_STANDALONE_SNIPPET_KEY)


@router.delete("/api/executions/{exec_id}/snippet", status_code=204)
async def cancel_snippet(exec_id: str):
    _cancel_snippet(exec_id)


@router.post("/api/executions/{exec_id}/snippet")
async def run_snippet(exec_id: str, data: SnippetIn, pool: TaskPool = Depends(get_pool)):
    _require_dev_mode()
    runner = pool.get(exec_id)
    if not runner or not runner.page:
        raise HTTPException(404, "execution not running or page not available")
    return await _exec_snippet(data.code, runner.page, exec_id)


@router.post("/api/executions/{exec_id}/ocr")
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
