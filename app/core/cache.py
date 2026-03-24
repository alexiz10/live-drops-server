import redis.asyncio as redis

from app.core.config import settings

redis_client = redis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
    max_connections=50
)

async def get_redis() -> redis.Redis:
    """
    FastAPI dependency to inject the Redis client into our endpoints.
    """
    return redis_client
