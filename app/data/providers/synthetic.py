"""Synthetic data provider for development and testing.

Generates deterministic, clearly-labeled synthetic OHLCV data
that must NEVER be mistaken for real market data.

All data includes a "SYNTHETIC" exchange marker and documentation
warnings to prevent accidental misuse.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
import hashlib
from typing import Any

import numpy as np
import pandas as pd

from app.data.interfaces import (
    AssetType,
    Exchange,
    Instrument,
    MarketDataProvider,
    ProviderStatus,
    Timeframe,
)

# ──────────────────────────────────────────────────────────────
# WARNING: This provider generates SYNTHETIC data only.
# It does NOT represent real market prices or volumes.
# Never use synthetic data for real trading decisions.
# ──────────────────────────────────────────────────────────────

# Predefined synthetic instruments for testing
SYNTHETIC_INSTRUMENTS: list[Instrument] = [
    Instrument(
        symbol="SYNTH_RELIANCE",
        name="[SYNTHETIC] Reliance Industries",
        exchange=Exchange.SYNTHETIC,
        asset_type=AssetType.EQUITY,
        lot_size=1,
        tick_size=0.05,
        currency="INR",
    ),
    Instrument(
        symbol="SYNTH_TCS",
        name="[SYNTHETIC] Tata Consultancy Services",
        exchange=Exchange.SYNTHETIC,
        asset_type=AssetType.EQUITY,
        lot_size=1,
        tick_size=0.05,
        currency="INR",
    ),
    Instrument(
        symbol="SYNTH_INFY",
        name="[SYNTHETIC] Infosys",
        exchange=Exchange.SYNTHETIC,
        asset_type=AssetType.EQUITY,
        lot_size=1,
        tick_size=0.05,
        currency="INR",
    ),
    Instrument(
        symbol="SYNTH_NIFTY50",
        name="[SYNTHETIC] Nifty 50 Index",
        exchange=Exchange.SYNTHETIC,
        asset_type=AssetType.INDEX,
        lot_size=50,
        tick_size=0.05,
        currency="INR",
    ),
    Instrument(
        symbol="SYNTH_HDFCBANK",
        name="[SYNTHETIC] HDFC Bank",
        exchange=Exchange.SYNTHETIC,
        asset_type=AssetType.EQUITY,
        lot_size=1,
        tick_size=0.05,
        currency="INR",
    ),
]

# Deterministic base prices for reproducibility
_BASE_PRICES: dict[str, float] = {
    "SYNTH_RELIANCE": 2500.0,
    "SYNTH_TCS": 3800.0,
    "SYNTH_INFY": 1600.0,
    "SYNTH_NIFTY50": 22000.0,
    "SYNTH_HDFCBANK": 1700.0,
}


def _deterministic_symbol_seed(symbol: str) -> int:
    """Generate a deterministic 32-bit unsigned integer seed from a symbol string using SHA-256.

    Guarantees cross-process and cross-platform reproducibility, unlike Python's built-in hash().
    """
    digest = hashlib.sha256(symbol.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], byteorder="big", signed=False)


def generate_synthetic_ohlcv(
    symbol: str,
    start_date: date,
    end_date: date,
    timeframe: Timeframe = Timeframe.DAILY,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate deterministic synthetic OHLCV data.

    Uses a random walk with controlled volatility to produce
    realistic-looking but entirely artificial price data.
    The same seed + symbol + dates always produces the exact same data across separate processes.

    Args:
        symbol: Instrument symbol.
        start_date: Start date (inclusive).
        end_date: End date (inclusive).
        timeframe: Data timeframe.
        seed: Random seed for reproducibility.

    Returns:
        DataFrame with columns: timestamp, open, high, low, close, volume, symbol, is_synthetic
    """
    # Combine symbol SHA-256 hash with seed for deterministic per-symbol seed
    symbol_seed = (int(seed) + _deterministic_symbol_seed(symbol)) % (2**31 - 1)
    rng = np.random.default_rng(symbol_seed)

    base_price = _BASE_PRICES.get(symbol, 1000.0)

    # Generate trading days (skip weekends for daily data)
    if timeframe == Timeframe.DAILY:
        all_dates = pd.bdate_range(start=start_date, end=end_date)
    else:
        all_dates = pd.date_range(start=start_date, end=end_date, freq="h")

    n_bars = len(all_dates)
    if n_bars == 0:
        return pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume", "symbol", "is_synthetic"]
        )

    # Random walk for close prices
    daily_returns = rng.normal(0.0005, 0.02, n_bars)  # ~0.05% daily drift, 2% vol
    cumulative = np.cumsum(daily_returns)
    close_prices = base_price * np.exp(cumulative)

    # Generate OHLCV from close prices
    intraday_range = rng.uniform(0.005, 0.03, n_bars)  # 0.5-3% intraday range
    open_offset = rng.uniform(-0.5, 0.5, n_bars)

    open_prices = close_prices * (1 + open_offset * intraday_range * 0.3)
    high_prices = np.maximum(open_prices, close_prices) * (1 + intraday_range * 0.5)
    low_prices = np.minimum(open_prices, close_prices) * (1 - intraday_range * 0.5)
    volumes = (rng.lognormal(15, 1.5, n_bars)).astype(int)

    # Round to tick size
    tick = 0.05
    open_prices = np.round(open_prices / tick) * tick
    high_prices = np.round(high_prices / tick) * tick
    low_prices = np.round(low_prices / tick) * tick
    close_prices = np.round(close_prices / tick) * tick

    df = pd.DataFrame({
        "timestamp": all_dates,
        "open": open_prices,
        "high": high_prices,
        "low": low_prices,
        "close": close_prices,
        "volume": volumes,
        "symbol": symbol,
        "is_synthetic": True,  # ALWAYS mark as synthetic
    })

    return df


class SyntheticDataProvider(MarketDataProvider):
    """Synthetic market data provider for development and testing.

    ⚠️ WARNING: All data from this provider is SYNTHETIC.
    It does not represent real market prices or volumes.
    """

    async def get_instruments(
        self, exchange: Exchange | None = None, asset_type: AssetType | None = None
    ) -> list[Instrument]:
        instruments = SYNTHETIC_INSTRUMENTS.copy()
        if exchange is not None and exchange != Exchange.SYNTHETIC:
            return []
        if asset_type is not None:
            instruments = [i for i in instruments if i.asset_type == asset_type]
        return instruments

    async def get_instrument(self, symbol: str, exchange: Exchange) -> Instrument | None:
        for inst in SYNTHETIC_INSTRUMENTS:
            if inst.symbol == symbol:
                return inst
        return None

    async def get_ohlcv(
        self,
        symbol: str,
        exchange: Exchange,
        timeframe: Timeframe,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        return generate_synthetic_ohlcv(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
        )

    async def get_status(self) -> ProviderStatus:
        return ProviderStatus(
            provider_name=self.provider_name,
            is_available=True,
        )

    @property
    def provider_name(self) -> str:
        return "Synthetic Data Provider (TEST DATA ONLY)"

    @property
    def is_synthetic(self) -> bool:
        return True
