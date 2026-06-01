from unittest.mock import AsyncMock

import pytest


class TestConnectionManager:
    @pytest.mark.asyncio
    async def test_connect_accepts_and_adds(self):
        from src.interfaces.web.websocket import ConnectionManager

        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect(ws)
        ws.accept.assert_awaited_once()
        assert mgr.active_count == 1

    @pytest.mark.asyncio
    async def test_disconnect_removes(self):
        from src.interfaces.web.websocket import ConnectionManager

        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect(ws)
        mgr.disconnect(ws)
        assert mgr.active_count == 0

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all(self):
        from src.interfaces.web.websocket import ConnectionManager

        mgr = ConnectionManager()
        ws1, ws2 = AsyncMock(), AsyncMock()
        await mgr.connect(ws1)
        await mgr.connect(ws2)
        await mgr.broadcast({"event": "test"})
        ws1.send_json.assert_awaited_once_with({"event": "test"})
        ws2.send_json.assert_awaited_once_with({"event": "test"})

    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_connections(self):
        from src.interfaces.web.websocket import ConnectionManager

        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws2.send_json.side_effect = Exception("gone")
        await mgr.connect(ws1)
        await mgr.connect(ws2)
        await mgr.broadcast({"event": "test"})
        assert mgr.active_count == 1

    def test_active_count_starts_zero(self):
        from src.interfaces.web.websocket import ConnectionManager

        assert ConnectionManager().active_count == 0
