from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis

from supertokens_python.recipe.session.framework.fastapi import verify_session
from supertokens_python.recipe.session import SessionContainer

from app.core.database import get_db
from app.core.redis import get_redis
from app.models import User, Auction
from app.schemas.auction import AuctionCreate, AuctionResponse

router = APIRouter(tags=["Auctions"])

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
