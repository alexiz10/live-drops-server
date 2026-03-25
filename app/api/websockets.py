import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from redis.asyncio import Redis

from app.core.websocket import manager
from app.core.cache import get_redis

router = APIRouter(tags=["WebSockets"])

@router.websocket("/auctions/{auction_id}/ws")
async def auction_websocket_endpoint(
        websocket: WebSocket,
        auction_id: uuid.UUID,
        redis_client: Redis = Depends(get_redis)
):
    await manager.connect(websocket, auction_id)

    try:
        current_price = await redis_client.get(f"auction:{auction_id}:price")

        if current_price:
            await websocket.send_json({
                "event": "new_highest_bid",
                "new_price": current_price,
                "bidder_id": None
            })

        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, auction_id)
