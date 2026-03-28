import pytest

async def test_health_check(async_client):
    response = await async_client.get("/health")

    assert response.status_code == 200
