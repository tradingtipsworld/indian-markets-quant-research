"""Market Regime Detection Engine.

Classifies market state into objective, deterministic regimes:
- TRENDING_BULLISH
- TRENDING_BEARISH
- RANGE_BOUND
- HIGH_VOLATILITY
- LOW_VOLATILITY
- UNKNOWN (insufficient or conflicting data — never invent false certainty)

Uses strictly point-in-time historical data without future leakage.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from app.quant.indicators.core import atr, bollinger_bands, ema, sma


class MarketRegime(str, Enum):
    """Deterministic market regime classification."""

    TRENDING_BULLISH = "trending_bullish"
    TRENDING_BEARISH = "trending_bearish"
    RANGE_BOUND = "range_bound"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    UNKNOWN = "unknown"


class RegimeAssessment(BaseModel):
    """Detailed market regime evaluation report."""

    regime: MarketRegime
    symbol: str
    confidence: float
    features: dict[str, Any] = Field(default_factory=dict)
    rationale: list[str] = Field(default_factory=list)


class MarketRegimeDetector:
    """Evaluates chronological price history to identify current market regime."""

    def __init__(
        self,
        trend_period_fast: int = 20,
        trend_period_slow: int = 50,
        atr_period: int = 14,
        volatility_high_threshold_pct: float = 2.5,
        volatility_low_threshold_pct: float = 0.8,
    ):
        self.fast = trend_period_fast
        self.slow = trend_period_slow
        self.atr_period = atr_period
        self.vol_high_thresh = volatility_high_threshold_pct
        self.vol_low_thresh = volatility_low_threshold_pct

    def detect(self, df: pd.DataFrame, symbol: str = "BENCHMARK") -> RegimeAssessment:
        """Classify market regime based strictly on past OHLCV bars."""
        min_required = max(self.slow + 5, 30)
        if df is None or len(df) < min_required:
            return RegimeAssessment(
                regime=MarketRegime.UNKNOWN,
                symbol=symbol,
                confidence=0.0,
                rationale=[f"Insufficient historical bars ({len(df) if df is not None else 0} < {min_required})"],
            )

        close = df["close"]
        high = df["high"]
        low = df["low"]
        curr_price = float(close.iloc[-1])

        sma_fast_series = sma(close, self.fast)
        sma_slow_series = sma(close, self.slow)
        atr_series = atr(high, low, close, self.atr_period)
        bb = bollinger_bands(close, period=20, std_dev=2.0)

        sma_fast_val = float(sma_fast_series.iloc[-1])
        sma_slow_val = float(sma_slow_series.iloc[-1])
        atr_val = float(atr_series.iloc[-1])
        bb_width_pct = float(((bb["upper"].iloc[-1] - bb["lower"].iloc[-1]) / curr_price) * 100.0)
        atr_pct = float((atr_val / curr_price) * 100.0)

        # Fast slope over last 5 bars
        fast_slope = float(sma_fast_series.iloc[-1] - sma_fast_series.iloc[-5]) / 5.0

        features = {
            "current_price": round(curr_price, 2),
            "sma_fast": round(sma_fast_val, 2),
            "sma_slow": round(sma_slow_val, 2),
            "atr_pct": round(atr_pct, 2),
            "bb_bandwidth_pct": round(bb_width_pct, 2),
            "fast_slope": round(fast_slope, 4),
        }

        rationale: list[str] = []

        # 1. Trending Bullish Check
        if curr_price > sma_fast_val > sma_slow_val and fast_slope > 0:
            rationale.append(f"Price ({curr_price:.2f}) > SMA{self.fast} ({sma_fast_val:.2f}) > SMA{self.slow} ({sma_slow_val:.2f}) with positive slope")
            return RegimeAssessment(
                regime=MarketRegime.TRENDING_BULLISH,
                symbol=symbol,
                confidence=0.80,
                features=features,
                rationale=rationale,
            )

        # 2. Trending Bearish Check
        if curr_price < sma_fast_val < sma_slow_val and fast_slope < 0:
            rationale.append(f"Price ({curr_price:.2f}) < SMA{self.fast} ({sma_fast_val:.2f}) < SMA{self.slow} ({sma_slow_val:.2f}) with negative slope")
            return RegimeAssessment(
                regime=MarketRegime.TRENDING_BEARISH,
                symbol=symbol,
                confidence=0.80,
                features=features,
                rationale=rationale,
            )

        # 3. High Volatility Check (Extreme ATR / wide erratic swings)
        if atr_pct >= self.vol_high_thresh or bb_width_pct >= (self.vol_high_thresh * 3.0):
            rationale.append(f"ATR is {atr_pct:.2f}% of price and BB width is {bb_width_pct:.2f}% (above high vol limit)")
            return RegimeAssessment(
                regime=MarketRegime.HIGH_VOLATILITY,
                symbol=symbol,
                confidence=0.85,
                features=features,
                rationale=rationale,
            )

        # 4. Low Volatility / Squeeze Check
        if atr_pct <= self.vol_low_thresh and bb_width_pct <= (self.vol_low_thresh * 2.0):
            rationale.append(f"Volatility compressed: ATR {atr_pct:.2f}%, BB width {bb_width_pct:.2f}%")
            return RegimeAssessment(
                regime=MarketRegime.LOW_VOLATILITY,
                symbol=symbol,
                confidence=0.75,
                features=features,
                rationale=rationale,
            )

        # 5. Range Bound / Consolidating
        if abs(curr_price - sma_fast_val) / curr_price < 0.015:
            rationale.append("Price oscillating within tight band around mean with flat slope")
            return RegimeAssessment(
                regime=MarketRegime.RANGE_BOUND,
                symbol=symbol,
                confidence=0.70,
                features=features,
                rationale=rationale,
            )

        # 6. Unclear / Conflicting Signals -> UNKNOWN
        rationale.append("Mixed moving average alignment and contradictory momentum metrics")
        return RegimeAssessment(
            regime=MarketRegime.UNKNOWN,
            symbol=symbol,
            confidence=0.40,
            features=features,
            rationale=rationale,
        )
