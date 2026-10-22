"""Unit tests for backtesting engine and anti-lookahead execution."""

import pytest
from app.backtesting.engine import BacktestConfig, BacktestEngine
from app.quant.strategies.sma_crossover import SMACrossoverParams, SMACrossoverStrategy


def test_backtest_execution_flow(synthetic_ohlcv_df):
    strategy = SMACrossoverStrategy(SMACrossoverParams(fast_period=5, slow_period=15))
    engine = BacktestEngine(BacktestConfig(initial_capital=500_000.0))
    result = engine.run(strategy, synthetic_ohlcv_df)

    assert result.total_bars == len(synthetic_ohlcv_df)
    assert len(result.equity_curve) == len(synthetic_ohlcv_df)
    assert result.max_drawdown_pct >= 0.0
    assert result.final_equity > 0.0
