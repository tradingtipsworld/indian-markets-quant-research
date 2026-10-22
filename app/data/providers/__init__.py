"""Data providers package.

Provides concrete implementations of MarketDataProvider:
- SyntheticDataProvider: Deterministic mock/testing data
- TejHQDataProvider: Official NSE/BSE EOD historical Bhavcopy provider
"""

from __future__ import annotations

from app.core.config import get_settings
from app.data.interfaces import MarketDataProvider
from app.data.providers.synthetic import (
    SYNTHETIC_INSTRUMENTS,
    SyntheticDataProvider,
    generate_synthetic_ohlcv,
)


def get_market_data_provider() -> MarketDataProvider:
    """Return configured market data provider singleton/factory based on AppSettings."""
    settings = get_settings()
    provider_name = (settings.market_data_provider or "mock").strip().lower()

    if provider_name in ("tejhq", "tej"):
        from app.data.providers.tejhq import TejHQDataProvider

        return TejHQDataProvider(api_key=settings.tejhq_api_key or None)

    return SyntheticDataProvider()


__all__ = [
    "MarketDataProvider",
    "SyntheticDataProvider",
    "SYNTHETIC_INSTRUMENTS",
    "generate_synthetic_ohlcv",
    "get_market_data_provider",
]
