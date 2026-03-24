from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from supertokens_python import get_all_cors_headers
from supertokens_python.framework.fastapi import get_middleware

from app.core.config import settings
from app.core.supertokens import init_supertokens
from app.core.redis import redis_client

from app.api.bids import router as bids_router

init_supertokens()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_client.ping()
    print("Successfully connected to Redis.")
    yield

    await redis_client.aclose()
    print("Redis connection closed.")

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(get_middleware())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "PUT", "POST", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type"] + get_all_cors_headers(),
)

app.include_router(bids_router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
