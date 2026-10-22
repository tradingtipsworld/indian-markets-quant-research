"""Market data API routes."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.data.interfaces import Exchange, Timeframe
from app.data.providers.synthetic import (
    SYNTHETIC_INSTRUMENTS,
    SyntheticDataProvider,
)
from app.data.validation import validate_ohlcv

router = APIRouter(prefix="/data", tags=["market_data"])
provider = SyntheticDataProvider()


@router.get("/instruments")
async def list_instruments():
    """List available market instruments (currently synthetic test fixtures)."""
    instruments = await provider.get_instruments()
    return {
        "count": len(instruments),
        "is_synthetic": True,
        "instruments": [i.model_dump() for i in instruments],
    }


@router.get("/ohlcv/{symbol}")
async def get_historical_ohlcv(
    symbol: str,
    days: int = Query(default=60, ge=5, le=365),
    timeframe: Timeframe = Timeframe.DAILY,
):
    """Retrieve historical OHLCV data for a symbol (synthetic fixture)."""
    end = date.today()
    start = end - timedelta(days=days)

    df = await provider.get_ohlcv(
        symbol=symbol,
        exchange=Exchange.SYNTHETIC,
        timeframe=timeframe,
        start_date=start,
        end_date=end,
    )

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data generated for symbol {symbol}")

    records = df.to_dict(orient="records")
    return {
        "symbol": symbol,
        "is_synthetic": True,
        "bars_count": len(records),
        "bars": records,
    }


@router.get("/validate/{symbol}")
async def validate_data_quality(symbol: str, days: int = 90):
    """Run data quality validation suite against symbol OHLCV records."""
    end = date.today()
    start = end - timedelta(days=days)
    df = await provider.get_ohlcv(
        symbol=symbol,
        exchange=Exchange.SYNTHETIC,
        timeframe=Timeframe.DAILY,
        start_date=start,
        end_date=end,
    )
    report = validate_ohlcv(df, symbol=symbol)
    return report.model_dump()
