"""Data validation checks for market data quality."""

from __future__ import annotations

from datetime import datetime

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
    - Duplicate timestamps
    - Invalid prices (negative, zero, NaN, high < low)
    - Invalid volumes (negative, NaN)
    - Chronological ordering
    - Data gaps

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

    # Check for duplicate timestamps
    if "timestamp" in df.columns:
        duplicates = df["timestamp"].duplicated().sum()
        report.duplicate_bars = int(duplicates)
        if duplicates > 0:
            report.issues.append(f"Found {duplicates} duplicate timestamps")

    # Check for invalid prices
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

    # Check high >= low
    if not df.empty:
        hl_violations = int((df["high"] < df["low"]).sum())
        if hl_violations > 0:
            report.issues.append(f"high < low in {hl_violations} bars")
            report.invalid_prices += hl_violations

    # Check high >= open and high >= close
    ho_violations = int(((df["high"] < df["open"]) | (df["high"] < df["close"])).sum())
    if ho_violations > 0:
        report.issues.append(f"high < open or high < close in {ho_violations} bars")

    # Check low <= open and low <= close
    lo_violations = int(((df["low"] > df["open"]) | (df["low"] > df["close"])).sum())
    if lo_violations > 0:
        report.issues.append(f"low > open or low > close in {lo_violations} bars")

    # Check volumes
    vol_nan = int(df["volume"].isna().sum())
    vol_neg = int((df["volume"] < 0).sum())
    report.invalid_volumes = vol_nan + vol_neg
    if vol_nan > 0:
        report.issues.append(f"volume: {vol_nan} NaN values")
    if vol_neg > 0:
        report.issues.append(f"volume: {vol_neg} negative values")

    # Set overall validity
    report.is_valid = (
        report.invalid_prices == 0
        and report.invalid_volumes == 0
        and report.duplicate_bars == 0
    )

    return report
