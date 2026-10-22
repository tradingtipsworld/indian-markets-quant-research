"""Whole-Market Quantitative Scanner for Indian Intraday Equities.

Scans a defined and documented NSE universe for actionable intraday setups
with objective entry triggers, invalidation conditions, market regime context,
sector performance rankings, and realistic transaction cost estimates.

Supports the critical capability to conclude: 'No sufficiently strong setup today'.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

import pandas as pd
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.portfolio.manager import TransactionCostModel
from app.portfolio.models import OrderSide
from app.quant.regime import MarketRegime, MarketRegimeDetector
from app.quant.strategies.base import BaseStrategy, SignalDirection
from app.quant.strategies.momentum import MomentumBreakoutStrategy
from app.quant.strategies.orb import OpeningRangeBreakoutStrategy
from app.quant.strategies.relative_strength import RelativeStrengthStrategy
from app.quant.strategies.vwap_pullback import VWAPPullbackStrategy

logger = get_logger(__name__)

# Standard Liquid NSE Cash Equity Universe
DEFAULT_NSE_UNIVERSE: list[str] = [
    "RELIANCE",
    "TCS",
    "HDFCBANK",
    "INFY",
    "ICICIBANK",
    "SBIN",
    "BHARTIARTL",
    "ITC",
    "LT",
    "TATAMOTORS",
    "BAJFINANCE",
    "MARUTI",
    "KOTAKBANK",
    "AXISBANK",
    "SUNPHARMA",
]

# Standard Sector Mapping for Indian Universe
NSE_SECTORS: dict[str, str] = {
    "RELIANCE": "ENERGY",
    "TCS": "IT",
    "INFY": "IT",
    "HDFCBANK": "BANKING",
    "ICICIBANK": "BANKING",
    "SBIN": "BANKING",
    "KOTAKBANK": "BANKING",
    "AXISBANK": "BANKING",
    "BHARTIARTL": "TELECOM",
    "ITC": "FMCG",
    "LT": "INFRASTRUCTURE",
    "TATAMOTORS": "AUTO",
    "MARUTI": "AUTO",
    "BAJFINANCE": "FINANCIAL_SERVICES",
    "SUNPHARMA": "PHARMA",
}


class SetupStatus(str, Enum):
    """Lifecycle status of an intraday setup."""

    CANDIDATE = "candidate"
    APPROVED = "approved"
    REJECTED = "rejected"
    TRIGGERED = "triggered"
    INVALIDATED = "invalidated"
    EXPIRED = "expired"


class IntradaySetupRecord(BaseModel):
    """Complete, auditable DNA record for an intraday trading setup."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    symbol: str
    sector: str = "GENERAL"
    timestamp: datetime = Field(default_factory=datetime.now)
    strategy_name: str
    strategy_version: str = "1.0"
    regime: MarketRegime
    entry_trigger_price: float
    invalidation_level: float  # Stop-loss
    target_price: float
    risk_reward_ratio: float
    estimated_transaction_cost: float = 0.0
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    rejection_reason: str | None = None
    status: SetupStatus = SetupStatus.CANDIDATE
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScannerResult(BaseModel):
    """Aggregate output from a whole-market intraday scan."""

    scan_timestamp: datetime = Field(default_factory=datetime.now)
    universe_scanned: list[str] = Field(default_factory=list)
    total_symbols_evaluated: int = 0
    eligible_setups: list[IntradaySetupRecord] = Field(default_factory=list)
    rejected_candidates: list[IntradaySetupRecord] = Field(default_factory=list)
    market_regime_summary: dict[str, str] = Field(default_factory=dict)
    sector_performance: dict[str, float] = Field(default_factory=dict)
    has_setups: bool = False
    no_trade_reason: str | None = None


