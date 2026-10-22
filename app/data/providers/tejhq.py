"""TejHQ Indian market data provider.

Integrates with the official TejHQ API (https://tejhq.dev) for NSE and BSE
End-of-Day (EOD) Bhavcopy data, corporate actions, and Point-in-Time metrics.

Data Provenance Note:
- All data returned by this provider is End-of-Day (EOD) historical bhavcopy data.
- It is labeled as DataMode.HISTORICAL_RESEARCH (never live intraday ticks).
- Real intraday execution or tick subscriptions are NOT provided by this provider.
"""

from __future__ import annotations

from datetime import date
from typing import Any
import structlog

import pandas as pd

from app.core.config import get_settings
from app.data.interfaces import (
    AssetType,
    DataMode,
    DataProvenance,
    Exchange,
    Instrument,
    MarketDataProvider,
    ProviderStatus,
    Timeframe,
)

logger = structlog.get_logger(__name__)

# Curated benchmark instruments across NSE & BSE with verified ISINs
TEJHQ_BENCHMARK_INSTRUMENTS: list[Instrument] = [
    Instrument(
        symbol="RELIANCE",
        name="Reliance Industries Limited",
        exchange=Exchange.NSE,
        asset_type=AssetType.EQUITY,
        isin="INE002A01018",
        lot_size=1,
        tick_size=0.05,
        currency="INR",
    ),
    Instrument(
        symbol="TCS",
        name="Tata Consultancy Services Limited",
        exchange=Exchange.NSE,
        asset_type=AssetType.EQUITY,
        isin="INE467B01029",
        lot_size=1,
        tick_size=0.05,
        currency="INR",
    ),
    Instrument(
        symbol="INFY",
        name="Infosys Limited",
        exchange=Exchange.NSE,
        asset_type=AssetType.EQUITY,
        isin="INE009A01021",
        lot_size=1,
        tick_size=0.05,
        currency="INR",
    ),
    Instrument(
        symbol="HDFCBANK",
        name="HDFC Bank Limited",
        exchange=Exchange.NSE,
        asset_type=AssetType.EQUITY,
        isin="INE040A01034",
        lot_size=1,
        tick_size=0.05,
        currency="INR",
    ),
    Instrument(
        symbol="ICICIBANK",
        name="ICICI Bank Limited",
        exchange=Exchange.NSE,
        asset_type=AssetType.EQUITY,
        isin="INE090A01021",
        lot_size=1,
        tick_size=0.05,
        currency="INR",
    ),
    Instrument(
        symbol="SBIN",
        name="State Bank of India",
        exchange=Exchange.NSE,
        asset_type=AssetType.EQUITY,
        isin="INE062A01020",
        lot_size=1,
        tick_size=0.05,
        currency="INR",
    ),
    Instrument(
        symbol="BHARTIARTL",
        name="Bharti Airtel Limited",
        exchange=Exchange.NSE,
        asset_type=AssetType.EQUITY,
        isin="INE397D01024",
        lot_size=1,
        tick_size=0.05,
        currency="INR",
    ),
    Instrument(
        symbol="ITC",
        name="ITC Limited",
        exchange=Exchange.NSE,
        asset_type=AssetType.EQUITY,
        isin="INE154A01025",
        lot_size=1,
        tick_size=0.05,
        currency="INR",
    ),
    Instrument(
        symbol="KOTAKBANK",
        name="Kotak Mahindra Bank Limited",
        exchange=Exchange.NSE,
        asset_type=AssetType.EQUITY,
        isin="INE237A01028",
        lot_size=1,
        tick_size=0.05,
        currency="INR",
    ),
    Instrument(
        symbol="LT",
        name="Larsen & Toubro Limited",
        exchange=Exchange.NSE,
        asset_type=AssetType.EQUITY,
        isin="INE018A01030",
        lot_size=1,
        tick_size=0.05,
        currency="INR",
    ),
]


