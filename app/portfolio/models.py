"""Portfolio and paper trading models and entities."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class PaperOrder(BaseModel):
    """Simulated order representation."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    symbol: str
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    quantity: int
    requested_price: float
    filled_price: float = 0.0
    filled_quantity: int = 0
    status: OrderStatus = OrderStatus.PENDING
    slippage: float = 0.0
    transaction_cost: float = 0.0
    strategy_name: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    filled_at: datetime | None = None
    reason: str = ""


class Position(BaseModel):
    """Open position in an asset."""

    symbol: str
    quantity: int = 0
    average_entry_price: float = 0.0
    current_price: float = 0.0
    realized_pnl: float = 0.0
    updated_at: datetime = Field(default_factory=datetime.now)

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        if self.quantity == 0:
            return 0.0
        return (self.current_price - self.average_entry_price) * self.quantity

    @property
    def unrealized_pnl_pct(self) -> float:
        cost = self.quantity * self.average_entry_price
        if cost == 0:
            return 0.0
        return (self.unrealized_pnl / cost) * 100.0


class TradeAuditRecord(BaseModel):
    """Immutable audit record for filled trades."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    slippage: float
    fees: float
    net_value: float
    executed_at: datetime = Field(default_factory=datetime.now)
    strategy_name: str = ""
    notes: str = "Paper Execution Only"
