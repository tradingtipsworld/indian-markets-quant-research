"""Unit tests for Walk-Forward and Out-of-Sample Performance Validation."""

from datetime import date, timedelta
import pytest
import pandas as pd

from app.backtesting.engine import BacktestConfig
from app.backtesting.walk_forward import WalkForwardEvaluator, WalkForwardEvaluationResult
from app.core.exceptions import BacktestError
from app.data.interfaces import Timeframe
from app.data.providers.synthetic import generate_synthetic_ohlcv
from app.quant.strategies.sma_crossover import SMACrossoverParams, SMACrossoverStrategy


def test_walk_forward_evaluation_success():
    # Generate 180 days of price data
    end = date.today()
    start = end - timedelta(days=180)
    df = generate_synthetic_ohlcv("TEST_STOCK", start, end, Timeframe.DAILY)

    evaluator = WalkForwardEvaluator(in_sample_pct=0.70)
    strategy = SMACrossoverStrategy(SMACrossoverParams(fast_period=5, slow_period=15))

    result = evaluator.evaluate(strategy, df)

    assert isinstance(result, WalkForwardEvaluationResult)
    assert result.strategy_name == strategy.name()
    assert result.in_sample_bars > 0
    assert result.out_of_sample_bars > 0
    assert (result.in_sample_bars + result.out_of_sample_bars) == len(df)
    assert isinstance(result.robustness_ratio, float)
    assert isinstance(result.is_robust, bool)
    assert len(result.notes) > 0


def test_walk_forward_insufficient_bars_raises_error():
    # Only 10 bars (less than strategy requirement * 2)
    end = date.today()
    start = end - timedelta(days=10)
    df = generate_synthetic_ohlcv("TEST_SHORT", start, end, Timeframe.DAILY)

    evaluator = WalkForwardEvaluator(in_sample_pct=0.70)
    strategy = SMACrossoverStrategy(SMACrossoverParams(fast_period=10, slow_period=30))

    with pytest.raises(BacktestError):
        evaluator.evaluate(strategy, df)


def test_walk_forward_invalid_in_sample_ratio():
    with pytest.raises(ValueError):
        WalkForwardEvaluator(in_sample_pct=0.40)  # Must be >= 0.50

    with pytest.raises(ValueError):
        WalkForwardEvaluator(in_sample_pct=0.90)  # Must be <= 0.85