class WholeMarketScanner:
    """Configurable quantitative scanner for liquid Indian equities."""

    def __init__(
        self,
        universe: list[str] | None = None,
        strategies: list[BaseStrategy] | None = None,
        min_daily_volume: int = 100_000,
        min_price: float = 50.0,
        max_price: float = 15_000.0,
        min_risk_reward: float = 1.5,
    ):
        self.universe = universe or DEFAULT_NSE_UNIVERSE
        self.strategies = strategies or [
            OpeningRangeBreakoutStrategy(),
            VWAPPullbackStrategy(),
            MomentumBreakoutStrategy(),
            RelativeStrengthStrategy(),
        ]
        self.min_daily_volume = min_daily_volume
        self.min_price = min_price
        self.max_price = max_price
        self.min_risk_reward = min_risk_reward
        self.regime_detector = MarketRegimeDetector()
        self.cost_model = TransactionCostModel(stt_pct=0.025)  # Intraday equity STT is 0.025%

    def scan(self, market_data_map: dict[str, pd.DataFrame]) -> ScannerResult:
        """Scan all universe symbols across loaded strategies, regimes, and sectors."""
        result = ScannerResult(
            universe_scanned=self.universe,
            total_symbols_evaluated=len(market_data_map),
        )

        # 1. Compute Sector Performance
        sector_returns: dict[str, list[float]] = {}

        for symbol, df in market_data_map.items():
            if df is None or df.empty or len(df) < 5:
                continue

            last_close = float(df["close"].iloc[-1])
            prev_close = float(df["close"].iloc[-2]) if len(df) >= 2 else last_close
            pct_return = ((last_close - prev_close) / prev_close) * 100.0 if prev_close > 0 else 0.0

            sec = NSE_SECTORS.get(symbol, "GENERAL")
            if sec not in sector_returns:
                sector_returns[sec] = []
            sector_returns[sec].append(pct_return)

            # Universe liquidity and price filters
            avg_volume = float(df["volume"].mean()) if "volume" in df.columns else 0.0
            if not (self.min_price <= last_close <= self.max_price):
                logger.debug("Symbol price out of bounds", symbol=symbol, price=last_close)
                continue

            if avg_volume < self.min_daily_volume:
                logger.debug("Symbol volume below liquidity threshold", symbol=symbol, volume=avg_volume)
                continue

            # 2. Detect regime
            regime_report = self.regime_detector.detect(df, symbol=symbol)
            result.market_regime_summary[symbol] = regime_report.regime.value

            # 3. Skip symbols in erratic / high-volatility regimes
            if regime_report.regime == MarketRegime.HIGH_VOLATILITY:
                result.rejected_candidates.append(
                    IntradaySetupRecord(
                        symbol=symbol,
                        sector=sec,
                        strategy_name="regime_filter",
                        regime=regime_report.regime,
                        entry_trigger_price=last_close,
                        invalidation_level=last_close * 0.98,
                        target_price=last_close * 1.04,
                        risk_reward_ratio=2.0,
                        estimated_transaction_cost=0.0,
                        rejection_reason="Excessive volatility regime: ATR exceeds safe threshold",
                        status=SetupStatus.REJECTED,
                    )
                )
                continue

            # 4. Run strategies
            for strategy in self.strategies:
                signals = strategy.generate_signals(df)
                for sig in signals:
                    if sig.direction != SignalDirection.BUY or sig.entry_price is None or sig.stop_loss is None:
                        continue

                    # Calculate risk/reward
                    risk = abs(sig.entry_price - sig.stop_loss)
                    reward = abs((sig.take_profit or sig.entry_price * 1.02) - sig.entry_price)
                    rr_ratio = round(reward / risk, 2) if risk > 0 else 0.0

                    # Calculate estimated round-trip transaction costs
                    est_cost = self.cost_model.calculate_fees(OrderSide.BUY, sig.entry_price, 100) + \
                               self.cost_model.calculate_fees(OrderSide.SELL, sig.take_profit or sig.entry_price, 100)

                    supporting = [
                        f"Active {strategy.name()} trigger at ₹{sig.entry_price:.2f}",
                        f"Regime: {regime_report.regime.value} (Confidence: {regime_report.confidence:.2f})",
                        f"Sector: {sec}",
                    ]
                    contradicting = []

                    # Invalidation check
                    if rr_ratio < self.min_risk_reward:
                        contradicting.append(f"Risk/reward ratio {rr_ratio:.2f} is below minimum requirement of {self.min_risk_reward}")
                        result.rejected_candidates.append(
                            IntradaySetupRecord(
                                symbol=symbol,
                                sector=sec,
                                strategy_name=strategy.name(),
                                regime=regime_report.regime,
                                entry_trigger_price=sig.entry_price,
                                invalidation_level=sig.stop_loss,
                                target_price=sig.take_profit or (sig.entry_price + risk * 2),
                                risk_reward_ratio=rr_ratio,
                                estimated_transaction_cost=est_cost,
                                supporting_evidence=supporting,
                                contradicting_evidence=contradicting,
                                rejection_reason=f"Insufficient risk-to-reward ({rr_ratio} < {self.min_risk_reward})",
                                status=SetupStatus.REJECTED,
                            )
                        )
                        continue

                    # Eligible setup found!
                    setup = IntradaySetupRecord(
                        symbol=symbol,
                        sector=sec,
                        strategy_name=strategy.name(),
                        regime=regime_report.regime,
                        entry_trigger_price=sig.entry_price,
                        invalidation_level=sig.stop_loss,
                        target_price=sig.take_profit or (sig.entry_price + risk * 2),
                        risk_reward_ratio=rr_ratio,
                        estimated_transaction_cost=est_cost,
                        supporting_evidence=supporting,
                        contradicting_evidence=contradicting,
                        status=SetupStatus.CANDIDATE,
                        metadata=sig.metadata,
                    )
                    result.eligible_setups.append(setup)

        # Average sector returns
        for sec, rets in sector_returns.items():
            result.sector_performance[sec] = round(float(sum(rets) / len(rets)), 2) if rets else 0.0

        result.has_setups = len(result.eligible_setups) > 0
        if not result.has_setups:
            result.no_trade_reason = (
                "Market conditions did not produce any candidate meeting minimum liquidity, "
                "regime stability, and risk-reward criteria (>= 1:1.5). No trade recommended today."
            )

        # Register scan results into singleton store for API visibility
        store = get_setup_store()
        store.add_setups(result.eligible_setups)
        store.add_setups(result.rejected_candidates)

        return result


