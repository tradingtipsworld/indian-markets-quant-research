"""FastAPI application factory.

Creates and configures the main application instance.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from app import __version__
from app.api.middleware import setup_middleware
from app.api.routes import agents, audit, intelligence, market_data, portfolio, quant, system
from app.core.config import get_settings
from app.core.events import on_shutdown, on_startup
from app.db.session import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler — startup and shutdown."""
    settings = get_settings()
    await on_startup(settings)
    await init_db()
    yield
    await close_db()
    await on_shutdown(settings)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="AI Quant Trading Platform",
        description=(
            "Foundational framework for AI quantitative research, "
            "deterministic backtesting, and paper trading on Indian financial markets. "
            "Educational and research purposes only."
        ),
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
    )

    # Middleware
    setup_middleware(app)

    # Mount API routers under versioned prefix
    app.include_router(system.router, prefix="/api/v1")
    app.include_router(market_data.router, prefix="/api/v1")
    app.include_router(quant.router, prefix="/api/v1")
    app.include_router(portfolio.router, prefix="/api/v1")
    app.include_router(agents.router, prefix="/api/v1")
    app.include_router(audit.router, prefix="/api/v1")
    app.include_router(intelligence.router, prefix="/api/v1")

    return app


# Default app instance for uvicorn
app = create_app()
