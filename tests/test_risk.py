"""Unit tests for independent risk engine checks."""

from datetime import datetime, timedelta
import pytest
from app.core.exceptions import KillSwitchActiveError
from app.risk.engine import PortfolioSnapshot, ProposedOrder, RiskEngine


def test_risk_approves_safe_order(risk_engine):
    snap = PortfolioSnapshot(total_value=1_000_000.0, cash=1_000_000.0)
    order = ProposedOrder(
        symbol="SYNTH_RELIANCE",
        direction="buy",
        quantity=20,
        price=2500.0,  # 50,000 INR = 5% of portfolio, limit is 10%
    )
    assessment = risk_engine.assess(order, snap)
    assert assessment.approved is True
    assert len(assessment.rejections) == 0


def test_risk_rejects_oversized_position(risk_engine):
    snap = PortfolioSnapshot(total_value=1_000_000.0, cash=1_000_000.0)
    order = ProposedOrder(
        symbol="SYNTH_RELIANCE",
        direction="buy",
        quantity=100,
        price=2500.0,  # 250,000 INR = 25% of portfolio (limit is 10%)
    )
    assessment = risk_engine.assess(order, snap)
    assert assessment.approved is False
    assert any("position_size" in r for r in assessment.rejections)


def test_risk_rejects_insufficient_cash(risk_engine):
    snap = PortfolioSnapshot(total_value=1_000_000.0, cash=10_000.0)
    order = ProposedOrder(
        symbol="SYNTH_RELIANCE",
        direction="buy",
        quantity=10,
        price=2500.0,  # 25,000 required, only 10,000 cash
    )
    assessment = risk_engine.assess(order, snap)
    assert assessment.approved is False
    assert any("available_cash" in r for r in assessment.rejections)


def test_kill_switch_blocks_all_actions(risk_engine):
    risk_engine.activate_kill_switch()
    snap = PortfolioSnapshot(total_value=1_000_000.0, cash=1_000_000.0)
    order = ProposedOrder(
        symbol="SYNTH_RELIANCE",
        direction="buy",
        quantity=1,
        price=2500.0,
    )
    with pytest.raises(KillSwitchActiveError):
        risk_engine.assess(order, snap)
