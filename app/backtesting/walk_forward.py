"""Walk-Forward and Out-of-Sample Performance Validation.

Splits chronological market data into distinct In-Sample (IS) and Out-of-Sample (OOS) windows
to detect look-ahead bias, curve-fitting, and strategy degradation across regime shifts.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

from app.backtesting.engine import BacktestConfig, BacktestEngine, BacktestResult
from app.core.exceptions import BacktestError
from app.core.logging import get_logger
from app.quant.strategies.base import BaseStrategy

logger = get_logger(__name__)


class WalkForwardEvaluationResult(BaseModel):
    """Comparative report between in-sample training and out-of-sample testing."""

    strategy_name: str
    symbol: str
    in_sample_bars: int
    out_of_sample_bars: int
    in_sample_return_pct: float
    out_of_sample_return_pct: float
    in_sample_sharpe: float
    out_of_sample_sharpe: float
    in_sample_win_rate_pct: float
    out_of_sample_win_rate_pct: float
    in_sample_max_dd_pct: float
    out_of_sample_max_dd_pct: float
    robustness_ratio: float = Field(
        description="OOS Sharpe / IS Sharpe. Values < 0.5 suggest potential curve-fitting or regime breakdown."
    )
    is_robust: bool
    notes: list[str] = Field(default_factory=list)


class WalkForwardEvaluator:
    """Evaluates strategy stability and robustness across split chronological horizons."""

    def __init__(self, in_sample_pct: float = 0.70, config: BacktestConfig | None = None):
        if not (0.50 <= in_sample_pct <= 0.85):
            raise ValueError(f"In-sample ratio must be between 0.50 and 0.85, got {in_sample_pct}")
        self.in_sample_pct = in_sample_pct
        self.config = config or BacktestConfig()
        self.engine = BacktestEngine(self.config)

    def evaluate(self, strategy: BaseStrategy, df: pd.DataFrame) -> WalkForwardEvaluationResult:
        """Run sequential split backtest and compare in-sample vs out-of-sample metrics."""
        if df.empty or len(df) < (strategy.min_bars_required() * 2):
            raise BacktestError(
                f"Data length ({len(df)}) insufficient for walk-forward evaluation (min {strategy.min_bars_required() * 2})"
            )

        # Sort chronologically ascending
        if not df["timestamp"].is_monotonic_increasing:
            df = df.sort_values("timestamp").reset_index(drop=True)

        split_idx = int(len(df) * self.in_sample_pct)
        is_df = df.iloc[:split_idx].copy().reset_index(drop=True)
        oos_df = df.iloc[split_idx:].copy().reset_index(drop=True)

        # Execute In-Sample
        is_result: BacktestResult = self.engine.run(strategy, is_df)

        # Execute Out-of-Sample
        oos_result: BacktestResult = self.engine.run(strategy, oos_df)

        # Calculate robustness / degradation ratio
        is_sharpe = max(is_result.sharpe_ratio, 0.01)
        oos_sharpe = max(oos_result.sharpe_ratio, 0.0)
        robustness = round(oos_sharpe / is_sharpe, 2)

        notes: list[str] = []
        is_robust = True

        if robustness < 0.50:
            is_robust = False
            notes.append(
                f"Performance degraded significantly out-of-sample (Robustness ratio {robustness:.2f} < 0.50). "
                "Potential curve-fitting or regime transition."
            )
        else:
            notes.append(f"Strategy demonstrated acceptable out-of-sample stability (Robustness ratio {robustness:.2f}).")

        if oos_result.max_drawdown_pct > (is_result.max_drawdown_pct * 1.5):
            notes.append(
                f"Out-of-sample drawdown ({oos_result.max_drawdown_pct:.1f}%) exceeded in-sample peak ({is_result.max_drawdown_pct:.1f}%)."
            )

        return WalkForwardEvaluationResult(
            strategy_name=strategy.name(),
            symbol=df["symbol"].iloc[0] if "symbol" in df.columns else "UNKNOWN",
            in_sample_bars=len(is_df),
            out_of_sample_bars=len(oos_df),
            in_sample_return_pct=is_result.total_return_pct,
            out_of_sample_return_pct=oos_result.total_return_pct,
            in_sample_sharpe=is_result.sharpe_ratio,
            out_of_sample_sharpe=oos_result.sharpe_ratio,
            in_sample_win_rate_pct=is_result.win_rate_pct,
            out_of_sample_win_rate_pct=oos_result.win_rate_pct,
            in_sample_max_dd_pct=is_result.max_drawdown_pct,
            out_of_sample_max_dd_pct=oos_result.max_drawdown_pct,
            robustness_ratio=robustness,
            is_robust=is_robust,
            notes=notes,
        )
