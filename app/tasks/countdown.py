import asyncio
from datetime import datetime, timezone

from app.core.websocket import manager
from app.core.cache import redis_client

async def auction_countdown_broadcaster():
    """
    Background task that runs every second.
    It checks all active WebSocket rooms and broadcasts the remaining time.
    """
    try:
        while True:
            await asyncio.sleep(1)

            active_auction_ids = list(manager.active_connections.keys())

            if not active_auction_ids:
                continue

            async with redis_client.pipeline() as pipe:
                for auction_id in active_auction_ids:
                    pipe.get(f"auction:{auction_id}:end_time")
                end_times_str = await pipe.execute()

            now = datetime.now(timezone.utc)

            for auction_id, end_time_str in zip(active_auction_ids, end_times_str):
                if not end_time_str:
                    continue

                end_time = datetime.fromisoformat(end_time_str)
                remaining_seconds = (end_time - now).total_seconds()

                if remaining_seconds <= 0:
                    await manager.broadcast_to_auction(
                        auction_id,
                        {"event": "auction_ended", "time_remaining": 0}
                    )
                else:
                    await manager.broadcast_to_auction(
                        auction_id,
                        {"event": "time_update", "time_remaining": int(remaining_seconds)}
                    )
    except asyncio.CancelledError:
        # This catches the cancellation signal when the server is shutting down
        # so it exits cleanly without throwing an error in the console.
        pass