class TejHQDataProvider(MarketDataProvider):
    """TejHQ market data provider for NSE and BSE equities.

    Features:
    - Official bhavcopy-backed EOD OHLCV data directly from exchanges
    - Robust error handling for auth, rate limits, and network errors
    - Auditable data provenance labeled as historical research
    - Supports keyless queries and authenticated queries with TEJHQ_API_KEY
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key if api_key is not None else settings.tejhq_api_key
        self._base_url = base_url
        self._timeout = timeout

    @property
    def provider_name(self) -> str:
        return "TejHQ Indian Market Data Provider (EOD Historical)"

    @property
    def is_synthetic(self) -> bool:
        return False

    @property
    def data_mode(self) -> DataMode:
        return DataMode.HISTORICAL_RESEARCH

    @property
    def has_api_key(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    def _get_client_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"timeout": self._timeout}
        if self._base_url:
            kwargs["base_url"] = self._base_url
        if self.has_api_key:
            kwargs["api_key"] = self._api_key.strip()
        return kwargs

    def _normalize_exchange(self, exchange: Exchange) -> str:
        """Map Exchange enum to TejHQ exchange string ('nse' or 'bse')."""
        if exchange == Exchange.BSE:
            return "bse"
        # NSE and any other fallback map to nse
        return "nse"

    async def get_instruments(
        self, exchange: Exchange | None = None, asset_type: AssetType | None = None
    ) -> list[Instrument]:
        """List benchmark instruments available for TejHQ."""
        instruments = TEJHQ_BENCHMARK_INSTRUMENTS.copy()
        if exchange is not None:
            instruments = [i for i in instruments if i.exchange == exchange]
        if asset_type is not None:
            instruments = [i for i in instruments if i.asset_type == asset_type]
        return instruments

    async def get_instrument(self, symbol: str, exchange: Exchange) -> Instrument | None:
        """Get metadata for a specific instrument, resolving ISIN when available."""
        clean_symbol = symbol.strip().upper()
        # Check benchmark instruments first
        for inst in TEJHQ_BENCHMARK_INSTRUMENTS:
            if inst.symbol == clean_symbol and inst.exchange == exchange:
                return inst

        # Try resolving via TejHQ API if key is present
        try:
            from tej import AsyncClient

            ex_str = self._normalize_exchange(exchange)
            async with AsyncClient(**self._get_client_kwargs()) as client:
                records = await client.symbols(ex_str, symbol=clean_symbol)
                if records:
                    rec = records[0]
                    isin = rec.get("isin", "")
                    return Instrument(
                        symbol=clean_symbol,
                        name=f"{clean_symbol} (NSE/BSE Listed)",
                        exchange=exchange,
                        asset_type=AssetType.EQUITY,
                        isin=isin,
                        lot_size=1,
                        tick_size=0.05,
                        currency="INR",
                    )
        except Exception as exc:
            logger.debug(
                "tejhq_symbol_lookup_unresolved",
                symbol=clean_symbol,
                error=str(exc),
            )

        # Fallback return a minimal instrument
        return Instrument(
            symbol=clean_symbol,
            name=clean_symbol,
            exchange=exchange,
            asset_type=AssetType.EQUITY,
        )

    async def get_ohlcv(
        self,
        symbol: str,
        exchange: Exchange,
        timeframe: Timeframe,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Fetch End-of-Day (EOD) OHLCV data from TejHQ.

        Args:
            symbol: Ticker symbol (e.g. 'RELIANCE', 'TCS').
            exchange: Exchange (Exchange.NSE or Exchange.BSE).
            timeframe: Must be Timeframe.DAILY (TejHQ provides EOD bhavcopy data).
            start_date: Inclusive start date.
            end_date: Inclusive end date.

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume, symbol, is_synthetic.
            Sorted chronologically ascending by timestamp.
        """
        if timeframe != Timeframe.DAILY:
            raise ValueError(
                f"TejHQ provider supplies End-of-Day (EOD) bhavcopy data only. "
                f"Requested timeframe '{timeframe.value}' is not supported. "
                "Intraday tick data is never synthesized or mislabeled as EOD."
            )

        clean_symbol = symbol.strip().upper()
        ex_str = self._normalize_exchange(exchange)

        empty_df = pd.DataFrame(
            columns=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "symbol",
                "is_synthetic",
            ]
        )

        try:
            from tej import AsyncClient
            from tej.exceptions import AuthError, NotFoundError, RateLimitError, TejError

            async with AsyncClient(**self._get_client_kwargs()) as client:
                rows = await client.ohlcv(
                    symbol=clean_symbol,
                    exchange=ex_str,
                    from_=start_date.isoformat(),
                    to=end_date.isoformat(),
                )

        except AuthError as exc:
            logger.error("tejhq_auth_failed", error="Invalid or revoked TEJHQ_API_KEY")
            raise PermissionError(
                "TejHQ authentication failed. Please verify your TEJHQ_API_KEY."
            ) from exc

        except RateLimitError as exc:
            logger.warning("tejhq_rate_limit_exceeded", symbol=clean_symbol)
            raise RuntimeError(
                "TejHQ rate limit exceeded (Free tier: 300 req/min, 1000 req/day)."
            ) from exc

        except NotFoundError:
            logger.info("tejhq_symbol_not_found", symbol=clean_symbol, exchange=ex_str)
            return empty_df

        except TejError as exc:
            logger.error("tejhq_api_error", symbol=clean_symbol, error=str(exc))
            raise RuntimeError(f"TejHQ API error: {exc}") from exc

        except Exception as exc:
            logger.error("tejhq_unexpected_error", symbol=clean_symbol, error=str(exc))
            raise RuntimeError(f"Failed to fetch market data from TejHQ: {exc}") from exc

        if not rows:
            return empty_df

        # Normalize rows into a pandas DataFrame conforming to platform contracts
        df = pd.DataFrame(rows)

        # Parse date -> timestamp
        if "date" in df.columns:
            df["timestamp"] = pd.to_datetime(df["date"])
        elif "timestamp" not in df.columns:
            df["timestamp"] = pd.date_range(start=start_date, periods=len(df), freq="D")

        # Ensure numeric columns
        for col in ["open", "high", "low", "close"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)

        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)

        df["symbol"] = clean_symbol
        df["is_synthetic"] = False

        # Sort ascending chronologically
        df = df.sort_values(by="timestamp", ascending=True).reset_index(drop=True)

        # Standard required columns
        standard_cols = [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "symbol",
            "is_synthetic",
        ]
        # Preserve extra TejHQ fields if available (turnover, trades, last, prev_close)
        extra_cols = [c for c in df.columns if c not in standard_cols and c != "date"]
        final_cols = standard_cols + extra_cols
        return df[final_cols]

    async def get_status(self) -> ProviderStatus:
        """Check TejHQ API availability and account quota status."""
        try:
            from tej import AsyncClient
            from tej.exceptions import AuthError, TejError

            async with AsyncClient(**self._get_client_kwargs()) as client:
                health = await client.health()
                is_healthy = health.get("status") == "ok"

                account_info = ""
                if self.has_api_key:
                    try:
                        me = await client.me()
                        tier = me.get("tier", "unknown")
                        usage = me.get("usage_today", {})
                        used = usage.get("used", 0)
                        limit = usage.get("limit", 0)
                        account_info = f" (Tier: {tier}, Used: {used}/{limit})"
                    except AuthError:
                        return ProviderStatus(
                            provider_name=self.provider_name,
                            is_available=False,
                            data_mode=self.data_mode,
                            error_message="TEJHQ_API_KEY is invalid or expired",
                        )

                return ProviderStatus(
                    provider_name=f"{self.provider_name}{account_info}",
                    is_available=is_healthy,
                    data_mode=self.data_mode,
                    error_message="" if is_healthy else "TejHQ health check failed",
                )

        except Exception as exc:
            return ProviderStatus(
                provider_name=self.provider_name,
                is_available=False,
                data_mode=self.data_mode,
                error_message=f"TejHQ unavailable: {exc}",
            )