class IntradaySetupStore:
    """In-memory and queryable registry of intraday candidate, active, and failed setups."""

    def __init__(self):
        self._setups: dict[str, IntradaySetupRecord] = {}

    def add_setup(self, setup: IntradaySetupRecord) -> None:
        self._setups[setup.id] = setup

    def add_setups(self, setups: list[IntradaySetupRecord]) -> None:
        for s in setups:
            self._setups[s.id] = s

    def get_setup(self, setup_id: str) -> IntradaySetupRecord | None:
        return self._setups.get(setup_id)

    def get_active_setups(self) -> list[IntradaySetupRecord]:
        return [
            s for s in self._setups.values()
            if s.status in (SetupStatus.CANDIDATE, SetupStatus.APPROVED, SetupStatus.TRIGGERED)
        ]

    def get_failed_setups(self) -> list[IntradaySetupRecord]:
        return [
            s for s in self._setups.values()
            if s.status in (SetupStatus.REJECTED, SetupStatus.INVALIDATED, SetupStatus.EXPIRED)
        ]

    def update_status(self, setup_id: str, status: SetupStatus, reason: str | None = None) -> bool:
        setup = self._setups.get(setup_id)
        if not setup:
            return False
        setup.status = status
        if reason:
            setup.rejection_reason = reason
        return True

    def clear(self) -> None:
        self._setups.clear()


_setup_store = IntradaySetupStore()


def get_setup_store() -> IntradaySetupStore:
    return _setup_store

