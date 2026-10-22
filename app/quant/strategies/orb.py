"""Opening Range Breakout (ORB) Intraday Strategy.

Calculates the high and low of the initial opening range (e.g. first 15 or 30 minutes).
Triggers an intraday setup when price breaks out above the range high with volume expansion,
with strict invalidation at the opening range midpoint or low.
"""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

import numpy as np
import pandas as pd
from pydantic import Field

from app.quant.indicators.core import sma
from app.quant.strategies.base import (
    BaseStrategy,
    Signal,
    SignalDirection,
    StrategyParameters,
)


class ORBParameters(StrategyParameters):
    """Parameters for Opening Range Breakout strategy."""

    range_bars: int = Field(default=6, description="Number of initial bars for the opening range (e.g. 6 x 5m = 30m)")
    volume_multiplier: float = Field(default=1.3, description="Minimum volume multiplier vs moving average")
    volume_period: int = Field(default=20, description="SMA period for average volume calculation")
    risk_reward_ratio: float = Field(default=2.0, description="Target distance multiplier relative to risk")


class OpeningRangeBreakoutStrategy(BaseStrategy):
    """Opening Range Breakout (ORB) Strategy for Intraday Equities."""

    def name(self) -> str:
        return "opening_range_breakout_v1"

    def description(self) -> str:
        return "Intraday breakout above the initial session opening range with volume expansion."

    def min_bars_required(self) -> int:
        return 25

    def generate_signals(
        self, df: pd.DataFrame, parameters: StrategyParameters | None = None
    ) -> list[Signal]:
        params = parameters if isinstance(parameters, ORBParameters) else ORBParameters()

        if not self.validate_data(df):
            return []

        symbol = df["symbol"].iloc[0] if "symbol" in df.columns else "UNKNOWN"
        signals: list[Signal] = []

        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]
        vol_sma = sma(volume, params.volume_period)

        # Determine opening range from the initial bars
        range_bars = min(params.range_bars, len(df) - 1)
        orb_high = float(high.iloc[:range_bars].max())
        orb_low = float(low.iloc[:range_bars].min())
        orb_mid = (orb_high + orb_low) / 2.0

        # Scan subsequent bars for breakout
        for i in range(range_bars, len(df)):
            curr_bar = df.iloc[i]
            prev_bar = df.iloc[i - 1]
            c_price = float(curr_bar["close"])
            p_price = float(prev_bar["close"])
            c_vol = float(curr_bar["volume"])
            avg_vol = float(vol_sma.iloc[i]) if not np.isnan(vol_sma.iloc[i]) else 1.0

            ts = curr_bar["timestamp"]
            if not isinstance(ts, datetime):
                ts = pd.Timestamp(ts).to_pydatetime()

            # Breakout condition: Previous close <= ORB High and Current close > ORB High
            # with volume confirmation
            is_breakout = (p_price <= orb_high) and (c_price > orb_high)
            has_volume = (c_vol >= (avg_vol * params.volume_multiplier)) if avg_vol > 0 else True

            if is_breakout and has_volume:
                risk = c_price - orb_mid
                if risk <= 0:
                    risk = c_price * 0.005  # 0.5% default minimum stop distance
                stop_loss = round(c_price - risk, 2)
                take_profit = round(c_price + (risk * params.risk_reward_ratio), 2)

                signals.append(
                    Signal(
                        symbol=symbol,
                        direction=SignalDirection.BUY,
                        strength=0.85,
                        timestamp=ts,
                        strategy_name=self.name(),
                        timeframe="5m",
                        entry_price=round(c_price, 2),
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        metadata={
                            "orb_high": round(orb_high, 2),
                            "orb_low": round(orb_low, 2),
                            "orb_mid": round(orb_mid, 2),
                            "volume_ratio": round(c_vol / avg_vol, 2) if avg_vol > 0 else 1.0,
                            "invalidation_level": stop_loss,
                        },
                    )
                )

        return signals
