"""Global pytest configuration and fixtures."""

from datetime import date
import pytest
import pandas as pd
from app.core.config import AppSettings, Environment, reset_settings
from app.data.interfaces import Exchange, Timeframe
from app.data.providers.synthetic import generate_synthetic_ohlcv
from app.risk.engine import RiskEngine
from app.portfolio.manager import PortfolioManager


@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure clean settings before and after each test."""
    reset_settings()
    yield
    reset_settings()


@pytest.fixture
def test_settings() -> AppSettings:
    """Fixture providing isolated testing settings."""
    return AppSettings(
        app_env=Environment.TESTING,
        app_debug=True,
        database_url="sqlite+aiosqlite:///:memory:",
        risk_paper_only=True,
        risk_max_position_size_pct=10.0,
        risk_max_portfolio_exposure_pct=80.0,
        risk_max_drawdown_pct=20.0,
        risk_max_concentration_pct=25.0,
        paper_initial_cash=1_000_000.0,
    )


@pytest.fixture
def synthetic_ohlcv_df() -> pd.DataFrame:
    """Fixture providing deterministic OHLCV bars."""
    return generate_synthetic_ohlcv(
        symbol="SYNTH_RELIANCE",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 6, 1),
        timeframe=Timeframe.DAILY,
        seed=123,
    )


@pytest.fixture
def risk_engine(test_settings) -> RiskEngine:
    return RiskEngine(test_settings)


@pytest.fixture
def portfolio_manager(risk_engine) -> PortfolioManager:
    return PortfolioManager(initial_cash=1_000_000.0, risk_engine=risk_engine)
