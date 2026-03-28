import pytest
import pytest_asyncio
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock
from sqlalchemy import select

from app.models import User, Auction, Bid
from app.services.bidding_service import BiddingService

@pytest_asyncio.fixture
async def setup_auction_data(db_session, clean_redis):
    """
    Creates an owner, an åuction, and a bidder in PostgreSQL.
    Also primes the Redis cache with the required auction state.
    """
    owner = User(
        supertokens_id="st-owner-789",
        email="owner@alexiz.dev"
    )
    bidder = User(
        supertokens_id="st-bidder-123",
        email="bidder@alexiz.dev"
    )

    db_session.add(owner)
    db_session.add(bidder)

    await db_session.flush()

    end_time = datetime.now(timezone.utc) + timedelta(minutes=5)

    auction = Auction(
        title="Test Auction",
        description="A strict test auction",
        starting_price=Decimal("10.00"),
        current_price=Decimal("10.00"),
        end_time=end_time,
        owner_id=owner.id
    )

    db_session.add(auction)
    await db_session.commit()

    await clean_redis.set(f"auction:{auction.id}:price", "10.00")
    await clean_redis.set(f"auction:{auction.id}:end_time", end_time.isoformat())

    return {
        "auction_id": auction.id,
        "bidder_id": bidder.id,
        "bidder_supertokens_id": bidder.supertokens_id,
        "bidder_email": bidder.email,
        "end_time": end_time
    }

@patch("app.services.bidding_service.manager.broadcast_to_auction", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_successful_first_bid(mock_broadcast, setup_auction_data, clean_redis, db_session):
    data = setup_auction_data
    service = BiddingService(redis_client=clean_redis, db_session=db_session)

    result = await service.place_bid(
        auction_id=data["auction_id"],
        user_id=data["bidder_id"],
        supertokens_id=data["bidder_supertokens_id"],
        user_email=data["bidder_email"],
        max_bid_amount=Decimal("15.00")
    )

    assert result["success"] is True
    assert result["is_winner"] is True

    price = await clean_redis.get(f"auction:{data['auction_id']}:price")
    max_bid = await clean_redis.get(f"auction:{data['auction_id']}:max_bid")

    assert Decimal(price) == Decimal("10.00")
    assert Decimal(max_bid) == Decimal("15.00")

    mock_broadcast.assert_called_once()

    query = select(Bid).where(Bid.auction_id == data["auction_id"])
    db_result = await db_session.execute(query)
    saved_bids = db_result.scalars().all()

    assert len(saved_bids) == 1
    assert saved_bids[0].amount == Decimal("10.00")
    assert saved_bids[0].bidder_id == data["bidder_id"]

@patch("app.services.bidding_service.manager.broadcast_to_auction", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_rejected_low_bid(mock_broadcast, setup_auction_data, clean_redis, db_session):
    data = setup_auction_data
    service = BiddingService(redis_client=clean_redis, db_session=db_session)

    result = await service.place_bid(
        auction_id=data["auction_id"],
        user_id=data["bidder_id"],
        supertokens_id=data["bidder_supertokens_id"],
        user_email=data["bidder_email"],
        max_bid_amount=Decimal("5.00")
    )

    assert result["success"] is False
    assert "Bid must be at least" in result["message"]

    mock_broadcast.assert_not_called()

@patch("app.services.bidding_service.manager.broadcast_to_auction", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_anti_sniping_time_extension(mock_broadcast, setup_auction_data, clean_redis, db_session):
    data = setup_auction_data
    service = BiddingService(redis_client=clean_redis, db_session=db_session)

    almost_over = datetime.now(timezone.utc) + timedelta(seconds=30)
    await clean_redis.set(f"auction:{data['auction_id']}:end_time", almost_over.isoformat())

    result = await service.place_bid(
        auction_id=data["auction_id"],
        user_id=data["bidder_id"],
        supertokens_id=data["bidder_supertokens_id"],
        user_email=data["bidder_email"],
        max_bid_amount=Decimal("20.00")
    )

    assert result["success"] is True

    new_end_time_str = await clean_redis.get(f"auction:{data['auction_id']}:end_time")
    new_end_time = datetime.fromisoformat(new_end_time_str)

    assert new_end_time > almost_over

    query = select(Auction).where(Auction.id == data["auction_id"])
    db_result = await db_session.execute(query)
    updated_auction = db_result.scalars().first()

    assert updated_auction.end_time.replace(microsecond=0) == new_end_time.replace(microsecond=0)

    assert mock_broadcast.call_count == 2
