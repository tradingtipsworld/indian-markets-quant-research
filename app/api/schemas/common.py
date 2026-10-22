"""Common API response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    code: str
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success wrapper for API responses."""

    data: T
    timestamp: datetime = Field(default_factory=datetime.now)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str
    environment: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ReadinessResponse(BaseModel):
    """Readiness check response."""

    ready: bool
    checks: dict[str, bool] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class ConfigSummaryResponse(BaseModel):
    """Non-sensitive configuration summary."""

    app_env: str
    app_debug: bool
    app_log_level: str
    database_type: str
    ai_provider: str
    market_data_provider: str
    broker_provider: str
    notification_provider: str
    risk_paper_only: bool
    risk_kill_switch: bool
    paper_initial_cash: float


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    data: list[T]
    total: int
    page: int
    page_size: int
    timestamp: datetime = Field(default_factory=datetime.now)
