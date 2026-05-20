"""
Shared FastAPI dependencies — Prisma DB client and SENTRA AI engine.
No authentication — all endpoints are public.
"""
from typing import Annotated

from fastapi import Depends

from app.database import prisma
from app.services.sentra_service import SentraService, get_sentra
from prisma import Prisma


def get_db() -> Prisma:
    """Return the shared Prisma client instance."""
    return prisma


DbDep = Annotated[Prisma, Depends(get_db)]
SentraDep = Annotated[SentraService, Depends(get_sentra)]
