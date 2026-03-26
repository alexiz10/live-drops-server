import math
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from redis.asyncio import Redis
from typing import Literal, List

from supertokens_python.recipe.session.framework.fastapi import verify_session
from supertokens_python.recipe.session import SessionContainer

from app.core.database import get_db
from app.core.cache import get_redis
from app.models import User, Auction, Bid
from app.schemas.auction import AuctionCreate, AuctionResponse, PaginatedAuctions, mask_email

router = APIRouter(tags=["Auctions"])

@router.get("/", response_model=PaginatedAuctions)
async def list_auctions_endpoint(
        status: Literal["active", "ended"] = "active",
        page: int = 1,
        size: int = 12,
        db: AsyncSession = Depends(get_db)
):
    now = datetime.now(timezone.utc)

    condition = Auction.end_time > now if status == "active" else Auction.end_time <= now

    count_query = select(func.count(Auction.id)).where(condition)
    total = (await db.execute(count_query)).scalar_one()

    query = select(Auction).where(condition)
    query = query.order_by(Auction.end_time.asc() if status == "active" else Auction.end_time.desc())
    query = query.limit(size).offset((page - 1) * size)

    auctions = (await db.execute(query)).scalars().all()

    return PaginatedAuctions(
        items=list(auctions),
        total=total,
        page=page,
        size=size,
        total_pages=math.ceil(total / size) if total > 0 else 1
    )

@router.get("/me/listings", response_model=PaginatedAuctions)
async def get_my_auctions_endpoint(
        status: Literal["active", "ended"] = "active",
        page: int = 1,
        size: int = 12,
        session: SessionContainer = Depends(verify_session()),
        db: AsyncSession = Depends(get_db)
):
    supertokens_id = session.get_user_id()
    user_res = await db.execute(select(User).where(User.supertokens_id == supertokens_id))
    user = user_res.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(timezone.utc)

    condition = (Auction.owner_id == user.id) & (Auction.end_time > now if status == "active" else Auction.end_time <= now)

    total = (await db.execute(select(func.count(Auction.id)).where(condition))).scalar_one()

    query = select(Auction).where(condition)
    query = query.order_by(Auction.end_time.asc() if status == "active" else Auction.end_time.desc())
    query = query.limit(size).offset((page - 1) * size)

    auctions = (await db.execute(query)).scalars().all()

    return PaginatedAuctions(
        items=list(auctions),
        total=total,
        page=page,
        size=size,
        total_pages=math.ceil(total / size) if total > 0 else 1
    )

@router.post(
    "/",
    response_model=AuctionResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_auction_endpoint(
        auction_in: AuctionCreate,
        session: SessionContainer = Depends(verify_session()),
        db: AsyncSession = Depends(get_db),
        redis_client: Redis = Depends(get_redis)
):
    # look up the user creating the auction
    supertokens_id = session.get_user_id()
    result = await db.execute(select(User).where(User.supertokens_id == supertokens_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # create the database record
    new_auction = Auction(
        title=auction_in.title,
        description=auction_in.description,
        starting_price=auction_in.starting_price,
        current_price=auction_in.starting_price,
        end_time=auction_in.end_time,
        owner_id=user.id
    )

    db.add(new_auction)

    await db.commit()
    await db.refresh(new_auction)

    # seed Redis with the initial state
    price_key = f"auction:{new_auction.id}:price"
    end_time_key = f"auction:{new_auction.id}:end_time"

    async with redis_client.pipeline() as pipe:
        # save price as a string, and end_time as an ISO format string
        await pipe.set(price_key, str(new_auction.starting_price))
        await pipe.set(end_time_key, new_auction.end_time.isoformat())
        await pipe.execute()

    return new_auction

@router.get("/{auction_id}", response_model=AuctionResponse)
async def get_auction_endpoint(
        auction_id: uuid.UUID,
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Auction).where(Auction.id == auction_id))
    auction = result.scalar_one_or_none()

    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")

    stmt = (
        select(Bid.bidder_id, User.email, User.supertokens_id)
        .join(User, User.id == Bid.bidder_id)
        .where(Bid.auction_id == auction_id)
        .order_by(Bid.amount.desc())
        .limit(1)
    )
    highest_bid_result = await db.execute(stmt)
    highest_bid = highest_bid_result.first()

    if highest_bid:
        auction.highest_bidder_id = uuid.UUID(highest_bid.supertokens_id)
        auction.highest_bidder_email = mask_email(highest_bid.email)
    else:
        auction.highest_bidder_id = None
        auction.highest_bidder_email = None

    return auction
