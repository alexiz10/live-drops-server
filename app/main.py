import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from supertokens_python import get_all_cors_headers
from supertokens_python.framework.fastapi import get_middleware

from app.core.config import settings
from app.core.supertokens import init_supertokens
from app.core.cache import redis_client

from app.api.auctions import router as auctions_router
from app.api.bids import router as bids_router
from app.api.websockets import router as websocket_router

from app.tasks.countdown import auction_countdown_broadcaster

init_supertokens()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_client.ping()
    print("Successfully connected to Redis.")

    countdown_task = asyncio.create_task(auction_countdown_broadcaster())

    yield

    countdown_task.cancel()

    try:
        await countdown_task
    except asyncio.CancelledError:
        pass

    await redis_client.aclose()
    print("Redis connection closed.")

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(get_middleware())

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "PUT", "POST", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type"] + get_all_cors_headers(),
)

app.include_router(auctions_router, prefix=f"{settings.API_V1_STR}/auctions")
app.include_router(bids_router, prefix=settings.API_V1_STR)
app.include_router(websocket_router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
