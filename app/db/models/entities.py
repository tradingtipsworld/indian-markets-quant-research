"""SQLAlchemy database models for persistence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class InstrumentModel(Base, TimestampMixin):
    """Persisted market instrument metadata."""

    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    exchange: Mapped[str] = mapped_column(String(16), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False)
    lot_size: Mapped[int] = mapped_column(Integer, default=1)
    tick_size: Mapped[float] = mapped_column(Float, default=0.05)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class OrderModel(Base, TimestampMixin):
    """Persisted order log."""

    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    order_type: Mapped[str] = mapped_column(String(16), default="market")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    requested_price: Mapped[float] = mapped_column(Float, nullable=False)
    filled_price: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(16), index=True, default="pending")
    strategy_name: Mapped[str] = mapped_column(String(64), default="")
    reason: Mapped[str] = mapped_column(Text, default="")


class AuditLogModel(Base, TimestampMixin):
    """Persisted security and risk audit events."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    actor: Mapped[str] = mapped_column(String(64), default="system")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    details_json: Mapped[str] = mapped_column(Text, default="{}")


class SetupRecordModel(Base, TimestampMixin):
    """Persisted intraday setup record (Setup DNA)."""

    __tablename__ = "setup_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    sector: Mapped[str] = mapped_column(String(32), default="GENERAL")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(16), default="1.0")
    regime: Mapped[str] = mapped_column(String(32), nullable=False)
    entry_trigger_price: Mapped[float] = mapped_column(Float, nullable=False)
    invalidation_level: Mapped[float] = mapped_column(Float, nullable=False)
    target_price: Mapped[float] = mapped_column(Float, nullable=False)
    risk_reward_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_transaction_cost: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(16), index=True, default="candidate")
    supporting_evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    contradicting_evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")


class LedgerBlockModel(Base, TimestampMixin):
    """Persisted cryptographic ledger block for tamper-evident signal audit."""

    __tablename__ = "ledger_blocks"

    entry_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(16), default="1.0")
    regime: Mapped[str] = mapped_column(String(32), nullable=False)
    entry_trigger_price: Mapped[float] = mapped_column(Float, nullable=False)
    invalidation_level: Mapped[float] = mapped_column(Float, nullable=False)
    target_price: Mapped[float] = mapped_column(Float, nullable=False)
    risk_reward_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    risk_assessment_json: Mapped[str] = mapped_column(Text, default="{}")
    ai_synthesis_summary: Mapped[str] = mapped_column(Text, default="")
    telegram_message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    outcome: Mapped[str] = mapped_column(String(32), index=True, default="candidate")
    outcome_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome_details_json: Mapped[str] = mapped_column(Text, default="{}")
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class DailySnapshotModel(Base, TimestampMixin):
    """Persisted daily portfolio snapshot and performance ledger."""

    __tablename__ = "daily_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    total_equity: Mapped[float] = mapped_column(Float, nullable=False)
    cash: Mapped[float] = mapped_column(Float, nullable=False)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    open_positions_count: Mapped[int] = mapped_column(Integer, default=0)
    completed_trades_count: Mapped[int] = mapped_column(Integer, default=0)
    win_rate_pct: Mapped[float] = mapped_column(Float, default=0.0)
    details_json: Mapped[str] = mapped_column(Text, default="{}")
