import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.models  # noqa: registers all models in Base.metadata
from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.user import User

TEST_DATABASE_URL = "postgresql+asyncpg://marketplace:marketplace@localhost:5432/marketplace_test"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(autouse=True)
async def reset_redis():
    """Close the Redis pool before each test so it's recreated on the current event loop."""
    from app.core import redis as redis_module
    if redis_module._redis_pool is not None:
        try:
            await redis_module._redis_pool.aclose()
        except Exception:
            pass
        redis_module._redis_pool = None
    yield


@pytest_asyncio.fixture(autouse=True)
async def clean_tables():
    """Truncate all tables and flush Redis after each test to ensure isolation."""
    yield
    async with test_engine.begin() as conn:
        table_names = ", ".join(
            f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables)
        )
        await conn.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
    from app.core import redis as redis_module
    if redis_module._redis_pool is not None:
        try:
            await redis_module._redis_pool.flushdb()
        except Exception:
            pass


@pytest_asyncio.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client with its own DB session — isolated from test_db."""
    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


async def _create_user(db: AsyncSession, email: str, role: str) -> User:
    user = User(
        email=email,
        hashed_password=hash_password("TestPass123!"),
        full_name=f"Test {role.title()}",
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def buyer_user() -> User:
    """Buyer User ORM object — use this when you need the buyer's id in tests."""
    async with TestSessionLocal() as db:
        return await _create_user(db, "buyer@test.com", "buyer")


@pytest_asyncio.fixture
async def buyer_token(buyer_user: User) -> str:
    return create_access_token({"sub": str(buyer_user.id), "role": buyer_user.role})


@pytest_asyncio.fixture
async def seller_user() -> User:
    """Seller User ORM object — use this when you need the seller's id in tests."""
    async with TestSessionLocal() as db:
        return await _create_user(db, "seller@test.com", "seller")


@pytest_asyncio.fixture
async def seller_token(seller_user: User) -> str:
    return create_access_token({"sub": str(seller_user.id), "role": seller_user.role})


@pytest_asyncio.fixture
async def admin_token() -> str:
    async with TestSessionLocal() as db:
        user = await _create_user(db, "admin@test.com", "admin")
        return create_access_token({"sub": str(user.id), "role": user.role})


@pytest_asyncio.fixture
async def inactive_buyer_token() -> str:
    async with TestSessionLocal() as db:
        user = User(
            email="inactive@test.com",
            hashed_password=hash_password("TestPass123!"),
            full_name="Inactive Buyer",
            role="buyer",
            is_active=False,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return create_access_token({"sub": str(user.id), "role": user.role})
