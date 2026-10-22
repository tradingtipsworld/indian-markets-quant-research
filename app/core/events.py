"""Application lifecycle events — startup and shutdown."""

from __future__ import annotations

import secrets

from app.core.config import AppSettings, Environment
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


async def on_startup(settings: AppSettings) -> None:
    """Run on application startup.

    - Configures logging
    - Validates environment
    - Logs safe configuration summary
    """
    configure_logging(
        log_level=settings.app_log_level,
        json_output=settings.is_production,
    )

    # Generate a dev-only secret key if not set
    if not settings.secret_key and settings.is_development:
        settings.secret_key = secrets.token_urlsafe(64)
        logger.warning(
            "Generated ephemeral SECRET_KEY for development. "
            "Set SECRET_KEY in .env for persistence."
        )

    logger.info(
        "Application starting",
        **settings.get_safe_summary(),
        version=settings.app_version,
    )

    if settings.risk_paper_only:
        logger.info("Paper-only mode ENABLED. No live trading is possible.")
    else:
        logger.warning("Paper-only mode DISABLED. Live trading may be active.")

    if settings.risk_kill_switch:
        logger.warning("Kill switch is ACTIVE. All trading is halted.")


async def on_shutdown(settings: AppSettings) -> None:
    """Run on application shutdown."""
    logger.info("Application shutting down")
