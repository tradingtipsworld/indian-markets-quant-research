"""Unit tests for quantitative technical indicators."""

import numpy as np
import pandas as pd
import pytest

from app.quant.indicators.core import atr, bollinger_bands, ema, macd, rsi, sma, vwap


def test_sma_calculation():
    s = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    res = sma(s, 3)
    assert pd.isna(res.iloc[0])
    assert pd.isna(res.iloc[1])
    assert res.iloc[2] == 20.0
    assert res.iloc[3] == 30.0
    assert res.iloc[4] == 40.0


def test_rsi_bounds(synthetic_ohlcv_df):
    close = synthetic_ohlcv_df["close"]
    res = rsi(close, 14)
    valid = res.dropna()
    assert (valid >= 0.0).all()
    assert (valid <= 100.0).all()


def test_macd_structure(synthetic_ohlcv_df):
    close = synthetic_ohlcv_df["close"]
    res = macd(close)
    assert "macd" in res.columns
    assert "signal" in res.columns
    assert "histogram" in res.columns
    # histogram should equal macd - signal
    valid = res.dropna()
    diff = (valid["macd"] - valid["signal"]) - valid["histogram"]
    assert np.allclose(diff, 0.0)


def test_bollinger_bands_ordering(synthetic_ohlcv_df):
    close = synthetic_ohlcv_df["close"]
    bb = bollinger_bands(close, period=20, std_dev=2.0).dropna()
    assert (bb["upper"] >= bb["middle"]).all()
    assert (bb["middle"] >= bb["lower"]).all()
