import asyncio
import logging

from fastapi import APIRouter
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.schemas.ocr import GraphBroadCast, PageStatus

router = APIRouter()

active_clients: set[WebSocket] = set()

logger = logging.getLogger(__name__)


@router.get("/status/sample", response_model=GraphBroadCast)
async def get_sample_status():
    # Return a sample or dummy response
    return GraphBroadCast(type="processing", id="abc123", status=PageStatus.APPROVED)


@router.websocket("/ws/status")
async def status_ws(ws: WebSocket):
    await ws.accept()
    active_clients.add(ws)
    logger.debug(f"🟢 WebSocket connected. Total: {len(active_clients)}")

    try:
        while True:
            await ws.send_text('{"message": "ping"}')  # keep it active and test connection
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        logger.debug("🔴 WebSocket disconnected")
    except Exception as e:
        logger.debug(f"⚠️ WebSocket error: {e}")
    finally:
        active_clients.discard(ws)
        logger.debug(f"🧹 Cleaned up socket. Total: {len(active_clients)}")


async def broadcast_status(message: GraphBroadCast):
    data = message.model_dump_json()
    for ws in list(active_clients):  # copy to avoid mutation issues
        try:
            await ws.send_text(data)
        except RuntimeError:
            active_clients.discard(ws)
