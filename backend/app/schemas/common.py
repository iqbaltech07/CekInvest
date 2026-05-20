"""
Generic API response envelope for consistent output across all endpoints.
"""
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field
from datetime import datetime, timezone


DataT = TypeVar("DataT")


class APIResponse(BaseModel, Generic[DataT]):
    """Standard success response wrapper."""

    success: bool = True
    data: DataT
    meta: dict[str, Any] = Field(
        default_factory=lambda: {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
        }
    )


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[Any] | None = None


class ErrorResponse(BaseModel):
    """Standard error response wrapper."""

    success: bool = False
    error: ErrorDetail


class PaginatedMeta(BaseModel):
    total: int
    page: int
    per_page: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Paginated success response wrapper."""

    success: bool = True
    data: list[DataT]
    meta: PaginatedMeta
