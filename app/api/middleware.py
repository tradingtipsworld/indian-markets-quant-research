"""API middleware — CORS, error handling, request logging."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    KillSwitchActiveError,
    PlatformError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


def setup_middleware(app: FastAPI) -> None:
    """Configure all middleware for the FastAPI application."""
    settings = get_settings()

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    # Exception handlers
    @app.exception_handler(PlatformError)
    async def platform_error_handler(request: Request, exc: PlatformError) -> JSONResponse:
        """Handle all platform-defined exceptions."""
        status_code = _error_to_status(exc)
        logger.warning(
            "Platform error",
            error_code=exc.code,
            error_message=str(exc),
            path=str(request.url.path),
        )
        return JSONResponse(
            status_code=status_code,
            content={
                "error": str(exc),
                "code": exc.code,
                "details": exc.details,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions without leaking internals."""
        logger.error(
            "Unhandled exception",
            error_type=type(exc).__name__,
            path=str(request.url.path),
            exc_info=exc,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "code": "INTERNAL_ERROR",
                "details": {},
            },
        )


def _error_to_status(exc: PlatformError) -> int:
    """Map platform exceptions to HTTP status codes."""
    if isinstance(exc, AuthenticationError):
        return 401
    if isinstance(exc, AuthorizationError):
        return 403
    if isinstance(exc, KillSwitchActiveError):
        return 503
    code = exc.code
    if "NOT_FOUND" in code:
        return 404
    if "VALIDATION" in code or "LIMIT_EXCEEDED" in code or "INSUFFICIENT" in code:
        return 422
    return 400
