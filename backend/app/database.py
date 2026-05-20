"""
Prisma client singleton — the single source of truth for all DB access.
Replaces SQLAlchemy engine + session factory.
"""
from prisma import Prisma

# Module-level singleton, connected during app lifespan
prisma: Prisma = Prisma()


async def connect() -> None:
    """Connect the Prisma client to the database."""
    await prisma.connect()


async def disconnect() -> None:
    """Disconnect the Prisma client cleanly."""
    await prisma.disconnect()
