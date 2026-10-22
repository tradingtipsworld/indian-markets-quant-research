"""Application configuration loaded from environment variables.

Uses pydantic-settings for validation and type safety.
All external API keys and secrets are optional — the platform
runs in development mode without any paid services.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class AppSettings(BaseSettings):
    """Core application settings."""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application ---
    app_env: Environment = Environment.DEVELOPMENT
    app_debug: bool = True
    app_log_level: str = "INFO"
    app_name: str = "AI Quant Trading Platform"
    app_version: str = "0.1.0"

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./platform.db"

    # --- API Server ---
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # --- Security ---
    secret_key: str = ""  # Generated at startup if empty in dev mode

    # --- AI Providers & Auto-Selection ---
    ai_provider: str = "mock"
    ai_auto_fallback: bool = True
    groq_api_key: str = ""
    openrouter_api_key: str = ""
    mistral_api_key: str = ""
    nvidia_api_key: str = ""
    gemini_api_key: str = ""
    gemini_api_key_backup: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_ai_api_key: str = ""
    ai_model_name: str = ""
    # --- Market Data ---
    market_data_provider: str = "mock"
    market_data_api_key: str = ""
    market_data_base_url: str = ""
    tejhq_api_key: str = ""

    # --- Broker (future) ---
    broker_provider: str = "paper"
    broker_api_key: str = ""
    broker_api_secret: str = ""
    broker_base_url: str = ""

    # --- Notifications (future) ---
    notification_provider: str = "mock"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_channel_username: str = "@tradingtipsworld"

    # --- Risk Engine ---
    risk_max_position_size_pct: float = 10.0
    risk_max_portfolio_exposure_pct: float = 80.0
    risk_max_drawdown_pct: float = 20.0
    risk_max_concentration_pct: float = 25.0
    risk_paper_only: bool = True
    risk_kill_switch: bool = False

    # --- Paper Trading ---
    paper_initial_cash: float = 1_000_000.0

    @field_validator("app_log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"Invalid log level '{v}'. Must be one of: {valid}")
        return upper

    @model_validator(mode="after")
    def validate_production_settings(self) -> "AppSettings":
        """Enforce stricter validation in production."""
        if self.app_env == Environment.PRODUCTION:
            if not self.secret_key:
                raise ValueError(
                    "SECRET_KEY must be set in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
                )
            if self.app_debug:
                raise ValueError("APP_DEBUG must be false in production.")
            if self.risk_paper_only is False and self.broker_provider == "paper":
                raise ValueError(
                    "Cannot disable paper-only mode without a configured broker provider."
                )
        return self

    @property
    def is_development(self) -> bool:
        return self.app_env == Environment.DEVELOPMENT

    @property
    def is_testing(self) -> bool:
        return self.app_env == Environment.TESTING

    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.database_url

    def get_safe_summary(self) -> dict[str, Any]:
        """Return a summary of settings without exposing secrets.

        This is safe for logging and API responses.
        """
        return {
            "app_env": self.app_env.value,
            "app_debug": self.app_debug,
            "app_log_level": self.app_log_level,
            "database_type": "sqlite" if self.is_sqlite else "postgresql",
            "ai_provider": self.ai_provider,
            "market_data_provider": self.market_data_provider,
            "broker_provider": self.broker_provider,
            "notification_provider": self.notification_provider,
            "risk_paper_only": self.risk_paper_only,
            "risk_kill_switch": self.risk_kill_switch,
            "paper_initial_cash": self.paper_initial_cash,
        }


# Module-level singleton — lazily initialized
_settings: AppSettings | None = None


def get_settings() -> AppSettings:
    """Get the application settings singleton."""
    global _settings
    if _settings is None:
        _settings = AppSettings()
    return _settings


def reset_settings() -> None:
    """Reset the settings singleton. Used in testing."""
    global _settings
    _settings = None
