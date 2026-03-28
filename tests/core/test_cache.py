import pytest
import redis.asyncio as redis

from app.core.config import settings
from app.core.cache import get_redis, redis_client

# =====================================================
# UNIT TESTS
# Testing logic in complete isolation without network calls.
# =====================================================

@pytest.mark.asyncio
async def test_unit_get_redis_returns_client():
    """
    Unit Test: Verifies that the FastAPI dependency strictly yields
    the exact singleton Redis client instantiated in the module.
    """

    client = await get_redis()

    assert client is redis_client
    assert isinstance(client, redis.Redis)

def test_unit_redis_client_configuration():
    """
    Unit Test: Verifies the global redis_client was instantiated with
    the correct parameters from settings, without actually connecting to Redis.
    """

    kwargs = redis_client.connection_pool.connection_kwargs

    assert kwargs.get("decode_responses") is True
    assert kwargs.get("encoding") == "utf-8"
    assert redis_client.connection_pool.max_connections == 50

# =====================================================
# INTEGRATION TESTS
# Testing that the configuration can actually connect to a real Redis instance.
# =====================================================

@pytest.mark.asyncio
async def test_integration_redis_connection(redis_url):
    """
    Integration Test: We build a temporary client using the exact same
    kwargs as the cache.py, but point it to the ephemeral testcontainer URL.
    """

    temp_client = redis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=50
    )

    try:
        response = await temp_client.ping()

        assert response is True
    finally:
        await temp_client.aclose()
