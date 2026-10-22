"""Quantitative backtesting and strategy API routes."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.backtesting.engine import BacktestConfig, BacktestEngine
from app.data.interfaces import Exchange, Timeframe
from app.data.providers.synthetic import SyntheticDataProvider
from app.quant.strategies.sma_crossover import SMACrossoverParams, SMACrossoverStrategy
from app.reports.generator import ReportGenerator

router = APIRouter(prefix="/quant", tags=["quant"])
data_provider = SyntheticDataProvider()


class BacktestRunRequest(BaseModel):
    symbol: str = "SYNTH_RELIANCE"
    fast_period: int = Field(default=10, ge=2, le=50)
    slow_period: int = Field(default=30, ge=5, le=200)
    days: int = Field(default=180, ge=30, le=730)
    initial_capital: float = Field(default=1_000_000.0, ge=10_000.0)


@router.get("/strategies")
async def list_strategies():
    """List registered quantitative strategies."""
    return {
        "strategies": [
            {
                "id": "sma_crossover",
                "name": "SMA Crossover",
                "description": "Momentum moving average trend-following strategy",
                "parameters": {"fast_period": "integer >= 2", "slow_period": "integer >= 5"},
            }
        ]
    }


@router.post("/backtest/run")
async def run_backtest(req: BacktestRunRequest):
    """Execute historical backtest on synthetic fixture data."""
    end = date.today()
    start = end - timedelta(days=req.days)

    df = await data_provider.get_ohlcv(
        symbol=req.symbol,
        exchange=Exchange.SYNTHETIC,
        timeframe=Timeframe.DAILY,
        start_date=start,
        end_date=end,
    )

    if df.empty or len(df) <= req.slow_period:
        raise HTTPException(status_code=400, detail="Insufficient price bars for backtest period")

    strategy = SMACrossoverStrategy(
        SMACrossoverParams(fast_period=req.fast_period, slow_period=req.slow_period)
    )
    engine = BacktestEngine(BacktestConfig(initial_capital=req.initial_capital))
    result = engine.run(strategy, df)

    # Generate research report
    report = ReportGenerator.generate_strategy_report(result)

    return {
        "result": result.model_dump(),
        "report_markdown": report.markdown_content,
    }
