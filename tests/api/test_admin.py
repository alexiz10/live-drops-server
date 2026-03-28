import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock
from sqlalchemy import select

from app.core.config import settings
from app.models import User

@pytest_asyncio.fixture
async def setup_cleanup_data(db_session):
    """
    Seeds the database with two users:
    - One 'stale' user created 10 hours ago
    - One 'fresh' user created 2 hours ago
    """

    now = datetime.now(timezone.utc)

    stale_user = User(
        supertokens_id="st-stale-123",
        email="stale@alexiz.dev",
        created_at=now - timedelta(hours=10)
    )

    fresh_user = User(
        supertokens_id="st-fresh-123",
        email="fresh@alexiz.dev",
        created_at=now - timedelta(hours=2)
    )

    db_session.add(stale_user)
    db_session.add(fresh_user)
    await db_session.commit()

    return {
        "stale_supertokens_id": stale_user.supertokens_id,
        "fresh_supertokens_id": fresh_user.supertokens_id
    }

@pytest.mark.asyncio
async def test_cleanup_unauthorized(async_client):
    """
    Tests that the endpoint strictly enforces the cron_secret header
    """

    response = await async_client.delete(
        "/api/v1/cleanup",
        headers={"x-cron-secret": "invalid-secret-key"}
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Unauthorized"

@patch("app.api.admin.delete_user", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_cleanup_success(mock_delete_user, async_client, setup_cleanup_data, db_session):
    """
    Tests that the endpoint correctly identifies stale data, calls SuperTokens,
    and removes the record from PostgreSQL.
    """

    data = setup_cleanup_data
    headers = {"x-cron-secret": settings.CRON_SECRET}

    response = await async_client.delete("/api/v1/cleanup", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"status": "success", "users_deleted": 1}

    mock_delete_user.assert_called_once_with(data["stale_supertokens_id"])

    query = select(User)
    result = await db_session.execute(query)
    remaining_users = result.scalars().all()

    assert len(remaining_users) == 1
    assert remaining_users[0].supertokens_id == data["fresh_supertokens_id"]

@patch("app.api.admin.delete_user", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_cleanup_supertokens_exception(mock_delete_user, async_client, setup_cleanup_data, db_session):
    """
    Tests the exception handling block. If SuperTokens fails to delete a user,
    the endpoint should log it, skip the DB deletion for that user, and return 200.
    """

    data = setup_cleanup_data
    headers = {"x-cron-secret": settings.CRON_SECRET}

    mock_delete_user.side_effect = Exception("SuperTokens network timeout")

    response = await async_client.delete("/api/v1/cleanup", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"status": "success", "users_deleted": 0}

    query = select(User)
    result = await db_session.execute(query)
    remaining_users = result.scalars().all()

    assert len(remaining_users) == 2
