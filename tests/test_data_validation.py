"""Unit tests for market data validation checks."""

from datetime import datetime
import pandas as pd
import pytest

from app.data.interfaces import Timeframe
from app.data.validation import validate_ohlcv


def test_validate_ohlcv_detects_nan():
    df = pd.DataFrame({
        "timestamp": [datetime(2025, 1, 1), datetime(2025, 1, 2)],
        "open": [100.0, None],
        "high": [105.0, 110.0],
        "low": [95.0, 90.0],
        "close": [102.0, 108.0],
        "volume": [1000, 2000],
    })
    report = validate_ohlcv(df, "TEST_SYM")
    assert report.is_valid is False
    assert report.invalid_prices > 0


def test_validate_ohlcv_detects_high_less_than_low():
    df = pd.DataFrame({
        "timestamp": [datetime(2025, 1, 1)],
        "open": [100.0],
        "high": [90.0],  # Invalid: high < low
        "low": [95.0],
        "close": [92.0],
        "volume": [1000],
    })
    report = validate_ohlcv(df, "TEST_SYM")
    assert report.is_valid is False
    assert any("high < low" in issue for issue in report.issues)


def test_validate_clean_synthetic_data(synthetic_ohlcv_df):
    report = validate_ohlcv(synthetic_ohlcv_df, "SYNTH_RELIANCE")
    assert report.is_valid is True
    assert report.total_bars == len(synthetic_ohlcv_df)
    assert len(report.issues) == 0
