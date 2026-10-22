"""Market data API routes."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.data.interfaces import Exchange, Timeframe
from app.data.providers import get_market_data_provider
from app.data.validation import validate_ohlcv

router = APIRouter(prefix="/data", tags=["market_data"])


@router.get("/status")
async def get_market_data_status():
    """Get status and health of the active market data provider."""
    provider = get_market_data_provider()
    status = await provider.get_status()
    return status.model_dump()


@router.get("/instruments")
async def list_instruments(
    exchange: Exchange | None = None,
):
    """List available market instruments from the active provider."""
    provider = get_market_data_provider()
    instruments = await provider.get_instruments(exchange=exchange)
    return {
        "count": len(instruments),
        "provider": provider.provider_name,
        "is_synthetic": provider.is_synthetic,
        "data_mode": provider.data_mode.value,
        "instruments": [i.model_dump() for i in instruments],
    }


@router.get("/ohlcv/{symbol}")
async def get_historical_ohlcv(
    symbol: str,
    days: int = Query(default=60, ge=5, le=365),
    timeframe: Timeframe = Timeframe.DAILY,
    exchange: Exchange = Exchange.NSE,
):
    """Retrieve historical OHLCV data for a symbol from the active provider."""
    provider = get_market_data_provider()
    end = date.today()
    start = end - timedelta(days=days)

    target_exchange = Exchange.SYNTHETIC if provider.is_synthetic else exchange

    try:
        df = await provider.get_ohlcv(
            symbol=symbol,
            exchange=target_exchange,
            timeframe=timeframe,
            start_date=start,
            end_date=end,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for symbol {symbol}")

    records = df.to_dict(orient="records")
    return {
        "symbol": symbol,
        "provider": provider.provider_name,
        "is_synthetic": provider.is_synthetic,
        "data_mode": provider.data_mode.value,
        "bars_count": len(records),
        "bars": records,
    }


@router.get("/validate/{symbol}")
async def validate_data_quality(
    symbol: str,
    days: int = 90,
    exchange: Exchange = Exchange.NSE,
):
    """Run data quality validation suite against symbol OHLCV records."""
    provider = get_market_data_provider()
    end = date.today()
    start = end - timedelta(days=days)

    target_exchange = Exchange.SYNTHETIC if provider.is_synthetic else exchange

    try:
        df = await provider.get_ohlcv(
            symbol=symbol,
            exchange=target_exchange,
            timeframe=Timeframe.DAILY,
            start_date=start,
            end_date=end,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed to fetch data: {e}")

    report = validate_ohlcv(df, symbol=symbol)
    return report.model_dump()
