"""Momentum Continuation Breakout Intraday Strategy.

Identifies multi-period breakout continuation setups where price makes a new high
with RSI in the optimal acceleration band (55 to 70) and volume expansion.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from pydantic import Field

from app.quant.indicators.core import rsi, sma
from app.quant.strategies.base import (
    BaseStrategy,
    Signal,
    SignalDirection,
    StrategyParameters,
)


class MomentumBreakoutParameters(StrategyParameters):
    """Parameters for Momentum Breakout Strategy."""

    breakout_lookback: int = Field(default=20, description="Bars to determine channel breakout level")
    rsi_min: float = Field(default=55.0, description="Minimum RSI for momentum confirmation")
    rsi_max: float = Field(default=72.0, description="Maximum RSI to avoid buying overextended exhausts")
    volume_multiplier: float = Field(default=1.3, description="Minimum volume surge vs 20 SMA")
    risk_reward_ratio: float = Field(default=2.0, description="Target distance multiplier relative to risk")


class MomentumBreakoutStrategy(BaseStrategy):
    """Momentum Continuation Breakout Strategy for Intraday Equities."""

    def name(self) -> str:
        return "momentum_breakout_v1"

    def description(self) -> str:
        return "Multi-period breakout with RSI acceleration (55-72) and volume expansion."

    def min_bars_required(self) -> int:
        return 25

    def generate_signals(
        self, df: pd.DataFrame, parameters: StrategyParameters | None = None
    ) -> list[Signal]:
        params = parameters if isinstance(parameters, MomentumBreakoutParameters) else MomentumBreakoutParameters()

        if not self.validate_data(df):
            return []

        symbol = df["symbol"].iloc[0] if "symbol" in df.columns else "UNKNOWN"
        signals: list[Signal] = []

        close = df["close"]
        high = df["high"]
        volume = df["volume"]

        rsi_series = rsi(close, 14)
        vol_sma = sma(volume, 20)

        lookback = params.breakout_lookback

        for i in range(max(lookback, 20), len(df)):
            curr_bar = df.iloc[i]
            prev_bar = df.iloc[i - 1]
            c_price = float(curr_bar["close"])
            c_vol = float(curr_bar["volume"])
            avg_vol = float(vol_sma.iloc[i]) if not np.isnan(vol_sma.iloc[i]) else 1.0
            rsi_val = float(rsi_series.iloc[i]) if not np.isnan(rsi_series.iloc[i]) else 50.0

            # Prior high over lookback window (excluding current bar)
            prior_high = float(high.iloc[i - lookback : i].max())

            ts = curr_bar["timestamp"]
            if not isinstance(ts, datetime):
                ts = pd.Timestamp(ts).to_pydatetime()

            # Conditions:
            # 1. Price closes above prior lookback high (clean breakout)
            # 2. RSI in momentum sweet spot (55 - 72)
            # 3. Volume is above average
            is_breakout = c_price > prior_high and float(prev_bar["close"]) <= prior_high
            has_momentum = params.rsi_min <= rsi_val <= params.rsi_max
            has_vol = c_vol >= (avg_vol * params.volume_multiplier) if avg_vol > 0 else True

            if is_breakout and has_momentum and has_vol:
                stop_loss = round(prior_high * 0.993, 2)
                risk = c_price - stop_loss
                if risk <= 0:
                    risk = c_price * 0.005
                take_profit = round(c_price + (risk * params.risk_reward_ratio), 2)

                signals.append(
                    Signal(
                        symbol=symbol,
                        direction=SignalDirection.BUY,
                        strength=0.88,
                        timestamp=ts,
                        strategy_name=self.name(),
                        timeframe="5m",
                        entry_price=round(c_price, 2),
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        metadata={
                            "breakout_level": round(prior_high, 2),
                            "rsi": round(rsi_val, 2),
                            "volume_ratio": round(c_vol / avg_vol, 2) if avg_vol > 0 else 1.0,
                            "invalidation_level": stop_loss,
                        },
                    )
                )

        return signals
