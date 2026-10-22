"""Unit tests for Market Regime Detection and Whole-Market Scanner."""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from app.quant.regime import MarketRegime, MarketRegimeDetector
from app.quant.scanner import WholeMarketScanner, SetupStatus
from app.quant.strategies.orb import OpeningRangeBreakoutStrategy
from app.quant.strategies.vwap_pullback import VWAPPullbackStrategy


def generate_regime_df(trend_type: str = "bullish", n_bars: int = 60) -> pd.DataFrame:
    base_price = 1000.0
    dates = [datetime(2026, 1, 1) + timedelta(minutes=5 * i) for i in range(n_bars)]
    
    if trend_type == "bullish":
        # Strongly upward trend
        closes = [base_price * (1.0 + 0.005 * i) for i in range(n_bars)]
    elif trend_type == "bearish":
        # Strongly downward trend
        closes = [base_price * (1.0 - 0.005 * i) for i in range(n_bars)]
    elif trend_type == "high_vol":
        # Wild oscillations
        closes = [base_price + (100.0 * (1 if i % 2 == 0 else -1)) for i in range(n_bars)]
    else:
        # Flat range-bound
        closes = [base_price + (0.5 * (1 if i % 2 == 0 else -1)) for i in range(n_bars)]

    highs = [c * 1.002 for c in closes]
    lows = [c * 0.998 for c in closes]
    opens = [c * 1.001 for c in closes]
    volumes = [150_000 for _ in range(n_bars)]

    return pd.DataFrame({
        "timestamp": dates,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
        "symbol": "NSE_TEST",
    })


def test_market_regime_detection():
    detector = MarketRegimeDetector()

    # 1. Bullish regime
    bull_df = generate_regime_df("bullish", 60)
    res_bull = detector.detect(bull_df, "NSE_TEST")
    assert res_bull.regime == MarketRegime.TRENDING_BULLISH
    assert res_bull.confidence >= 0.70

    # 2. Bearish regime
    bear_df = generate_regime_df("bearish", 60)
    res_bear = detector.detect(bear_df, "NSE_TEST")
    assert res_bear.regime == MarketRegime.TRENDING_BEARISH
    assert res_bear.confidence >= 0.70

    # 3. Insufficient data -> UNKNOWN
    res_short = detector.detect(bull_df.iloc[:10], "NSE_TEST")
    assert res_short.regime == MarketRegime.UNKNOWN
    assert res_short.confidence == 0.0


def test_opening_range_breakout_strategy():
    strategy = OpeningRangeBreakoutStrategy()
    df = generate_regime_df("bullish", 40)
    signals = strategy.generate_signals(df)
    assert isinstance(signals, list)
    for sig in signals:
        assert sig.entry_price is not None
        assert sig.stop_loss is not None
        assert sig.take_profit is not None
        assert sig.take_profit > sig.entry_price > sig.stop_loss


def test_vwap_pullback_strategy():
    strategy = VWAPPullbackStrategy()
    df = generate_regime_df("bullish", 45)
    signals = strategy.generate_signals(df)
    assert isinstance(signals, list)


def test_whole_market_scanner_no_trade():
    scanner = WholeMarketScanner(min_daily_volume=500_000)  # High filter to trigger no trade
    # Test data has volume 150_000, so it will be filtered out
    data_map = {"RELIANCE": generate_regime_df("bullish", 40)}
    result = scanner.scan(data_map)
    assert result.has_setups is False
    assert result.no_trade_reason is not None
    assert "No trade recommended today" in result.no_trade_reason
