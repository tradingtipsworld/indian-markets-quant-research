"""Unit tests for paper trading portfolio operations."""

import pytest
from app.core.exceptions import InsufficientFundsError, PortfolioError
from app.portfolio.models import OrderSide, OrderStatus


def test_paper_buy_order_execution(portfolio_manager):
    order = portfolio_manager.submit_order(
        symbol="SYNTH_RELIANCE",
        side=OrderSide.BUY,
        quantity=20,
        market_price=2500.0,
    )
    assert order.status == OrderStatus.FILLED
    assert "SYNTH_RELIANCE" in portfolio_manager.positions
    pos = portfolio_manager.positions["SYNTH_RELIANCE"]
    assert pos.quantity == 20
    assert portfolio_manager.cash < 1_000_000.0  # Cash debited with fees/slippage


def test_paper_sell_order_execution(portfolio_manager):
    # Buy first
    portfolio_manager.submit_order("SYNTH_RELIANCE", OrderSide.BUY, 20, 2500.0)
    # Sell partial
    sell_order = portfolio_manager.submit_order("SYNTH_RELIANCE", OrderSide.SELL, 10, 2600.0)
    assert sell_order.status == OrderStatus.FILLED
    assert portfolio_manager.positions["SYNTH_RELIANCE"].quantity == 10


def test_cannot_sell_unowned_shares(portfolio_manager):
    with pytest.raises(PortfolioError, match="Insufficient position"):
        portfolio_manager.submit_order("SYNTH_TCS", OrderSide.SELL, 5, 3800.0)
