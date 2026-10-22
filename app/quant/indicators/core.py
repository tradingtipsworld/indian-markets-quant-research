"""Core technical indicators — deterministic, tested implementations.

All indicator functions operate on pandas Series or DataFrames
and return new Series/DataFrames without modifying inputs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average.

    Args:
        series: Price series (typically close prices).
        period: Number of periods for the average.

    Returns:
        SMA series. First (period-1) values will be NaN.
    """
    if period < 1:
        raise ValueError(f"SMA period must be >= 1, got {period}")
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average.

    Args:
        series: Price series.
        period: Number of periods (span) for the EMA.

    Returns:
        EMA series.
    """
    if period < 1:
        raise ValueError(f"EMA period must be >= 1, got {period}")
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index.

    Uses the standard Wilder smoothing method.

    Args:
        series: Price series (typically close prices).
        period: RSI lookback period.

    Returns:
        RSI series with values between 0 and 100.
    """
    if period < 1:
        raise ValueError(f"RSI period must be >= 1, got {period}")

    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_values = 100.0 - (100.0 / (1.0 + rs))

    return rsi_values


def macd(
    series: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> pd.DataFrame:
    """Moving Average Convergence Divergence.

    Args:
        series: Price series.
        fast_period: Fast EMA period.
        slow_period: Slow EMA period.
        signal_period: Signal line EMA period.

    Returns:
        DataFrame with columns: macd, signal, histogram.
    """
    fast_ema = ema(series, fast_period)
    slow_ema = ema(series, slow_period)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal_period)
    histogram = macd_line - signal_line

    return pd.DataFrame({
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram,
    })


def bollinger_bands(
    series: pd.Series, period: int = 20, std_dev: float = 2.0
) -> pd.DataFrame:
    """Bollinger Bands.

    Args:
        series: Price series.
        period: Moving average period.
        std_dev: Number of standard deviations for bands.

    Returns:
        DataFrame with columns: upper, middle, lower.
    """
    middle = sma(series, period)
    std = series.rolling(window=period, min_periods=period).std()

    return pd.DataFrame({
        "upper": middle + (std * std_dev),
        "middle": middle,
        "lower": middle - (std * std_dev),
    })


def atr(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.Series:
    """Average True Range.

    Args:
        high: High price series.
        low: Low price series.
        close: Close price series.
        period: ATR period.

    Returns:
        ATR series.
    """
    if period < 1:
        raise ValueError(f"ATR period must be >= 1, got {period}")

    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    return true_range.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()


def vwap(
    high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series
) -> pd.Series:
    """Volume Weighted Average Price (cumulative).

    Args:
        high: High price series.
        low: Low price series.
        close: Close price series.
        volume: Volume series.

    Returns:
        Cumulative VWAP series.
    """
    typical_price = (high + low + close) / 3.0
    cumulative_tp_vol = (typical_price * volume).cumsum()
    cumulative_vol = volume.cumsum()
    return cumulative_tp_vol / cumulative_vol.replace(0, np.nan)
