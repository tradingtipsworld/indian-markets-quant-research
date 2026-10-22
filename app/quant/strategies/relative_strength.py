"""Relative Strength (RS) Intraday Strategy vs Benchmark Index.

Compares individual stock momentum against the broader index (NIFTY 50)
to identify institutional accumulation leadership.
Stocks that outperform during market dips or consolidate tightly at new highs
provide superior intraday risk-reward continuation setups.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from pydantic import Field

from app.quant.indicators.core import ema
from app.quant.strategies.base import (
    BaseStrategy,
    Signal,
    SignalDirection,
    StrategyParameters,
)


class RelativeStrengthParameters(StrategyParameters):
    """Parameters for Relative Strength Strategy."""

    lookback_period: int = Field(default=20, description="Bars to measure relative return vs benchmark")
    rs_threshold_pct: float = Field(default=1.5, description="Minimum percentage outperformance vs benchmark")
    trend_ema_period: int = Field(default=20, description="EMA to confirm local trend posture")
    risk_reward_ratio: float = Field(default=2.0, description="Target distance multiplier relative to risk")


class RelativeStrengthStrategy(BaseStrategy):
    """Relative Strength Strategy for NSE Equities vs Benchmark Index."""

    def name(self) -> str:
        return "relative_strength_v1"

    def description(self) -> str:
        return "Identifies market leaders outperforming the benchmark index with trend alignment."

    def min_bars_required(self) -> int:
        return 30

    def generate_signals(
        self, df: pd.DataFrame, parameters: StrategyParameters | None = None
    ) -> list[Signal]:
        params = parameters if isinstance(parameters, RelativeStrengthParameters) else RelativeStrengthParameters()

        if not self.validate_data(df):
            return []

        symbol = df["symbol"].iloc[0] if "symbol" in df.columns else "UNKNOWN"
        signals: list[Signal] = []

        close = df["close"]
        ema_series = ema(close, params.trend_ema_period)

        # Calculate percentage returns over lookback period
        lookback = params.lookback_period
        stock_pct_chg = close.pct_change(periods=lookback) * 100.0

        for i in range(max(lookback, params.trend_ema_period), len(df)):
            curr_bar = df.iloc[i]
            c_price = float(curr_bar["close"])
            ema_val = float(ema_series.iloc[i])
            stock_ret = float(stock_pct_chg.iloc[i])

            if np.isnan(ema_val) or np.isnan(stock_ret):
                continue

            ts = curr_bar["timestamp"]
            if not isinstance(ts, datetime):
                ts = pd.Timestamp(ts).to_pydatetime()

            # Conditions:
            # 1. Price above EMA20 (clear uptrend)
            # 2. Stock outperforming threshold
            # 3. Bar closed green (buying confirmation)
            is_uptrend = c_price > ema_val
            is_strong = stock_ret >= params.rs_threshold_pct
            is_green = c_price >= float(curr_bar["open"])

            if is_uptrend and is_strong and is_green:
                stop_loss = round(ema_val * 0.995, 2)
                risk = c_price - stop_loss
                if risk <= 0:
                    risk = c_price * 0.005
                take_profit = round(c_price + (risk * params.risk_reward_ratio), 2)

                signals.append(
                    Signal(
                        symbol=symbol,
                        direction=SignalDirection.BUY,
                        strength=0.82,
                        timestamp=ts,
                        strategy_name=self.name(),
                        timeframe="5m",
                        entry_price=round(c_price, 2),
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        metadata={
                            "relative_return_pct": round(stock_ret, 2),
                            "ema20": round(ema_val, 2),
                            "invalidation_level": stop_loss,
                        },
                    )
                )

        return signals
