from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient

from app.main import app as fastapi_app
from app.routes.status import active_clients, broadcast_status
from app.schemas.ocr import GraphBroadCast, PageStatus

# -----------------------------------------------------------
# GET /status/sample
# -----------------------------------------------------------


@pytest.mark.asyncio
async def test_status_sample(authed_client_session: AsyncClient):
    resp = await authed_client_session.get("/api/v1/status/sample")
    assert resp.status_code == 200
    body = resp.json()

    assert body["type"] == "processing"
    assert body["id"] == "abc123"
    assert body["status"] == "APPROVED"


# -----------------------------------------------------------
# WebSocket connection test
# -----------------------------------------------------------


def test_status_websocket_connect_and_ping():
    """
    Uses TestClient (sync) because httpx.AsyncClient does not support WS.
    TestClient fully supports WS and your ASGITransport works fine with it.
    """
    client = TestClient(fastapi_app)

    with client.websocket_connect("/api/v1/ws/status") as ws:
        # First message should be the ping loop
        msg = ws.receive_text()
        assert msg == '{"message": "ping"}'

        # Ensure in active_clients
        assert len(active_clients) == 1

    # After exiting context manager ws is closed → removed from active_clients
    assert len(active_clients) == 0


# -----------------------------------------------------------
# broadcast_status() tests
# -----------------------------------------------------------


@pytest.mark.asyncio
async def test_broadcast_status_sends_to_clients(monkeypatch):
    """
    Verify that broadcast_status() loops through active_clients
    and calls send_text() with expected JSON.
    """

    # Fake WebSocket with send_text()
    fake_ws = AsyncMock()
    fake_ws.send_text = AsyncMock()

    active_clients.add(fake_ws)

    msg = GraphBroadCast(type="ok", id="123", status=PageStatus.APPROVED)
    await broadcast_status(msg)

    expected_json = msg.model_dump_json()
    fake_ws.send_text.assert_awaited_once_with(expected_json)

    active_clients.clear()


@pytest.mark.asyncio
async def test_broadcast_status_removes_dead_clients(monkeypatch):
    """
    If send_text raises RuntimeError, client should be removed.
    """

    fake_ws = AsyncMock()
    fake_ws.send_text = AsyncMock(side_effect=RuntimeError("ws closed"))

    active_clients.add(fake_ws)

    msg = GraphBroadCast(type="x", id="y", status=PageStatus.APPROVED)
    await broadcast_status(msg)

    # Verify it was removed
    assert fake_ws not in active_clients

    active_clients.clear()
