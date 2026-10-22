"""Tests verifying synthetic market data determinism and cross-process reproducibility."""

from datetime import date
import json
import subprocess
import sys
import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

from app.data.interfaces import Timeframe
from app.data.providers.synthetic import (
    SYNTHETIC_INSTRUMENTS,
    SyntheticDataProvider,
    generate_synthetic_ohlcv,
)


def test_repeated_calls_identical_output():
    """Verify that repeated calls with identical inputs yield identical DataFrames."""
    start = date(2025, 1, 1)
    end = date(2025, 3, 1)

    df1 = generate_synthetic_ohlcv("SYNTH_RELIANCE", start, end, Timeframe.DAILY, seed=42)
    df2 = generate_synthetic_ohlcv("SYNTH_RELIANCE", start, end, Timeframe.DAILY, seed=42)

    assert_frame_equal(df1, df2)


def test_cross_process_reproducibility():
    """Verify that separate Python processes produce bit-for-bit identical results.

    Tests that process-randomized hash seeds (PYTHONHASHSEED) do not alter the output.
    """
    start = date(2025, 1, 1)
    end = date(2025, 2, 1)

    # In-process generation
    df_local = generate_synthetic_ohlcv("SYNTH_INFY", start, end, Timeframe.DAILY, seed=99)
    local_closes = df_local["close"].tolist()

    # Out-of-process generation via subprocess with randomized hash seed
    script = (
        "import json, sys; "
        "from datetime import date; "
        "from app.data.interfaces import Timeframe; "
        "from app.data.providers.synthetic import generate_synthetic_ohlcv; "
        "df = generate_synthetic_ohlcv('SYNTH_INFY', date(2025, 1, 1), date(2025, 2, 1), Timeframe.DAILY, seed=99); "
        "print(json.dumps(df['close'].tolist()))"
    )

    cmd = [sys.executable, "-c", script]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    subprocess_closes = json.loads(result.stdout.strip())

    assert local_closes == subprocess_closes


def test_different_symbols_produce_different_sequences():
    """Verify that different symbols generate distinct deterministic price series."""
    start = date(2025, 1, 1)
    end = date(2025, 3, 1)

    df_rel = generate_synthetic_ohlcv("SYNTH_RELIANCE", start, end, Timeframe.DAILY, seed=42)
    df_tcs = generate_synthetic_ohlcv("SYNTH_TCS", start, end, Timeframe.DAILY, seed=42)

    assert not df_rel["close"].equals(df_tcs["close"])


def test_output_schema_and_synthetic_marker():
    """Verify that output adheres to the expected schema and is explicitly marked synthetic."""
    start = date(2025, 1, 1)
    end = date(2025, 1, 15)

    df = generate_synthetic_ohlcv("SYNTH_HDFCBANK", start, end, Timeframe.DAILY, seed=10)

    expected_cols = ["timestamp", "open", "high", "low", "close", "volume", "symbol", "is_synthetic"]
    assert list(df.columns) == expected_cols
    assert (df["is_synthetic"] == True).all()  # noqa: E712
    assert (df["high"] >= df["low"]).all()
    assert (df["volume"] >= 0).all()


@pytest.mark.asyncio
async def test_provider_interface_conformance():
    """Verify SyntheticDataProvider conforms to MarketDataProvider contract."""
    provider = SyntheticDataProvider()
    assert provider.is_synthetic is True
    assert "SYNTHETIC" in provider.provider_name.upper()

    instruments = await provider.get_instruments()
    assert len(instruments) == len(SYNTHETIC_INSTRUMENTS)
