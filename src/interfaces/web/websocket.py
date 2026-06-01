import asyncio

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self._connections: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.add(ws)

    def disconnect(self, ws: WebSocket):
        self._connections.discard(ws)

    async def broadcast(self, event: dict):
        dead = set()
        for ws in self._connections:
            try:
                await ws.send_json(event)
            except Exception:
                from src.infrastructure.logger import get_logger

                get_logger("TerminalServerRPA.ws-broadcast").warning(
                    "broadcast.send_failed", event_type=event.get("type", "unknown")
                )
                dead.add(ws)
        self._connections -= dead

    @property
    def active_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()

_loop: asyncio.AbstractEventLoop | None = None


def broadcast_event(event: dict):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = _loop
    if loop is None:
        # No event loop available (e.g. CLI mode) — nothing to broadcast to.
        raise RuntimeError("no event loop available for broadcast")
    loop.call_soon_threadsafe(lambda: asyncio.create_task(manager.broadcast(event)))


async def broadcast_from_queue(queue: asyncio.Queue):
    global _loop
    _loop = asyncio.get_running_loop()
    while True:
        event = await queue.get()
        await manager.broadcast(event)
