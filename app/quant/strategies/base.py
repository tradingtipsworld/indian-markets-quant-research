"""Strategy interface — defines the contract for all trading strategies.

Strategies produce signals but do NOT execute trades.
Execution is handled by the portfolio/paper trading module
after passing through the risk engine.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field


class SignalDirection(str, Enum):
    """Trading signal direction."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class Signal(BaseModel):
    """Trading signal produced by a strategy."""

    symbol: str
    direction: SignalDirection
    strength: float = Field(ge=0.0, le=1.0, description="Signal strength 0.0 to 1.0")
    timestamp: datetime
    strategy_name: str
    timeframe: str = "1d"
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_actionable(self) -> bool:
        """Whether this signal suggests opening/closing a position."""
        return self.direction != SignalDirection.HOLD


class StrategyParameters(BaseModel):
    """Base class for strategy parameters.

    Each strategy should define its own parameters subclass.
    """

    model_config = {"frozen": True}


class StrategyResult(BaseModel):
    """Result of running a strategy on historical data."""

    strategy_name: str
    signals: list[Signal] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    computed_at: datetime = Field(default_factory=datetime.now)


class BaseStrategy(ABC):
    """Abstract base strategy.

    All strategies must implement this interface.
    Strategies receive OHLCV data and produce signals.
    They must NOT have side effects or access future data.
    """

    @abstractmethod
    def name(self) -> str:
        """Unique strategy name."""
        ...

    @abstractmethod
    def description(self) -> str:
        """Human-readable strategy description."""
        ...

    @abstractmethod
    def generate_signals(
        self, df: pd.DataFrame, parameters: StrategyParameters | None = None
    ) -> list[Signal]:
        """Generate trading signals from OHLCV data.

        Args:
            df: DataFrame with columns [timestamp, open, high, low, close, volume].
                Data is sorted ascending by timestamp.
                The strategy must NOT modify this DataFrame.
            parameters: Optional strategy-specific parameters.

        Returns:
            List of Signal objects. May be empty if no signals are generated.

        Important:
            - Must NOT access future data (look-ahead bias).
            - Must be deterministic given the same inputs.
            - Must NOT execute trades or call external APIs.
        """
        ...

    def validate_data(self, df: pd.DataFrame) -> bool:
        """Check if the input data has the required columns and minimum rows."""
        required = {"timestamp", "open", "high", "low", "close", "volume"}
        if not required.issubset(df.columns):
            return False
        return len(df) >= self.min_bars_required()

    def min_bars_required(self) -> int:
        """Minimum number of bars needed for this strategy to produce signals."""
        return 1
