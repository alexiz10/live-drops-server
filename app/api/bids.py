import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis

from supertokens_python.recipe.session.framework.fastapi import verify_session
from supertokens_python.recipe.session import SessionContainer

from app.core.database import get_db
from app.core.cache import get_redis
from app.models import User
from app.schemas.bid import BidCreate, BidResponse
from app.services.bidding_service import BiddingService

router = APIRouter(tags=["Bids"])

@router.post("/auctions/{auction_id}/bids", response_model=BidResponse, status_code=status.HTTP_201_CREATED)
async def place_bid_endpoint(
        auction_id: uuid.UUID,
        bid_in: BidCreate,
        session: SessionContainer = Depends(verify_session()),
        db: AsyncSession = Depends(get_db),
        redis_client: Redis = Depends(get_redis)
):
    supertokens_id = session.get_user_id()

    result = await db.execute(select(User).where(User.supertokens_id == supertokens_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User record not found in database."
        )

    bidding_service = BiddingService(redis_client=redis_client, db_session=db)

    success = await bidding_service.place_bid(
        auction_id=auction_id,
        user_id=user.id,
        user_email=user.email,
        bid_amount=bid_in.amount
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bid rejected. You were outbid or the amount is too low."
        )

    return BidResponse(message="Bid placed successfully")
