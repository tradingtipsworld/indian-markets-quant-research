"""Market data interfaces.

Defines abstract contracts for market data providers.
All implementations must conform to these interfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from enum import Enum
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field


class Exchange(str, Enum):
    """Supported exchanges."""

    NSE = "NSE"
    BSE = "BSE"
    SYNTHETIC = "SYNTHETIC"  # For test/synthetic data


class AssetType(str, Enum):
    """Supported asset types."""

    EQUITY = "equity"
    INDEX = "index"
    ETF = "etf"
    FUTURES = "futures"
    OPTIONS = "options"


class Timeframe(str, Enum):
    """Supported data timeframes."""

    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOURLY = "1h"
    DAILY = "1d"
    WEEKLY = "1w"
    MONTHLY = "1M"


class Instrument(BaseModel):
    """Market instrument metadata."""

    symbol: str
    name: str
    exchange: Exchange
    asset_type: AssetType
    isin: str = ""
    lot_size: int = 1
    tick_size: float = 0.05
    currency: str = "INR"
    is_active: bool = True

    model_config = {"frozen": True}


class OHLCVBar(BaseModel):
    """Single OHLCV price bar."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    symbol: str = ""
    timeframe: Timeframe = Timeframe.DAILY


class DataQualityReport(BaseModel):
    """Result of data quality validation."""

    symbol: str
    timeframe: Timeframe
    total_bars: int = 0
    missing_bars: int = 0
    duplicate_bars: int = 0
    invalid_prices: int = 0
    invalid_volumes: int = 0
    gaps: list[dict[str, Any]] = Field(default_factory=list)
    is_valid: bool = True
    issues: list[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=datetime.now)


class ProviderStatus(BaseModel):
    """Status of a data provider."""

    provider_name: str
    is_available: bool
    last_checked: datetime = Field(default_factory=datetime.now)
    error_message: str = ""


class MarketDataProvider(ABC):
    """Abstract interface for market data providers.

    All market data providers must implement this interface.
    This ensures consistent behavior across mock, file-based,
    and future API-based data sources.
    """

    @abstractmethod
    async def get_instruments(
        self, exchange: Exchange | None = None, asset_type: AssetType | None = None
    ) -> list[Instrument]:
        """List available instruments, optionally filtered."""
        ...

    @abstractmethod
    async def get_instrument(self, symbol: str, exchange: Exchange) -> Instrument | None:
        """Get metadata for a specific instrument."""
        ...

    @abstractmethod
    async def get_ohlcv(
        self,
        symbol: str,
        exchange: Exchange,
        timeframe: Timeframe,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Get historical OHLCV data.

        Returns a DataFrame with columns:
        timestamp, open, high, low, close, volume

        Indexed by timestamp. Data must be sorted ascending by time.
        """
        ...

    @abstractmethod
    async def get_status(self) -> ProviderStatus:
        """Check if the provider is available and responsive."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name of this provider."""
        ...

    @property
    def is_synthetic(self) -> bool:
        """Whether this provider returns synthetic/test data."""
        return False
