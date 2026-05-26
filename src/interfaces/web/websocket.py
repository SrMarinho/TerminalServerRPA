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
                dead.add(ws)
        self._connections -= dead

    @property
    def active_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()


def broadcast_event(event: dict):
    loop = asyncio.get_event_loop()
    loop.call_soon_threadsafe(
        lambda: asyncio.create_task(manager.broadcast(event))
    )


async def broadcast_from_queue(queue: asyncio.Queue):
    while True:
        event = await queue.get()
        await manager.broadcast(event)
