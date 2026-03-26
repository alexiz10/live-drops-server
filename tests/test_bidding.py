import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from app.services.bidding_service import BiddingService
from app.models import User, Auction

@pytest.mark.asyncio
async def test_place_bid_success(db_session, clean_redis):
    # setup: create a user in the DB
    user = User(supertokens_id="test_user", email="test@example.com")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # setup: create an auction in the DB
    end_time = datetime.now(timezone.utc) + timedelta(hours=1)
    auction = Auction(
        title="Test Auction",
        description="A great item",
        starting_price=Decimal("100.00"),
        current_price=Decimal("100.00"),
        end_time=end_time,
        owner_id=user.id
    )
    db_session.add(auction)
    await db_session.commit()
    await db_session.refresh(auction)

    # seed Redis
    await clean_redis.set(f"auction:{auction.id}:price", "100.00")
    await clean_redis.set(f"auction:{auction.id}:end_time", end_time.isoformat())

    # execute: place a higher bid
    service = BiddingService(clean_redis, db_session)
    success = await service.place_bid(
        auction_id=auction.id,
        user_id=user.id,
        max_bid_amount=Decimal("150.00")
    )

    # assert: did it work in Redis and the DB?
    assert success is True

    # check Redis state
    new_price = await clean_redis.get(f"auction:{auction.id}:price")
    assert new_price == "150.00"

    # check DB state
    from sqlalchemy import select
    from app.models import Bid
    result = await db_session.execute(select(Bid).where(Bid.auction_id == auction.id))
    bid_record = result.scalar_one()
    assert bid_record.amount == Decimal("150.00")

@pytest.mark.asyncio
async def test_place_bid_too_low(db_session, clean_redis):
    # setup
    auction_id = uuid.uuid4()
    await clean_redis.set(f"auction:{auction_id}:price", "200.00")

    # execute: try to bid lower than the current price
    service = BiddingService(clean_redis, db_session)
    success = await service.place_bid(
        auction_id=auction_id,
        user_id=uuid.uuid4(),
        max_bid_amount=Decimal("150.00")
    )

    # assert
    assert success is False
