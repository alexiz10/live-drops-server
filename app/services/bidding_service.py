import uuid
from decimal import Decimal
from datetime import datetime, timezone
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

    async def place_bid(self, auction_id: uuid.UUID, user_id: uuid.UUID, supertokens_id: str, user_email: str, max_bid_amount: Decimal):
        """
        Proxy Bidding Engine using Redis Optimistic Locking.
        """
        safe_email = mask_email(user_email)
        INCREMENT = Decimal("1.00")

        price_key = f"auction:{auction_id}:price"
        bidder_key = f"auction:{auction_id}:bidder"
        max_bid_key = f"auction:{auction_id}:max_bid"
        bidder_email_key = f"auction:{auction_id}:bidder_email"
        supertokens_key = f"auction:{auction_id}:supertokens_id"

        async with self.redis.pipeline() as pipe:
            try:
                # watch all relevant keys for race conditions
                await pipe.watch(price_key, max_bid_key, bidder_key)

                # fetch current state
                current_price_str = await pipe.get(price_key)
                current_price = Decimal(current_price_str) if current_price_str else Decimal("0.00")

                current_max_str = await pipe.get(max_bid_key)
                current_max = Decimal(current_max_str) if current_max_str else Decimal("0.00")

                current_bidder = await pipe.get(bidder_key)
                current_bidder = current_bidder.decode("utf-8") if isinstance(current_bidder, bytes) else current_bidder

                # time check
                end_time_str = await self.redis.get(f"auction:{auction_id}:end_time")
                if end_time_str:
                    end_time = datetime.fromisoformat(end_time_str)
                    if datetime.now(timezone.utc) >= end_time:
                        await pipe.unwatch()
                        return False

                # validation: is the new bid allowed?
                # if there is an existing max bid, the new bid must be at least the current public price + increment
                minimum_allowed = current_price + INCREMENT if current_max else current_price
                if max_bid_amount < minimum_allowed:
                    await pipe.unwatch()
                    return {"success": False, "message": f"Bid must be at least ${minimum_allowed}"}

                # the proxy algorithm
                winning_user_id = str(user_id)
                winning_supertokens_id = supertokens_id
                winning_email = safe_email
                winning_max_bid = max_bid_amount

                if not current_max:
                    # first bid, public price stays at the starting price
                    new_price = current_price

                elif current_bidder == str(user_id):
                    # the user is just increasing their own ceiling
                    new_price = current_price

                else:
                    # proxy war
                    if max_bid_amount > current_max:
                        # the new bidder breaks through the old ceiling
                        new_price = min(current_max + INCREMENT, max_bid_amount)
                    else:
                        # the old bidder's proxy defends
                        new_price = min(max_bid_amount + INCREMENT, current_max)

                        # revert the winner stats back to the defending champion
                        winning_user_id = current_bidder
                        winning_max_bid = current_max

                        # we have to fetch the old winner's details from Redis to broadcast them again
                        winning_email = await pipe.get(bidder_email_key)
                        winning_email = winning_email.decode("utf-8") if isinstance(winning_email, bytes) else winning_email
                        winning_supertokens_id = await pipe.get(supertokens_key)
                        winning_supertokens_id = winning_supertokens_id.decode("utf-8") if isinstance(winning_supertokens_id, bytes) else winning_supertokens_id

                # lock in the new state
                pipe.multi()

                await pipe.set(price_key, str(new_price))
                await pipe.set(max_bid_key, str(winning_max_bid))
                await pipe.set(bidder_key, winning_user_id)
                await pipe.set(bidder_email_key, winning_email)
                await pipe.set(supertokens_key, winning_supertokens_id)

                await pipe.execute()

                # database sync
                # only log a new bid row if the price actually moved, or if it's the very first bid
                if new_price > current_price or not current_max:
                    new_bid = Bid(
                        auction_id=auction_id,
                        bidder_id=uuid.UUID(winning_user_id),
                        amount=new_price
                    )
                    self.db.add(new_bid)

                    await self.db.execute(
                        update(Auction)
                        .where(Auction.id == auction_id)
                        .values(current_price=new_price)
                    )
                    await self.db.commit()

                # broadcast the result
                await manager.broadcast_to_auction(
                    auction_id,
                    {
                        "event": "new_highest_bid",
                        "new_price": str(new_price),
                        "bidder_id": winning_supertokens_id,
                        "bidder_email": winning_email
                    }
                )

                return {
                    "success": True,
                    "is_winner": str(user_id) == winning_user_id
                }

            except WatchError:
                return {"success": False, "message": "High traffic. Please try again."}

            except Exception as e:
                await self.db.rollback()
                print(f"CRITICAL: Redis proxy failed for auction {auction_id}. Error: {e}")
                raise e
