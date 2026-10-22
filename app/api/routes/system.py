"""Health and system status routes."""

from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.api.schemas.common import (
    ConfigSummaryResponse,
    HealthResponse,
    ReadinessResponse,
)
from app.core.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint. Returns 200 if the server is running."""
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        version=__version__,
        environment=settings.app_env.value,
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check():
    """Readiness check. Verifies that essential subsystems are operational."""
    checks: dict[str, bool] = {}

    # Check database connectivity
    try:
        from app.db.session import get_engine

        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        checks["database"] = True
    except Exception:
        checks["database"] = False

    # Check configuration
    try:
        settings = get_settings()
        checks["configuration"] = True
    except Exception:
        checks["configuration"] = False

    ready = all(checks.values())
    return ReadinessResponse(ready=ready, checks=checks)


@router.get("/config", response_model=ConfigSummaryResponse)
async def config_summary():
    """Return non-sensitive configuration summary.

    Does NOT expose API keys, tokens, passwords, or connection strings.
    """
    settings = get_settings()
    return ConfigSummaryResponse(**settings.get_safe_summary())
