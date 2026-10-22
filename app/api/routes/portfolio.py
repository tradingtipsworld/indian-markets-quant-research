"""Paper trading portfolio API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.portfolio.manager import PortfolioManager
from app.portfolio.models import OrderSide
from app.risk.engine import RiskEngine

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

# In-memory singleton portfolio instance for local dev
_risk_engine = RiskEngine(get_settings())
_portfolio_manager = PortfolioManager(
    initial_cash=get_settings().paper_initial_cash,
    risk_engine=_risk_engine,
)


class PaperOrderRequest(BaseModel):
    symbol: str
    side: OrderSide
    quantity: int = Field(gt=0)
    current_price: float = Field(gt=0.0)
    strategy_name: str = "manual_paper"


@router.get("/summary")
async def get_portfolio_summary():
    """Retrieve current paper trading portfolio snapshot."""
    return {
        "cash": _portfolio_manager.cash,
        "total_value": _portfolio_manager.total_value,
        "unrealized_pnl": _portfolio_manager.unrealized_pnl,
        "realized_pnl": _portfolio_manager.realized_pnl,
        "positions_count": len(_portfolio_manager.positions),
        "positions": {
            s: {
                "quantity": p.quantity,
                "avg_price": p.average_entry_price,
                "current_price": p.current_price,
                "market_value": p.market_value,
                "unrealized_pnl": p.unrealized_pnl,
                "unrealized_pnl_pct": p.unrealized_pnl_pct,
            }
            for s, p in _portfolio_manager.positions.items()
        },
    }


@router.get("/orders")
async def list_orders():
    """List recent paper orders and fill audit logs."""
    return {
        "orders": [o.model_dump() for o in _portfolio_manager.orders],
        "audit_trades": [t.model_dump() for t in _portfolio_manager.trade_history],
    }


@router.post("/order")
async def submit_paper_order(req: PaperOrderRequest):
    """Submit a paper order through risk controls and simulated execution."""
    order = _portfolio_manager.submit_order(
        symbol=req.symbol,
        side=req.side,
        quantity=req.quantity,
        market_price=req.current_price,
        strategy_name=req.strategy_name,
    )
    return {
        "status": order.status.value,
        "order": order.model_dump(),
    }


@router.post("/kill-switch/toggle")
async def toggle_kill_switch(active: bool):
    """Emergency control: toggle the risk kill switch."""
    if active:
        _risk_engine.activate_kill_switch()
    else:
        _risk_engine.deactivate_kill_switch()

    return {
        "kill_switch_active": _risk_engine.is_kill_switch_active,
        "message": "Kill switch state updated successfully",
    }
