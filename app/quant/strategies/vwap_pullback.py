"""VWAP Pullback Intraday Strategy.

Identifies trend continuation setups where an intraday trending asset pulls back
to test the Volume Weighted Average Price (VWAP) and resumes the primary trend direction.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from pydantic import Field

from app.quant.indicators.core import ema, vwap
from app.quant.strategies.base import (
    BaseStrategy,
    Signal,
    SignalDirection,
    StrategyParameters,
)


class VWAPPullbackParameters(StrategyParameters):
    """Parameters for VWAP Pullback strategy."""

    trend_ema_period: int = Field(default=20, description="EMA period to confirm bullish trend above VWAP")
    pullback_tolerance_pct: float = Field(default=0.4, description="Max percentage distance from VWAP for pullback entry")
    risk_reward_ratio: float = Field(default=2.0, description="Target distance multiplier relative to risk")


class VWAPPullbackStrategy(BaseStrategy):
    """VWAP Pullback Strategy for Intraday Equities."""

    def name(self) -> str:
        return "vwap_pullback_v1"

    def description(self) -> str:
        return "Trend-following pullback entry on test and bounce from intraday VWAP."

    def min_bars_required(self) -> int:
        return 30

    def generate_signals(
        self, df: pd.DataFrame, parameters: StrategyParameters | None = None
    ) -> list[Signal]:
        params = parameters if isinstance(parameters, VWAPPullbackParameters) else VWAPPullbackParameters()

        if not self.validate_data(df):
            return []

        symbol = df["symbol"].iloc[0] if "symbol" in df.columns else "UNKNOWN"
        signals: list[Signal] = []

        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        vwap_series = vwap(high, low, close, volume)
        ema_series = ema(close, params.trend_ema_period)

        for i in range(params.trend_ema_period, len(df)):
            curr_bar = df.iloc[i]
            prev_bar = df.iloc[i - 1]
            c_price = float(curr_bar["close"])
            c_low = float(curr_bar["low"])
            vwap_val = float(vwap_series.iloc[i])
            ema_val = float(ema_series.iloc[i])

            if np.isnan(vwap_val) or np.isnan(ema_val) or vwap_val <= 0:
                continue

            ts = curr_bar["timestamp"]
            if not isinstance(ts, datetime):
                ts = pd.Timestamp(ts).to_pydatetime()

            # Conditions:
            # 1. Primary trend bullish: price and EMA above VWAP
            is_bullish_trend = c_price > vwap_val and ema_val >= vwap_val
            # 2. Pullback test: bar low touched near VWAP (within tolerance)
            pct_distance = abs(c_low - vwap_val) / vwap_val * 100.0
            tested_vwap = pct_distance <= params.pullback_tolerance_pct
            # 3. Bullish candle close above open (bounce confirmation)
            bounced = c_price > float(curr_bar["open"])

            if is_bullish_trend and tested_vwap and bounced:
                stop_loss = round(vwap_val * 0.996, 2)  # 0.4% below VWAP as invalidation
                risk = c_price - stop_loss
                if risk <= 0:
                    risk = c_price * 0.005
                take_profit = round(c_price + (risk * params.risk_reward_ratio), 2)

                signals.append(
                    Signal(
                        symbol=symbol,
                        direction=SignalDirection.BUY,
                        strength=0.80,
                        timestamp=ts,
                        strategy_name=self.name(),
                        timeframe="5m",
                        entry_price=round(c_price, 2),
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        metadata={
                            "vwap": round(vwap_val, 2),
                            "ema": round(ema_val, 2),
                            "pullback_distance_pct": round(pct_distance, 2),
                            "invalidation_level": stop_loss,
                        },
                    )
                )

        return signals
