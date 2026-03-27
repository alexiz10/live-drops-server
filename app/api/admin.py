from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from supertokens_python.asyncio import delete_user

from app.core.config import settings
from app.core.database import get_db
from app.models import User

router = APIRouter(tags=["Admin"])

@router.delete("/cleanup")
async def cleanup_old_data(
        cron_secret: str = Header(None, alias="x-cron-secret"),
        db: AsyncSession = Depends(get_db)
):
    # verify request
    if cron_secret != settings.CRON_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")

    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=8)

    # get all users created before the cutoff time
    query = select(User).where(User.created_at < cutoff_time)
    result = await db.execute(query)
    stale_users = result.scalars().all()

    deleted_count = 0

    for user in stale_users:
        try:
            # wipe the user from SuperTokens first
            await delete_user(user.supertokens_id)

            # wipe user from Postgres database
            await db.delete(user)
            deleted_count += 1

        except Exception as e:
            # log the error but don't crash the whole cleanup job
            print(f"Failed to delete user {user.supertokens_id}: {e}")
            continue

    await db.commit()

    return {"status": "success", "users_deleted": deleted_count}
