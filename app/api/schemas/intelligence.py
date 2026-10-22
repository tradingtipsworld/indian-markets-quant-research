"""Pydantic schemas for the Indian Market Intelligence and Dashboard API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SetupDNAResponse(BaseModel):
    """Auditable Setup DNA record."""

    id: str
    symbol: str
    sector: str = "GENERAL"
    timestamp: datetime
    strategy_name: str
    strategy_version: str = "1.0"
    regime: str
    entry_trigger_price: float
    invalidation_level: float
    target_price: float
    risk_reward_ratio: float
    estimated_transaction_cost: float = 0.0
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    rejection_reason: str | None = None
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ActiveSetupsResponse(BaseModel):
    """Response containing currently active candidate and triggered setups."""

    count: int
    setups: list[SetupDNAResponse]


class FailedSetupsResponse(BaseModel):
    """Response containing failed or invalidated setups with breach diagnostics."""

    count: int
    setups: list[SetupDNAResponse]


class MarketPulseResponse(BaseModel):
    """Real-time Indian market pulse, calendar state, and regime overview."""

    timestamp: datetime
    session_state: str
    is_trading_day: bool
    benchmark_symbol: str = "NIFTY50"
    regime: str
    regime_confidence: float
    sector_performance: dict[str, float] = Field(default_factory=dict)
    advances: int = 0
    declines: int = 0
    unchanged: int = 0


class SectorPerformanceResponse(BaseModel):
    """Sector performance rankings and momentum."""

    timestamp: datetime
    sector_returns: dict[str, float]
    top_sector: str | None = None
    bottom_sector: str | None = None


class LedgerScorecardResponse(BaseModel):
    """Cryptographic ledger verification status and historical trade scorecard."""

    integrity_verified: bool
    verification_message: str
    total_signals_recorded: int
    outcomes_breakdown: dict[str, int]
    completed_trades: int
    wins: int
    losses: int
    invalidated_setups: int
    expired_setups: int
    win_rate_pct: float
    latest_block_hash: str | None = None
