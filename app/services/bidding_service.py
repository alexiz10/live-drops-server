import uuid
from datetime import datetime, timezone
from decimal import Decimal
from redis.asyncio import Redis
from redis.exceptions import WatchError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select

from app.core.websocket import manager
from app.models import Bid, Auction, User
from app.schemas.auction import mask_email

class BiddingService:
    def __init__(self, redis_client: Redis, db_session: AsyncSession):
        self.redis = redis_client
        self.db = db_session

    async def place_bid(self, auction_id: uuid.UUID, user_id: uuid.UUID, user_email: str, bid_amount: Decimal) -> bool:
        """
        Attempts to place a bid using Redis Optimistic Locking.
        Returns True if successful, False if outbid or the bid is too low.
        """
        safe_email = mask_email(user_email)

        price_key = f"auction:{auction_id}:price"
        bidder_key = f"auction:{auction_id}:bidder"
        bidder_email_key = f"auction:{auction_id}:bidder_email"

        async with self.redis.pipeline() as pipe:
            try:
                await pipe.watch(price_key)

                current_price_str = await pipe.get(price_key)
                current_price = Decimal(current_price_str) if current_price_str else Decimal("0.00")

                if bid_amount <= current_price:
                    await pipe.unwatch()
                    return False

                end_time_str = await self.redis.get(f"auction:{auction_id}:end_time")
                if end_time_str:
                    end_time = datetime.fromisoformat(end_time_str)
                    if datetime.now(timezone.utc) >= end_time:
                        await pipe.unwatch()
                        return False

                pipe.multi()

                await pipe.set(price_key, str(bid_amount))
                await pipe.set(bidder_key, str(user_id))
                await pipe.set(bidder_email_key, safe_email)

                await pipe.execute()

                new_bid = Bid(
                    auction_id=auction_id,
                    bidder_id=user_id,
                    amount=bid_amount
                )
                self.db.add(new_bid)

                await self.db.execute(
                    update(Auction)
                    .where(Auction.id == auction_id)
                    .values(current_price=bid_amount)
                )

                await self.db.commit()

                await manager.broadcast_to_auction(
                    auction_id,
                    {
                        "event": "new_highest_bid",
                        "new_price": str(bid_amount),
                        "bidder_id": str(user_id),
                        "bidder_email": str(safe_email)
                    }
                )

                return True
            except WatchError:
                return False
            except Exception as e:
                await self.db.rollback()
                print(f"CRITICAL: Redis succeeded but DB failed for auction {auction_id}. Error: {e}")
                raise e
