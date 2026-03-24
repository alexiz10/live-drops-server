import uuid
from decimal import Decimal
from redis.asyncio import Redis
from redis.exceptions import WatchError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from app.models import Bid, Auction

class BiddingService:
    def __init__(self, redis_client: Redis, db_session: AsyncSession):
        self.redis = redis_client
        self.db = db_session

    async def place_bid(self, auction_id: uuid.UUID, user_id: uuid.UUID, bid_amount: Decimal) -> bool:
        """
        Attempts to place a bid using Redis Optimistic Locking.
        Returns True if successful, False if outbid or the bid is too low.
        """
        price_key = f"auction:{auction_id}:price"
        bidder_key = f"auction:{auction_id}:bidder"

        async with self.redis.pipeline() as pipe:
            try:
                await pipe.watch(price_key)

                current_price_str = await pipe.get(price_key)
                current_price = Decimal(current_price_str) if current_price_str else Decimal("0.00")

                if bid_amount <= current_price:
                    await pipe.unwatch()
                    return False

                pipe.multi()

                await pipe.set(price_key, str(bid_amount))
                await pipe.set(bidder_key, str(user_id))

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

                return True
            except WatchError:
                return False
            except Exception as e:
                await self.db.rollback()
                print(f"CRITICAL: Redis succeeded but DB failed for auction {auction_id}. Error: {e}")
                raise e
