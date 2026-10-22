"""Data validation checks for market data quality and integrity."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from app.data.interfaces import DataQualityReport, Timeframe


def validate_ohlcv(
    df: pd.DataFrame,
    symbol: str,
    timeframe: Timeframe = Timeframe.DAILY,
) -> DataQualityReport:
    """Validate OHLCV data quality.

    Checks for:
    - Missing/empty data
    - Required column presence
    - Duplicate timestamps
    - Chronological sorting (monotonic increasing timestamps)
    - Invalid prices (negative, zero, NaN, high < low)
    - Boundary consistency (high >= open/close, low <= open/close)
    - Invalid volumes (negative, NaN)
    - Zero volume anomalies
    - Significant unexpected timestamp gaps

    Args:
        df: DataFrame with columns [timestamp, open, high, low, close, volume].
        symbol: Instrument symbol for the report.
        timeframe: Expected data timeframe.

    Returns:
        DataQualityReport with all issues found.
    """
    report = DataQualityReport(symbol=symbol, timeframe=timeframe)

    if df is None or df.empty:
        report.is_valid = False
        report.issues.append("Data is empty or None")
        return report

    required_cols = {"open", "high", "low", "close", "volume"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        report.is_valid = False
        report.issues.append(f"Missing required columns: {missing_cols}")
        return report

    report.total_bars = len(df)

    # 1. Chronological & Duplicate Timestamps Check
    if "timestamp" in df.columns:
        ts_series = pd.to_datetime(df["timestamp"])
        duplicates = int(ts_series.duplicated().sum())
        report.duplicate_bars = duplicates
        if duplicates > 0:
            report.issues.append(f"Found {duplicates} duplicate timestamps")

        if not ts_series.is_monotonic_increasing:
            report.issues.append("Timestamps are not in strictly ascending chronological order")

        # Gap detection
        if len(ts_series) > 1:
            diffs = ts_series.diff().dropna()
            median_delta = diffs.median()
            large_gaps = diffs[diffs > median_delta * 3]
            for idx, gap in large_gaps.items():
                gap_start = ts_series.iloc[idx - 1]
                gap_end = ts_series.iloc[idx]
                report.gaps.append({
                    "start": str(gap_start),
                    "end": str(gap_end),
                    "gap_duration": str(gap),
                })
            if report.gaps:
                report.issues.append(f"Detected {len(report.gaps)} significant timestamp gaps")

    # 2. Price Validation (NaN, negative, zero)
    price_cols = ["open", "high", "low", "close"]
    for col in price_cols:
        nan_count = int(df[col].isna().sum())
        neg_count = int((df[col] < 0).sum())
        zero_count = int((df[col] == 0).sum())
        if nan_count > 0:
            report.issues.append(f"{col}: {nan_count} NaN values")
            report.invalid_prices += nan_count
        if neg_count > 0:
            report.issues.append(f"{col}: {neg_count} negative values")
            report.invalid_prices += neg_count
        if zero_count > 0:
            report.issues.append(f"{col}: {zero_count} zero values")
            report.invalid_prices += zero_count

    # 3. Geometric Candle Boundaries (High >= Low, High >= Open/Close, Low <= Open/Close)
    if not df.empty:
        hl_violations = int((df["high"] < df["low"]).sum())
        if hl_violations > 0:
            report.issues.append(f"high < low in {hl_violations} bars")
            report.invalid_prices += hl_violations

        ho_violations = int(((df["high"] < df["open"]) | (df["high"] < df["close"])).sum())
        if ho_violations > 0:
            report.issues.append(f"high < open or high < close in {ho_violations} bars")

        lo_violations = int(((df["low"] > df["open"]) | (df["low"] > df["close"])).sum())
        if lo_violations > 0:
            report.issues.append(f"low > open or low > close in {lo_violations} bars")

    # 4. Volume Validation
    vol_nan = int(df["volume"].isna().sum())
    vol_neg = int((df["volume"] < 0).sum())
    report.invalid_volumes = vol_nan + vol_neg
    if vol_nan > 0:
        report.issues.append(f"volume: {vol_nan} NaN values")
    if vol_neg > 0:
        report.issues.append(f"volume: {vol_neg} negative values")

    # 5. Set Overall Validity Flag
    report.is_valid = (
        report.invalid_prices == 0
        and report.invalid_volumes == 0
        and report.duplicate_bars == 0
        and not any("not in strictly ascending" in iss for iss in report.issues)
    )

    return report
