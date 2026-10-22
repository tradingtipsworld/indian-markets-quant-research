"""Risk engine — independent, testable risk validation.

The risk engine evaluates proposed trading actions against
configurable risk limits. It is intentionally separate from
strategy generation and portfolio management.

A failed risk check REJECTS the proposed action by default.
The risk engine does not generate trading signals or advice.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import AppSettings
from app.core.exceptions import KillSwitchActiveError, RiskLimitExceededError
from app.core.logging import get_logger

logger = get_logger(__name__)


class RiskCheckResult(BaseModel):
    """Result of a single risk check."""

    check_name: str
    passed: bool
    message: str
    value: float | None = None
    limit: float | None = None
    timestamp: datetime = Field(default_factory=datetime.now)


class RiskAssessment(BaseModel):
    """Complete risk assessment for a proposed action."""

    approved: bool
    checks: list[RiskCheckResult] = Field(default_factory=list)
    rejections: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    assessed_at: datetime = Field(default_factory=datetime.now)


class ProposedOrder(BaseModel):
    """A proposed order to be validated by the risk engine."""

    symbol: str
    direction: str  # "buy" or "sell"
    quantity: int
    price: float
    order_type: str = "market"
    strategy_name: str = ""
    signal_timestamp: datetime | None = None


class PortfolioSnapshot(BaseModel):
    """Current portfolio state for risk evaluation."""

    total_value: float
    cash: float
    positions: dict[str, dict[str, Any]] = Field(default_factory=dict)
    # positions: {symbol: {quantity, avg_price, current_price, market_value}}
    unrealized_pnl: float = 0.0
    peak_value: float = 0.0
    initial_value: float = 0.0


class RiskEngine:
    """Independent risk validation engine.

    Evaluates proposed orders against configurable risk limits.
    All checks must pass for an order to be approved.
    """

    def __init__(self, settings: AppSettings):
        self._max_position_size_pct = settings.risk_max_position_size_pct
        self._max_portfolio_exposure_pct = settings.risk_max_portfolio_exposure_pct
        self._max_drawdown_pct = settings.risk_max_drawdown_pct
        self._max_concentration_pct = settings.risk_max_concentration_pct
        self._paper_only = settings.risk_paper_only
        self._kill_switch = settings.risk_kill_switch

    def assess(
        self,
        order: ProposedOrder,
        portfolio: PortfolioSnapshot,
    ) -> RiskAssessment:
        """Run all risk checks on a proposed order.

        Args:
            order: The proposed order to validate.
            portfolio: Current portfolio state.

        Returns:
            RiskAssessment with all check results.

        Raises:
            KillSwitchActiveError: If the kill switch is active.
        """
        assessment = RiskAssessment(approved=True)

        # Kill switch — hard stop, raise immediately
        if self._kill_switch:
            raise KillSwitchActiveError()

        # Run all checks
        checks = [
            self._check_paper_only(order),
            self._check_available_cash(order, portfolio),
            self._check_position_size(order, portfolio),
            self._check_concentration(order, portfolio),
            self._check_portfolio_exposure(order, portfolio),
            self._check_drawdown(portfolio),
            self._check_signal_freshness(order),
        ]

        for check in checks:
            assessment.checks.append(check)
            if not check.passed:
                assessment.approved = False
                assessment.rejections.append(f"{check.check_name}: {check.message}")

        if not assessment.approved:
            logger.warning(
                "Risk assessment REJECTED order",
                symbol=order.symbol,
                direction=order.direction,
                rejections=assessment.rejections,
            )
        else:
            logger.info(
                "Risk assessment APPROVED order",
                symbol=order.symbol,
                direction=order.direction,
            )

        return assessment

    def _check_paper_only(self, order: ProposedOrder) -> RiskCheckResult:
        """Ensure we're in paper-only mode."""
        return RiskCheckResult(
            check_name="paper_only",
            passed=self._paper_only,
            message="Paper-only mode is active" if self._paper_only else "LIVE TRADING NOT PERMITTED in Phase 1",
        )

    def _check_available_cash(
        self, order: ProposedOrder, portfolio: PortfolioSnapshot
    ) -> RiskCheckResult:
        """Check if sufficient cash is available for buy orders."""
        if order.direction != "buy":
            return RiskCheckResult(
                check_name="available_cash",
                passed=True,
                message="Not a buy order — cash check not applicable",
            )

        required_cash = order.quantity * order.price
        available = portfolio.cash

        return RiskCheckResult(
            check_name="available_cash",
            passed=available >= required_cash,
            message=(
                f"Required: {required_cash:.2f}, Available: {available:.2f}"
                if available < required_cash
                else "Sufficient cash available"
            ),
            value=required_cash,
            limit=available,
        )

    def _check_position_size(
        self, order: ProposedOrder, portfolio: PortfolioSnapshot
    ) -> RiskCheckResult:
        """Check that no single position exceeds the max position size."""
        if portfolio.total_value <= 0:
            return RiskCheckResult(
                check_name="position_size",
                passed=False,
                message="Portfolio has zero or negative total value",
            )

        order_value = order.quantity * order.price
        position_pct = (order_value / portfolio.total_value) * 100

        return RiskCheckResult(
            check_name="position_size",
            passed=position_pct <= self._max_position_size_pct,
            message=(
                f"Position {position_pct:.1f}% exceeds limit {self._max_position_size_pct}%"
                if position_pct > self._max_position_size_pct
                else f"Position {position_pct:.1f}% within limit"
            ),
            value=position_pct,
            limit=self._max_position_size_pct,
        )

    def _check_concentration(
        self, order: ProposedOrder, portfolio: PortfolioSnapshot
    ) -> RiskCheckResult:
        """Check that concentration in a single symbol stays within limits."""
        if portfolio.total_value <= 0:
            return RiskCheckResult(
                check_name="concentration",
                passed=False,
                message="Portfolio has zero or negative total value",
            )

        existing_value = 0.0
        if order.symbol in portfolio.positions:
            existing_value = portfolio.positions[order.symbol].get("market_value", 0.0)

        if order.direction == "buy":
            new_value = existing_value + (order.quantity * order.price)
        else:
            new_value = max(0, existing_value - (order.quantity * order.price))

        concentration_pct = (new_value / portfolio.total_value) * 100

        return RiskCheckResult(
            check_name="concentration",
            passed=concentration_pct <= self._max_concentration_pct,
            message=(
                f"Concentration {concentration_pct:.1f}% exceeds limit {self._max_concentration_pct}%"
                if concentration_pct > self._max_concentration_pct
                else f"Concentration {concentration_pct:.1f}% within limit"
            ),
            value=concentration_pct,
            limit=self._max_concentration_pct,
        )

    def _check_portfolio_exposure(
        self, order: ProposedOrder, portfolio: PortfolioSnapshot
    ) -> RiskCheckResult:
        """Check total portfolio exposure (invested vs total value)."""
        if portfolio.total_value <= 0:
            return RiskCheckResult(
                check_name="portfolio_exposure",
                passed=False,
                message="Portfolio has zero or negative total value",
            )

        invested = portfolio.total_value - portfolio.cash
        if order.direction == "buy":
            invested += order.quantity * order.price

        exposure_pct = (invested / portfolio.total_value) * 100

        return RiskCheckResult(
            check_name="portfolio_exposure",
            passed=exposure_pct <= self._max_portfolio_exposure_pct,
            message=(
                f"Exposure {exposure_pct:.1f}% exceeds limit {self._max_portfolio_exposure_pct}%"
                if exposure_pct > self._max_portfolio_exposure_pct
                else f"Exposure {exposure_pct:.1f}% within limit"
            ),
            value=exposure_pct,
            limit=self._max_portfolio_exposure_pct,
        )

    def _check_drawdown(self, portfolio: PortfolioSnapshot) -> RiskCheckResult:
        """Check that portfolio drawdown is within limits."""
        if portfolio.peak_value <= 0:
            return RiskCheckResult(
                check_name="drawdown",
                passed=True,
                message="No peak value recorded yet",
            )

        drawdown_pct = (
            (portfolio.peak_value - portfolio.total_value) / portfolio.peak_value
        ) * 100

        return RiskCheckResult(
            check_name="drawdown",
            passed=drawdown_pct <= self._max_drawdown_pct,
            message=(
                f"Drawdown {drawdown_pct:.1f}% exceeds limit {self._max_drawdown_pct}%"
                if drawdown_pct > self._max_drawdown_pct
                else f"Drawdown {drawdown_pct:.1f}% within limit"
            ),
            value=drawdown_pct,
            limit=self._max_drawdown_pct,
        )

    def _check_signal_freshness(
        self, order: ProposedOrder, max_age_minutes: int = 60
    ) -> RiskCheckResult:
        """Reject stale signals."""
        if order.signal_timestamp is None:
            return RiskCheckResult(
                check_name="signal_freshness",
                passed=True,
                message="No signal timestamp — manual or system order",
            )

        age = datetime.now() - order.signal_timestamp
        max_age = timedelta(minutes=max_age_minutes)

        return RiskCheckResult(
            check_name="signal_freshness",
            passed=age <= max_age,
            message=(
                f"Signal is {age.total_seconds() / 60:.0f} minutes old, max allowed is {max_age_minutes}"
                if age > max_age
                else "Signal is fresh"
            ),
        )

    def activate_kill_switch(self) -> None:
        """Activate the kill switch — halt all trading."""
        self._kill_switch = True
        logger.critical("KILL SWITCH ACTIVATED — all trading halted")

    def deactivate_kill_switch(self) -> None:
        """Deactivate the kill switch."""
        self._kill_switch = False
        logger.warning("Kill switch deactivated — trading may resume")

    @property
    def is_kill_switch_active(self) -> bool:
        return self._kill_switch
