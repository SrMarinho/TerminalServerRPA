"""Live screenshot streaming for running executions.

Encapsulates what used to be four module-level dicts + loose functions in
task_runner. One ScreenshotManager owns its subscriber/task/cache state and
publishes frames through the infra event bus.
"""

import asyncio
import base64
from collections.abc import Callable
from typing import TYPE_CHECKING

from src.infrastructure.events import publish
from src.infrastructure.logger import get_logger

if TYPE_CHECKING:
    from playwright.async_api import Page

_log = get_logger("TerminalServerRPA.screenshot")

_POLL_INTERVAL = 0.25  # seconds between frame polls
_SCALE = 0.75  # downscale factor before JPEG encode
_JPEG_QUALITY = 88


class ScreenshotManager:
    def __init__(self, page_provider: Callable[[str], Page | None]):
        self._page_provider = page_provider
        self._subscribers: dict[str, int] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._last: dict[str, tuple[str, str]] = {}  # exec_id -> (mime, b64)
        self._last_hash: dict[str, int] = {}

    def subscribe(self, exec_id: str) -> None:
        self._subscribers[exec_id] = self._subscribers.get(exec_id, 0) + 1
        cached = self._last.get(exec_id)
        if cached:
            publish({"type": "execution:screenshot", "execution_id": exec_id, "data": cached[1], "mime": cached[0]})
        if exec_id not in self._tasks:
            self._tasks[exec_id] = asyncio.create_task(self._loop(exec_id))

    def unsubscribe(self, exec_id: str) -> None:
        count = self._subscribers.get(exec_id, 0) - 1
        if count <= 0:
            self._subscribers.pop(exec_id, None)
        else:
            self._subscribers[exec_id] = count

    async def _loop(self, exec_id: str) -> None:
        import cv2  # type: ignore[import-untyped]
        import numpy as np  # type: ignore[import-untyped]

        try:
            while self._subscribers.get(exec_id, 0) > 0:
                page = self._page_provider(exec_id)
                if page:
                    try:
                        raw = await page.screenshot()
                        h = hash(raw)
                        if h != self._last_hash.get(exec_id):
                            self._last_hash[exec_id] = h
                            img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
                            if img is None:
                                continue
                            ih, iw = img.shape[:2]
                            img = cv2.resize(
                                img, (int(iw * _SCALE), int(ih * _SCALE)), interpolation=cv2.INTER_LANCZOS4
                            )
                            ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, _JPEG_QUALITY])
                            if ok:
                                b64 = base64.b64encode(buf.tobytes()).decode()
                                self._last[exec_id] = ("image/jpeg", b64)
                                publish(
                                    {
                                        "type": "execution:screenshot",
                                        "execution_id": exec_id,
                                        "data": b64,
                                        "mime": "image/jpeg",
                                    }
                                )
                    except Exception as exc:
                        _log.warning("screenshot.error", error=str(exc))
                await asyncio.sleep(_POLL_INTERVAL)
        finally:
            self._tasks.pop(exec_id, None)
            self._last_hash.pop(exec_id, None)
            self._last.pop(exec_id, None)
