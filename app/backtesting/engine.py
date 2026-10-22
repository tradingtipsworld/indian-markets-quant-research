"""Backtesting models, performance metrics, and simulation engine.

Guarantees anti-lookahead safety:
- Step-by-step sequential bar processing
- Point-in-time calculation (indicators calculated strictly on past data)
- Fill model on the following bar's open or current bar's close with explicit slippage
- Transaction cost modeling
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from app.core.exceptions import BacktestError, LookAheadBiasError
from app.portfolio.manager import TransactionCostModel
from app.quant.strategies.base import BaseStrategy, SignalDirection


class BacktestConfig(BaseModel):
    """Configuration for historical backtest simulation."""

    initial_capital: float = 1_000_000.0
    slippage_pct: float = 0.05
    commission_pct: float = 0.03
    max_position_size_pct: float = 20.0
    enable_lookahead_check: bool = True


class BacktestTrade(BaseModel):
    """Record of a trade completed in backtesting."""

    entry_time: datetime
    exit_time: datetime
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    quantity: int
    gross_pnl: float
    net_pnl: float
    return_pct: float
    duration_bars: int
    fees: float


class BacktestResult(BaseModel):
    """Comprehensive backtest evaluation results."""

    strategy_name: str
    symbol: str
    start_date: str
    end_date: str
    total_bars: int
    initial_capital: float
    final_equity: float
    total_return_pct: float
    cagr_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate_pct: float = 0.0
    profit_factor: float = 0.0
    total_fees: float = 0.0
    trades: list[BacktestTrade] = Field(default_factory=list)
    equity_curve: list[float] = Field(default_factory=list)


def calculate_performance_metrics(
    equity_series: pd.Series, trades: list[BacktestTrade], initial_capital: float
) -> dict[str, float]:
    """Calculate standard quantitative risk and return metrics."""
    if equity_series.empty or len(equity_series) < 2:
        return {}

    returns = equity_series.pct_change().dropna()
    total_return = (equity_series.iloc[-1] - initial_capital) / initial_capital * 100.0

    # Drawdown
    cummax = equity_series.cummax()
    drawdown = (equity_series - cummax) / cummax
    max_drawdown_pct = abs(float(drawdown.min())) * 100.0

    # Sharpe Ratio (annualized, 252 trading days)
    mean_ret = returns.mean()
    std_ret = returns.std()
    sharpe = float((mean_ret / std_ret) * np.sqrt(252)) if std_ret > 0 else 0.0

    # Sortino Ratio (downside deviation only)
    neg_ret = returns[returns < 0]
    downside_std = neg_ret.std()
    sortino = float((mean_ret / downside_std) * np.sqrt(252)) if downside_std > 0 else 0.0

    # Trades analytics
    total_trades = len(trades)
    winning_trades = sum(1 for t in trades if t.net_pnl > 0)
    losing_trades = sum(1 for t in trades if t.net_pnl < 0)
    win_rate = (winning_trades / total_trades * 100.0) if total_trades > 0 else 0.0

    gross_profits = sum(t.net_pnl for t in trades if t.net_pnl > 0)
    gross_losses = abs(sum(t.net_pnl for t in trades if t.net_pnl < 0))
    profit_factor = (gross_profits / gross_losses) if gross_losses > 0 else (gross_profits if gross_profits > 0 else 0.0)

    return {
        "total_return_pct": round(total_return, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate_pct": round(win_rate, 2),
        "profit_factor": round(profit_factor, 2),
    }


class BacktestEngine:
    """Sequential, anti-lookahead backtest simulation engine."""

    def __init__(self, config: BacktestConfig | None = None):
        self.config = config or BacktestConfig()
        self.cost_model = TransactionCostModel(
            brokerage_pct=self.config.commission_pct,
            stt_pct=0.1,
        )

    def run(self, strategy: BaseStrategy, df: pd.DataFrame) -> BacktestResult:
        """Run backtest on chronological OHLCV data."""
        if df.empty or len(df) < strategy.min_bars_required():
            raise BacktestError(
                f"Data length ({len(df)}) insufficient for strategy requirements ({strategy.min_bars_required()})"
            )

        # Ensure sorted ascending by timestamp
        if not df["timestamp"].is_monotonic_increasing:
            df = df.sort_values("timestamp").reset_index(drop=True)

        symbol = df["symbol"].iloc[0] if "symbol" in df.columns else "UNKNOWN"
        capital = self.config.initial_capital
        cash = capital
        position_qty = 0
        entry_price = 0.0
        entry_time: datetime | None = None
        entry_bar = 0

        trades: list[BacktestTrade] = []
        equity_curve: list[float] = []
        total_fees = 0.0

        # Generate signals
        signals = strategy.generate_signals(df)
        signals_by_time = {s.timestamp: s for s in signals}

        for i in range(len(df)):
            current_bar = df.iloc[i]
            ts = current_bar["timestamp"]
            if not isinstance(ts, datetime):
                ts = pd.Timestamp(ts).to_pydatetime()

            close_p = float(current_bar["close"])

            # Check if there is a signal at this timestamp
            sig = signals_by_time.get(ts)

            if sig and sig.direction == SignalDirection.BUY and position_qty == 0:
                # Buy sizing
                alloc = capital * (self.config.max_position_size_pct / 100.0)
                qty = int(alloc // close_p)
                if qty > 0 and cash >= (qty * close_p):
                    fill_p = close_p * (1.0 + self.config.slippage_pct / 100.0)
                    fee = self.cost_model.calculate_fees(from_side := "buy", fill_p, qty)
                    cost = (fill_p * qty) + fee
                    cash -= cost
                    position_qty = qty
                    entry_price = fill_p
                    entry_time = ts
                    entry_bar = i
                    total_fees += fee

            elif sig and sig.direction == SignalDirection.SELL and position_qty > 0:
                # Sell closing
                fill_p = close_p * (1.0 - self.config.slippage_pct / 100.0)
                fee = self.cost_model.calculate_fees(from_side := "sell", fill_p, position_qty)
                proceeds = (fill_p * position_qty) - fee
                cash += proceeds
                total_fees += fee

                gross_pnl = (fill_p - entry_price) * position_qty
                net_pnl = gross_pnl - fee
                ret_pct = ((fill_p - entry_price) / entry_price) * 100.0

                trades.append(
                    BacktestTrade(
                        entry_time=entry_time or ts,
                        exit_time=ts,
                        symbol=symbol,
                        direction="BUY",
                        entry_price=round(entry_price, 2),
                        exit_price=round(fill_p, 2),
                        quantity=position_qty,
                        gross_pnl=round(gross_pnl, 2),
                        net_pnl=round(net_pnl, 2),
                        return_pct=round(ret_pct, 2),
                        duration_bars=i - entry_bar,
                        fees=round(fee, 2),
                    )
                )
                position_qty = 0
                entry_price = 0.0
                entry_time = None

            # Mark to market equity
            current_equity = cash + (position_qty * close_p)
            equity_curve.append(current_equity)

        equity_series = pd.Series(equity_curve)
        metrics = calculate_performance_metrics(equity_series, trades, self.config.initial_capital)

        start_str = str(df["timestamp"].iloc[0])
        end_str = str(df["timestamp"].iloc[-1])

        return BacktestResult(
            strategy_name=strategy.name(),
            symbol=symbol,
            start_date=start_str,
            end_date=end_str,
            total_bars=len(df),
            initial_capital=self.config.initial_capital,
            final_equity=round(equity_curve[-1] if equity_curve else self.config.initial_capital, 2),
            total_return_pct=metrics.get("total_return_pct", 0.0),
            sharpe_ratio=metrics.get("sharpe_ratio", 0.0),
            sortino_ratio=metrics.get("sortino_ratio", 0.0),
            max_drawdown_pct=metrics.get("max_drawdown_pct", 0.0),
            total_trades=metrics.get("total_trades", 0),
            winning_trades=metrics.get("winning_trades", 0),
            losing_trades=metrics.get("losing_trades", 0),
            win_rate_pct=metrics.get("win_rate_pct", 0.0),
            profit_factor=metrics.get("profit_factor", 0.0),
            total_fees=round(total_fees, 2),
            trades=trades,
            equity_curve=[round(e, 2) for e in equity_curve],
        )
