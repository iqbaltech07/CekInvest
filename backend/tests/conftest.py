"""
Test configuration and shared fixtures.
No auth required — all endpoints are public.
"""
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import prisma


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    """Connect to the Prisma database for the test session."""
    if not prisma.is_connected():
        await prisma.connect()
    yield
    try:
        if prisma.is_connected():
            await prisma.disconnect()
    except Exception:
        pass



@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Provide an async test client for FastAPI."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def db():
    """Provide the connected Prisma database client."""
    return prisma

