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
    """Calculates brokerage, STT, exchange turnover fees, and stamp duty for Indian markets.

    Supports both Intraday and Delivery equity cash trading regimes with standard statutory caps.
    """

    def __init__(
        self,
        brokerage_pct: float = 0.03,  # 0.03% or ₹20 flat max
        max_brokerage_per_order: float = 20.0,
        is_intraday: bool = True,
        stt_pct: float | None = None,
        exchange_turnover_pct: float = 0.00345,  # 0.00345% NSE
        gst_pct: float = 18.0,  # 18% on (brokerage + turnover)
        sebi_charges_pct: float = 0.0001,  # ₹10 per crore (0.0001%)
        stamp_duty_pct: float | None = None,
    ):
        self.brokerage_pct = brokerage_pct / 100.0
        self.max_brokerage = max_brokerage_per_order
        self.is_intraday = is_intraday
        # In India: Intraday STT = 0.025% on Sell only; Delivery = 0.1% on Buy & Sell
        if stt_pct is not None:
            self.stt_pct = stt_pct / 100.0
        else:
            self.stt_pct = (0.025 if is_intraday else 0.1) / 100.0
        self.turnover_pct = exchange_turnover_pct / 100.0
        self.gst_pct = gst_pct / 100.0
        self.sebi_pct = sebi_charges_pct / 100.0
        # Stamp duty: Intraday = 0.003% on Buy; Delivery = 0.015% on Buy
        if stamp_duty_pct is not None:
            self.stamp_duty_pct = stamp_duty_pct / 100.0
        else:
            self.stamp_duty_pct = (0.003 if is_intraday else 0.015) / 100.0

    def calculate_fees(self, side: OrderSide, price: float, quantity: int) -> float:
        turnover = price * quantity
        # Brokerage with discount broker ₹20 cap
        brokerage = min(turnover * self.brokerage_pct, self.max_brokerage)
        stt = turnover * self.stt_pct if side == OrderSide.SELL else (0.0 if self.is_intraday else turnover * self.stt_pct)
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
    """Tracks cash balances, open positions, total equity, and risk allocations."""

    def __init__(
        self,
        initial_cash: float = 1_000_000.0,
        broker: PaperBroker | None = None,
        risk_engine: RiskEngine | None = None,
    ):
        self.cash: float = initial_cash
        self.initial_cash: float = initial_cash
        self.peak_equity: float = initial_cash
        self.positions: dict[str, Position] = {}
        self.orders: list[PaperOrder] = []
        self.trade_history: list[TradeAuditRecord] = []
        self.broker = broker or PaperBroker()
        self.risk_engine = risk_engine

    def get_portfolio_snapshot(self, current_prices: dict[str, float] | None = None) -> PortfolioSnapshot:
        """Create real-time snapshot of portfolio for risk evaluation."""
        prices = current_prices or {}
        pos_dict: dict[str, dict[str, Any]] = {}
        total_market_val = 0.0
        total_unrealized_pnl = 0.0

        for sym, pos in self.positions.items():
            curr_p = prices.get(sym, pos.average_price)
            pos.update_price(curr_p)
            pos_dict[sym] = {
                "quantity": pos.quantity,
                "avg_price": pos.average_price,
                "current_price": curr_p,
                "market_value": pos.market_value,
            }
            total_market_val += pos.market_value
            total_unrealized_pnl += pos.unrealized_pnl

        total_equity = self.cash + total_market_val
        if total_equity > self.peak_equity:
            self.peak_equity = total_equity

        return PortfolioSnapshot(
            total_value=round(total_equity, 2),
            cash=round(self.cash, 2),
            positions=pos_dict,
            unrealized_pnl=round(total_unrealized_pnl, 2),
            peak_value=round(self.peak_equity, 2),
            initial_value=round(self.initial_cash, 2),
        )

    def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        market_price: float,
        strategy_name: str = "",
    ) -> PaperOrder:
        """Validate against risk engine and simulate paper order execution."""
        if quantity <= 0:
            raise PortfolioError(f"Quantity must be positive, got {quantity}")

        snapshot = self.get_portfolio_snapshot({symbol: market_price})

        # Run independent risk validation if configured
        if self.risk_engine:
            prop = ProposedOrder(
                symbol=symbol,
                direction=side.value,
                quantity=quantity,
                price=market_price,
                strategy_name=strategy_name,
            )
            assessment = self.risk_engine.assess(prop, snapshot)
            if not assessment.approved:
                order = PaperOrder(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    requested_price=market_price,
                    status=OrderStatus.REJECTED,
                    strategy_name=strategy_name,
                    rejection_reason="; ".join(assessment.rejections),
                )
                self.orders.append(order)
                logger.warning("Paper order rejected by risk engine", symbol=symbol, reasons=assessment.rejections)
                return order

        # Handle Cash / Balance Constraints
        order = PaperOrder(
            symbol=symbol,
            side=side,
            quantity=quantity,
            requested_price=market_price,
            strategy_name=strategy_name,
        )

        if side == OrderSide.BUY:
            est_cost = (market_price * quantity) * 1.01  # approx buffer for slippage & fee
            if self.cash < est_cost:
                order.status = OrderStatus.REJECTED
                order.rejection_reason = f"Insufficient cash (required ₹{est_cost:.2f}, available ₹{self.cash:.2f})"
                self.orders.append(order)
                raise InsufficientFundsError(order.rejection_reason)

        elif side == OrderSide.SELL:
            existing = self.positions.get(symbol)
            if not existing or existing.quantity < quantity:
                order.status = OrderStatus.REJECTED
                order.rejection_reason = f"Insufficient position to sell (owned {existing.quantity if existing else 0}, attempted {quantity})"
                self.orders.append(order)
                raise PortfolioError(order.rejection_reason)

        # Execute fill via paper broker
        filled_order, audit = self.broker.execute(order, market_price)
        self.orders.append(filled_order)
        self.trade_history.append(audit)

        # Update cash and positions
        if side == OrderSide.BUY:
            self.cash -= ((filled_order.filled_price * quantity) + filled_order.transaction_cost)
            if symbol not in self.positions:
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=quantity,
                    average_price=filled_order.filled_price,
                    current_price=filled_order.filled_price,
                )
            else:
                pos = self.positions[symbol]
                total_shares = pos.quantity + quantity
                total_cost = (pos.quantity * pos.average_price) + (quantity * filled_order.filled_price)
                pos.average_price = round(total_cost / total_shares, 2)
                pos.quantity = total_shares
                pos.update_price(filled_order.filled_price)
        else:
            proceeds = (filled_order.filled_price * quantity) - filled_order.transaction_cost
            self.cash += proceeds
            pos = self.positions[symbol]
            pos.quantity -= quantity
            if pos.quantity == 0:
                del self.positions[symbol]
            else:
                pos.update_price(filled_order.filled_price)

        logger.info(
            "Paper order executed",
            symbol=symbol,
            side=side.value,
            qty=quantity,
            fill=filled_order.filled_price,
            cash=round(self.cash, 2),
        )
        return filled_order
