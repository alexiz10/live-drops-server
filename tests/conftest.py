import pytest
import pytest_asyncio
import redis.asyncio as redis_async
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.models import Base

@pytest.fixture(scope="session")
def postgres_url():
    """
    Spins up an ephemeral PostgreSQL container before tests start.
    It automatically shuts down when the test session ends.
    """
    with PostgresContainer("postgres:17-alpine") as postgres:
        # testcontainers defaults to psycopg2, so we explicitly request the asyncpg driver
        yield postgres.get_connection_url(driver="asyncpg")

@pytest.fixture(scope="session")
def redis_url():
    """Spins up an ephemeral Redis container."""
    with RedisContainer("redis:7-alpine") as redis:
        # get_client() creates a sync client, so we just extract the URL
        # to build our own async client.
        yield f"redis://{redis.get_container_host_ip()}:{redis.get_exposed_port(6379)}/0"

@pytest_asyncio.fixture(scope="function")
async def db_session(postgres_url):
    """
    Connects to the ephemeral testcontainers database, creates all tables,
    yields the session for the test, and drops the tables afterward.
    """
    engine = create_async_engine(postgres_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.connect() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.commit()

    async with async_session() as session:
        yield session

    async with engine.connect() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.commit()

    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def clean_redis(redis_url):
    """
    Connects to the ephemeral testcontainers Redis instance and flushes
    data before and after each test.
    """
    client = redis_async.from_url(redis_url, encoding="utf-8", decode_responses=True)

    await client.flushdb()
    yield client
    await client.flushdb()

    await client.aclose()
