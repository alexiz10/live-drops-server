import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.websocket import manager

router = APIRouter(tags=["WebSockets"])

@router.websocket("/auctions/{auction_id}/ws")
async def auction_websocket_endpoint(websocket: WebSocket, auction_id: uuid.UUID):
    await manager.connect(websocket, auction_id)

    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, auction_id)
