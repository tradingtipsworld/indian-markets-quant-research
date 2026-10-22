"""Unit tests for configuration loading, security redactions, and validation."""

import pytest
from app.core.config import AppSettings, Environment


def test_default_development_config():
    settings = AppSettings()
    assert settings.app_env == Environment.DEVELOPMENT
    assert settings.risk_paper_only is True
    assert settings.is_development is True
    assert "sqlite" in settings.database_url


def test_safe_summary_does_not_leak_secrets():
    settings = AppSettings(
        openai_api_key="sk-real-secret-12345",
        secret_key="top-secret-jwt-key",
        broker_api_secret="broker-secret",
    )
    summary = settings.get_safe_summary()
    assert "openai_api_key" not in summary
    assert "secret_key" not in summary
    assert "broker_api_secret" not in summary
    assert "sk-real-secret" not in str(summary)


def test_production_mode_requires_secret_key():
    with pytest.raises(ValueError, match="SECRET_KEY must be set in production"):
        AppSettings(
            app_env=Environment.PRODUCTION,
            app_debug=False,
            secret_key="",
        )


def test_invalid_log_level_rejected():
    with pytest.raises(ValueError, match="Invalid log level"):
        AppSettings(app_log_level="SUPER_VERBOSE")
