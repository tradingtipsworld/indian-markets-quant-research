"""Unit and integration tests for TejHQ Indian market data provider."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.core.config import AppSettings, Environment
from app.data.interfaces import (
    AssetType,
    DataMode,
    Exchange,
    Timeframe,
)
from app.data.providers import get_market_data_provider
from app.data.providers.synthetic import SyntheticDataProvider
from app.data.providers.tejhq import TEJHQ_BENCHMARK_INSTRUMENTS, TejHQDataProvider


@pytest.fixture
def tejhq_provider() -> TejHQDataProvider:
    return TejHQDataProvider(api_key="mock_test_key_abc123")


@pytest.fixture
def sample_tejhq_rows() -> list[dict]:
    return [
        {
            "date": "2026-10-15",
            "open": 1185.2,
            "high": 1218.8,
            "low": 1177.2,
            "close": 1215.0,
            "last": 1215.0,
            "prev_close": 1174.6,
            "volume": 23456219,
            "turnover": 28290205774.8,
            "trades": 335751,
        },
        {
            "date": "2026-10-16",
            "open": 1215.0,
            "high": 1215.4,
            "low": 1193.0,
            "close": 1211.2,
            "last": 1211.2,
            "prev_close": 1215.0,
            "volume": 17225283,
            "turnover": 20794678894.3,
            "trades": 247276,
        },
    ]


def test_tejhq_provider_metadata(tejhq_provider: TejHQDataProvider):
    """Verify provider properties and provenance metadata."""
    assert tejhq_provider.is_synthetic is False
    assert tejhq_provider.data_mode == DataMode.HISTORICAL_RESEARCH
    assert "TejHQ" in tejhq_provider.provider_name
    assert "EOD Historical" in tejhq_provider.provider_name
    assert tejhq_provider.has_api_key is True


@pytest.mark.asyncio
async def test_tejhq_get_instruments(tejhq_provider: TejHQDataProvider):
    """Verify listing and filtering benchmark instruments."""
    instruments = await tejhq_provider.get_instruments()
    assert len(instruments) == len(TEJHQ_BENCHMARK_INSTRUMENTS)
    assert any(i.symbol == "RELIANCE" for i in instruments)
    assert any(i.isin == "INE002A01018" for i in instruments)

    # Filter by exchange
    nse_instruments = await tejhq_provider.get_instruments(exchange=Exchange.NSE)
    assert len(nse_instruments) > 0
    assert all(i.exchange == Exchange.NSE for i in nse_instruments)

    # Filter by asset type
    equity_instruments = await tejhq_provider.get_instruments(asset_type=AssetType.EQUITY)
    assert len(equity_instruments) == len(instruments)


@pytest.mark.asyncio
async def test_tejhq_get_instrument_resolution(tejhq_provider: TejHQDataProvider):
    """Verify fetching single instrument by symbol."""
    inst = await tejhq_provider.get_instrument("TCS", Exchange.NSE)
    assert inst is not None
    assert inst.symbol == "TCS"
    assert inst.isin == "INE467B01029"


@pytest.mark.asyncio
async def test_tejhq_ohlcv_intraday_rejection(tejhq_provider: TejHQDataProvider):
    """Ensure provider strictly rejects intraday timeframes to prevent mislabeling."""
    with pytest.raises(ValueError, match="End-of-Day.*EOD.*bhavcopy"):
        await tejhq_provider.get_ohlcv(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            timeframe=Timeframe.MINUTE_5,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 10),
        )


@pytest.mark.asyncio
async def test_tejhq_ohlcv_successful_parsing(
    tejhq_provider: TejHQDataProvider, sample_tejhq_rows: list[dict]
):
    """Test normalized DataFrame formatting from mocked TejHQ API response."""
    mock_async_client = AsyncMock()
    mock_async_client.ohlcv.return_value = sample_tejhq_rows

    with patch("tej.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value = mock_async_client

        df = await tejhq_provider.get_ohlcv(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            timeframe=Timeframe.DAILY,
            start_date=date(2026, 10, 15),
            end_date=date(2026, 10, 16),
        )

        assert not df.empty
        assert len(df) == 2
        assert list(df.columns[:8]) == [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "symbol",
            "is_synthetic",
        ]
        assert df["symbol"].iloc[0] == "RELIANCE"
        assert bool(df["is_synthetic"].iloc[0]) is False
        assert df["close"].iloc[0] == 1215.0
        assert df["volume"].iloc[0] == 23456219
        assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])
        assert df["timestamp"].is_monotonic_increasing


@pytest.mark.asyncio
async def test_tejhq_ohlcv_auth_error_handling(tejhq_provider: TejHQDataProvider):
    """Test graceful handling of authentication failure."""
    from tej.exceptions import AuthError

    mock_async_client = AsyncMock()
    mock_async_client.ohlcv.side_effect = AuthError("API key invalid", status_code=401)

    with patch("tej.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value = mock_async_client

        with pytest.raises(PermissionError, match="TejHQ authentication failed"):
            await tejhq_provider.get_ohlcv(
                symbol="RELIANCE",
                exchange=Exchange.NSE,
                timeframe=Timeframe.DAILY,
                start_date=date(2026, 10, 1),
                end_date=date(2026, 10, 5),
            )


@pytest.mark.asyncio
async def test_tejhq_ohlcv_rate_limit_error_handling(tejhq_provider: TejHQDataProvider):
    """Test graceful handling of rate limiting."""
    from tej.exceptions import RateLimitError

    mock_async_client = AsyncMock()
    mock_async_client.ohlcv.side_effect = RateLimitError("rate limit exceeded", status_code=429)

    with patch("tej.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value = mock_async_client

        with pytest.raises(RuntimeError, match="TejHQ rate limit exceeded"):
            await tejhq_provider.get_ohlcv(
                symbol="RELIANCE",
                exchange=Exchange.NSE,
                timeframe=Timeframe.DAILY,
                start_date=date(2026, 10, 1),
                end_date=date(2026, 10, 5),
            )


@pytest.mark.asyncio
async def test_tejhq_ohlcv_not_found_returns_empty(tejhq_provider: TejHQDataProvider):
    """Test 404 symbol not found gracefully returns empty DataFrame."""
    from tej.exceptions import NotFoundError

    mock_async_client = AsyncMock()
    mock_async_client.ohlcv.side_effect = NotFoundError("symbol not found", status_code=404)

    with patch("tej.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value = mock_async_client

        df = await tejhq_provider.get_ohlcv(
            symbol="NONEXISTENT",
            exchange=Exchange.NSE,
            timeframe=Timeframe.DAILY,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 5),
        )

        assert df.empty
        assert "timestamp" in df.columns
        assert "close" in df.columns


@pytest.mark.asyncio
async def test_tejhq_status_check(tejhq_provider: TejHQDataProvider):
    """Test health and usage quota status inquiry."""
    mock_async_client = AsyncMock()
    mock_async_client.health.return_value = {"status": "ok"}
    mock_async_client.me.return_value = {
        "tier": "free",
        "usage_today": {"used": 15, "limit": 1000},
    }

    with patch("tej.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value = mock_async_client

        status = await tejhq_provider.get_status()
        assert status.is_available is True
        assert status.data_mode == DataMode.HISTORICAL_RESEARCH
        assert "Used: 15/1000" in status.provider_name


def test_provider_factory():
    """Test dynamic provider selection via AppSettings."""
    with patch("app.data.providers.get_settings") as mock_settings:
        # Mock provider config
        mock_settings.return_value = AppSettings(
            market_data_provider="mock",
        )
        provider = get_market_data_provider()
        assert isinstance(provider, SyntheticDataProvider)

        # TejHQ provider config
        mock_settings.return_value = AppSettings(
            market_data_provider="tejhq",
            tejhq_api_key="tej_live_test",
        )
        provider = get_market_data_provider()
        assert isinstance(provider, TejHQDataProvider)
        assert provider.is_synthetic is False
