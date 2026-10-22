"""Paper trading execution broker and portfolio manager.

Handles virtual order execution, slippage simulation, transaction fees,
cash balances, position tracking, and trade audit logging.
Never connects to live exchanges or places real orders.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.exceptions import InsufficientFundsError, PortfolioError
from app.core.logging import get_logger
from app.portfolio.models import (
    OrderSide,
    OrderStatus,
    OrderType,
    PaperOrder,
    Position,
    TradeAuditRecord,
)
from app.risk.engine import PortfolioSnapshot, ProposedOrder, RiskEngine

logger = get_logger(__name__)


class TransactionCostModel:
    """Calculates brokerage, STT, exchange turnover fees, and stamp duty for Indian markets."""

    def __init__(
        self,
        brokerage_pct: float = 0.03,  # 0.03% or flat
        stt_pct: float = 0.1,  # 0.1% on delivery buy/sell
        exchange_turnover_pct: float = 0.00345,
        gst_pct: float = 18.0,  # 18% on brokerage + turnover
        sebi_charges_pct: float = 0.0001,
        stamp_duty_pct: float = 0.015,  # 0.015% on buy
    ):
        self.brokerage_pct = brokerage_pct / 100.0
        self.stt_pct = stt_pct / 100.0
        self.turnover_pct = exchange_turnover_pct / 100.0
        self.gst_pct = gst_pct / 100.0
        self.sebi_pct = sebi_charges_pct / 100.0
        self.stamp_duty_pct = stamp_duty_pct / 100.0

    def calculate_fees(self, side: OrderSide, price: float, quantity: int) -> float:
        turnover = price * quantity
        brokerage = turnover * self.brokerage_pct
        stt = turnover * self.stt_pct if side == OrderSide.SELL else 0.0
        turnover_charges = turnover * self.turnover_pct
        gst = (brokerage + turnover_charges) * self.gst_pct
        sebi = turnover * self.sebi_pct
        stamp = (turnover * self.stamp_duty_pct) if side == OrderSide.BUY else 0.0
        return round(brokerage + stt + turnover_charges + gst + sebi + stamp, 2)


class PaperBroker:
    """Simulates realistic broker order execution with slippage and fees."""

    def __init__(
        self,
        cost_model: TransactionCostModel | None = None,
        default_slippage_pct: float = 0.05,  # 0.05% slippage default
    ):
        self.cost_model = cost_model or TransactionCostModel()
        self.slippage_pct = default_slippage_pct / 100.0

    def execute(self, order: PaperOrder, market_price: float) -> tuple[PaperOrder, TradeAuditRecord]:
        """Simulate execution of an order at market price with slippage and fees."""
        # Calculate slippage
        if order.side == OrderSide.BUY:
            fill_price = market_price * (1.0 + self.slippage_pct)
        else:
            fill_price = market_price * (1.0 - self.slippage_pct)

        fill_price = round(fill_price, 2)
        slippage_cost = abs(fill_price - market_price) * order.quantity
        fees = self.cost_model.calculate_fees(order.side, fill_price, order.quantity)

        order.status = OrderStatus.FILLED
        order.filled_price = fill_price
        order.filled_quantity = order.quantity
        order.slippage = slippage_cost
        order.transaction_cost = fees
        order.filled_at = datetime.now()

        net_val = (fill_price * order.quantity) + (fees if order.side == OrderSide.BUY else -fees)
        audit = TradeAuditRecord(
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            slippage=slippage_cost,
            fees=fees,
            net_value=round(net_val, 2),
            strategy_name=order.strategy_name,
        )
        return order, audit


class PortfolioManager:
    """Manages cash balances, open positions, equity curve, and simulated orders."""

    def __init__(
        self,
        initial_cash: float = 1_000_000.0,
        risk_engine: RiskEngine | None = None,
        broker: PaperBroker | None = None,
    ):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: dict[str, Position] = {}
        self.orders: list[PaperOrder] = []
        self.trade_history: list[TradeAuditRecord] = []
        self.peak_value = initial_cash
        self.risk_engine = risk_engine
        self.broker = broker or PaperBroker()

    @property
    def total_value(self) -> float:
        positions_val = sum(pos.market_value for pos in self.positions.values())
        return round(self.cash + positions_val, 2)

    @property
    def unrealized_pnl(self) -> float:
        return round(sum(pos.unrealized_pnl for pos in self.positions.values()), 2)

    @property
    def realized_pnl(self) -> float:
        return round(sum(pos.realized_pnl for pos in self.positions.values()), 2)

    def update_market_price(self, symbol: str, price: float) -> None:
        """Update current mark price for an open position."""
        if symbol in self.positions:
            self.positions[symbol].current_price = price
            self.positions[symbol].updated_at = datetime.now()
            if self.total_value > self.peak_value:
                self.peak_value = self.total_value

    def get_snapshot(self) -> PortfolioSnapshot:
        """Export snapshot for risk engine evaluation."""
        pos_dict = {
            s: {
                "quantity": p.quantity,
                "avg_price": p.average_entry_price,
                "current_price": p.current_price,
                "market_value": p.market_value,
            }
            for s, p in self.positions.items()
        }
        return PortfolioSnapshot(
            total_value=self.total_value,
            cash=self.cash,
            positions=pos_dict,
            unrealized_pnl=self.unrealized_pnl,
            peak_value=self.peak_value,
            initial_value=self.initial_cash,
        )

    def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        market_price: float,
        strategy_name: str = "",
    ) -> PaperOrder:
        """Submit a paper order with independent risk checks and simulated fill."""
        if quantity <= 0:
            raise PortfolioError(f"Quantity must be positive, got {quantity}")
        if market_price <= 0:
            raise PortfolioError(f"Market price must be positive, got {market_price}")

        order = PaperOrder(
            symbol=symbol,
            side=side,
            quantity=quantity,
            requested_price=market_price,
            strategy_name=strategy_name,
        )

        # Independent Risk Evaluation
        if self.risk_engine:
            prop = ProposedOrder(
                symbol=symbol,
                direction=side.value,
                quantity=quantity,
                price=market_price,
                strategy_name=strategy_name,
                signal_timestamp=datetime.now(),
            )
            assessment = self.risk_engine.assess(prop, self.get_snapshot())
            if not assessment.approved:
                order.status = OrderStatus.REJECTED
                order.reason = "; ".join(assessment.rejections)
                self.orders.append(order)
                return order

        # Cash pre-check for BUY
        estimated_cost = (quantity * market_price) * 1.05  # buffer for fees/slippage
        if side == OrderSide.BUY and self.cash < estimated_cost:
            order.status = OrderStatus.REJECTED
            order.reason = f"Insufficient cash: required {estimated_cost:.2f}, available {self.cash:.2f}"
            self.orders.append(order)
            raise InsufficientFundsError(order.reason)

        # Sell quantity check
        if side == OrderSide.SELL:
            current_pos = self.positions.get(symbol)
            if not current_pos or current_pos.quantity < quantity:
                avail = current_pos.quantity if current_pos else 0
                order.status = OrderStatus.REJECTED
                order.reason = f"Insufficient position: holding {avail}, requested {quantity}"
                self.orders.append(order)
                raise PortfolioError(order.reason)

        # Execute through paper broker
        filled_order, audit = self.broker.execute(order, market_price)
        self._apply_fill(filled_order, audit)
        self.orders.append(filled_order)
        self.trade_history.append(audit)

        if self.total_value > self.peak_value:
            self.peak_value = self.total_value

        return filled_order

    def _apply_fill(self, order: PaperOrder, audit: TradeAuditRecord) -> None:
        """Update cash and position after order fill."""
        fill_price = order.filled_price
        qty = order.filled_quantity
        fees = order.transaction_cost

        if order.side == OrderSide.BUY:
            total_debit = (fill_price * qty) + fees
            self.cash -= total_debit

            if order.symbol not in self.positions:
                self.positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=qty,
                    average_entry_price=fill_price,
                    current_price=fill_price,
                )
            else:
                pos = self.positions[order.symbol]
                new_qty = pos.quantity + qty
                new_cost = (pos.quantity * pos.average_entry_price) + (qty * fill_price)
                pos.average_entry_price = new_cost / new_qty
                pos.quantity = new_qty
                pos.current_price = fill_price
                pos.updated_at = datetime.now()

        elif order.side == OrderSide.SELL:
            total_credit = (fill_price * qty) - fees
            self.cash += total_credit

            pos = self.positions[order.symbol]
            realized = (fill_price - pos.average_entry_price) * qty - fees
            pos.realized_pnl += realized
            pos.quantity -= qty
            pos.current_price = fill_price
            pos.updated_at = datetime.now()

            if pos.quantity == 0:
                del self.positions[order.symbol]
