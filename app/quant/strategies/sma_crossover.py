"""Example SMA crossover strategy — demonstrates the strategy interface.

This is a simple moving-average crossover strategy for testing purposes.
It is NOT recommended for real trading without thorough backtesting
and risk analysis.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
from pydantic import Field

from app.quant.indicators.core import sma
from app.quant.strategies.base import (
    BaseStrategy,
    Signal,
    SignalDirection,
    StrategyParameters,
)


class SMACrossoverParams(StrategyParameters):
    """Parameters for the SMA Crossover strategy."""

    fast_period: int = Field(default=20, ge=2, description="Fast SMA period")
    slow_period: int = Field(default=50, ge=5, description="Slow SMA period")


class SMACrossoverStrategy(BaseStrategy):
    """Simple Moving Average crossover strategy.

    Generates a BUY signal when the fast SMA crosses above the slow SMA,
    and a SELL signal when the fast SMA crosses below the slow SMA.

    ⚠️ This is a demonstration strategy. Past performance of any strategy
    does not guarantee future results. Do not use without proper
    backtesting and risk management.
    """

    def __init__(self, params: SMACrossoverParams | None = None):
        self._params = params or SMACrossoverParams()

    def name(self) -> str:
        return f"SMA_Crossover_{self._params.fast_period}_{self._params.slow_period}"

    def description(self) -> str:
        return (
            f"SMA Crossover: Buy when SMA({self._params.fast_period}) crosses above "
            f"SMA({self._params.slow_period}), sell on cross below."
        )

    def min_bars_required(self) -> int:
        return self._params.slow_period + 1

    def generate_signals(
        self, df: pd.DataFrame, parameters: StrategyParameters | None = None
    ) -> list[Signal]:
        params = parameters if isinstance(parameters, SMACrossoverParams) else self._params

        if not self.validate_data(df):
            return []

        # Compute indicators — operates on a copy, never modifies input
        close = df["close"]
        fast_sma = sma(close, params.fast_period)
        slow_sma = sma(close, params.slow_period)

        # Detect crossovers
        signals: list[Signal] = []
        prev_fast = None
        prev_slow = None

        for i in range(len(df)):
            curr_fast = fast_sma.iloc[i]
            curr_slow = slow_sma.iloc[i]

            if pd.isna(curr_fast) or pd.isna(curr_slow):
                prev_fast = curr_fast
                prev_slow = curr_slow
                continue

            if prev_fast is not None and prev_slow is not None:
                if not pd.isna(prev_fast) and not pd.isna(prev_slow):
                    # Bullish crossover: fast crosses above slow
                    if prev_fast <= prev_slow and curr_fast > curr_slow:
                        ts = df["timestamp"].iloc[i]
                        if not isinstance(ts, datetime):
                            ts = pd.Timestamp(ts).to_pydatetime()
                        signals.append(Signal(
                            symbol=df["symbol"].iloc[i] if "symbol" in df.columns else "",
                            direction=SignalDirection.BUY,
                            strength=min(1.0, abs(curr_fast - curr_slow) / curr_slow * 10),
                            timestamp=ts,
                            strategy_name=self.name(),
                            entry_price=float(close.iloc[i]),
                            metadata={"fast_sma": float(curr_fast), "slow_sma": float(curr_slow)},
                        ))

                    # Bearish crossover: fast crosses below slow
                    elif prev_fast >= prev_slow and curr_fast < curr_slow:
                        ts = df["timestamp"].iloc[i]
                        if not isinstance(ts, datetime):
                            ts = pd.Timestamp(ts).to_pydatetime()
                        signals.append(Signal(
                            symbol=df["symbol"].iloc[i] if "symbol" in df.columns else "",
                            direction=SignalDirection.SELL,
                            strength=min(1.0, abs(curr_fast - curr_slow) / curr_slow * 10),
                            timestamp=ts,
                            strategy_name=self.name(),
                            entry_price=float(close.iloc[i]),
                            metadata={"fast_sma": float(curr_fast), "slow_sma": float(curr_slow)},
                        ))

            prev_fast = curr_fast
            prev_slow = curr_slow

        return signals
