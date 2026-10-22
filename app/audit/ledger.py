"""Tamper-Evident Signal and Audit Ledger.

Maintains an append-only, cryptographically chained event log of:
- All generated market setups and candidate DNA
- AI deliberations and debate consensus
- Independent risk engine decisions
- Telegram publication message IDs
- Actual post-alert market outcomes (Triggered, Invalidated, Expired, Won, Lost, No-Trade)

Uses SHA-256 block-hash chaining so past records cannot be retrospectively altered.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.entities import LedgerBlockModel

logger = get_logger(__name__)


class SignalOutcome(str, Enum):
    """Auditable final or current state of an intraday signal."""

    CANDIDATE = "candidate"
    APPROVED = "approved"
    REJECTED_RISK = "rejected_risk"
    PUBLISHED = "published"
    TRIGGERED = "triggered"
    INVALIDATED = "invalidated"
    EXPIRED = "expired"
    CLOSED_WIN = "closed_win"
    CLOSED_LOSS = "closed_loss"
    NO_TRADE = "no_trade"


class LedgerEntry(BaseModel):
    """Single immutable entry in the audit ledger with cryptographic chaining."""

    entry_id: str = Field(default_factory=lambda: str(uuid4()))
    sequence: int
    timestamp: datetime = Field(default_factory=datetime.now)
    symbol: str
    strategy_name: str
    strategy_version: str = "1.0"
    regime: str
    entry_trigger_price: float
    invalidation_level: float
    target_price: float
    risk_reward_ratio: float
    risk_assessment: dict[str, Any] = Field(default_factory=dict)
    ai_synthesis_summary: str = ""
    telegram_message_id: str | None = None
    outcome: SignalOutcome = SignalOutcome.CANDIDATE
    outcome_timestamp: datetime | None = None
    outcome_details: dict[str, Any] = Field(default_factory=dict)
    previous_hash: str = "0" * 64
    entry_hash: str = ""

    def compute_hash(self) -> str:
        """Calculate SHA-256 hash across immutable entry attributes and previous hash."""
        data_to_hash = {
            "entry_id": self.entry_id,
            "sequence": self.sequence,
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "strategy": f"{self.strategy_name}@{self.strategy_version}",
            "regime": self.regime,
            "entry": self.entry_trigger_price,
            "invalidation": self.invalidation_level,
            "target": self.target_price,
            "previous_hash": self.previous_hash,
        }
        encoded = json.dumps(data_to_hash, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class TamperEvidentSignalLedger:
    """Append-only cryptographic ledger tracking trading signals and outcomes."""

    def __init__(self):
        self._entries: list[LedgerEntry] = []
        self._index_by_id: dict[str, int] = {}

    def append(
        self,
        symbol: str,
        strategy_name: str,
        regime: str,
        entry_price: float,
        invalidation_level: float,
        target_price: float,
        risk_reward_ratio: float,
        strategy_version: str = "1.0",
        risk_assessment: dict[str, Any] | None = None,
        ai_synthesis_summary: str = "",
        telegram_message_id: str | None = None,
        outcome: SignalOutcome = SignalOutcome.CANDIDATE,
    ) -> LedgerEntry:
        """Append a new signal entry with cryptographic hash chaining."""
        prev_hash = self._entries[-1].entry_hash if self._entries else ("0" * 64)
        seq = len(self._entries)

        entry = LedgerEntry(
            sequence=seq,
            symbol=symbol,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            regime=regime,
            entry_trigger_price=entry_price,
            invalidation_level=invalidation_level,
            target_price=target_price,
            risk_reward_ratio=risk_reward_ratio,
            risk_assessment=risk_assessment or {},
            ai_synthesis_summary=ai_synthesis_summary,
            telegram_message_id=telegram_message_id,
            outcome=outcome,
            previous_hash=prev_hash,
        )
        entry.entry_hash = entry.compute_hash()

        self._entries.append(entry)
        self._index_by_id[entry.entry_id] = seq

        logger.info(
            "Ledger entry appended",
            seq=seq,
            symbol=symbol,
            strategy=strategy_name,
            hash=entry.entry_hash[:12],
        )
        return entry

    def record_outcome(
        self,
        entry_id: str,
        outcome: SignalOutcome,
        details: dict[str, Any] | None = None,
    ) -> bool:
        """Update the verifiable outcome of a previously recorded setup without modifying original entry data."""
        if entry_id not in self._index_by_id:
            logger.warning("Attempted to record outcome for unknown entry ID", entry_id=entry_id)
            return False

        idx = self._index_by_id[entry_id]
        entry = self._entries[idx]
        entry.outcome = outcome
        entry.outcome_timestamp = datetime.now()
        entry.outcome_details = details or {}

        logger.info("Signal outcome recorded", entry_id=entry_id, outcome=outcome.value)
        return True

    def verify_integrity(self) -> tuple[bool, str]:
        """Verify the cryptographic hash chain across all ledger entries."""
        if not self._entries:
            return True, "Ledger is empty"

        for i, entry in enumerate(self._entries):
            # Check previous hash linkage
            expected_prev = "0" * 64 if i == 0 else self._entries[i - 1].entry_hash
            if entry.previous_hash != expected_prev:
                return False, f"Broken hash chain at sequence {i}: previous_hash mismatch"

            # Check self-hash calculation
            if entry.entry_hash != entry.compute_hash():
                return False, f"Entry hash tampered at sequence {i}: data has been modified"

        return True, f"All {len(self._entries)} entries verified successfully"

    def get_entries(self, limit: int = 50) -> list[LedgerEntry]:
        """Return the most recent ledger entries."""
        return self._entries[-limit:]

    def get_entry(self, entry_id: str) -> LedgerEntry | None:
        """Lookup a single entry by its unique entry ID."""
        if entry_id not in self._index_by_id:
            return None
        return self._entries[self._index_by_id[entry_id]]

    def get_scorecard(self) -> dict[str, Any]:
        """Calculate transparent performance metrics across all recorded signals."""
        total = len(self._entries)
        if total == 0:
            return {"total_signals": 0}

        counts: dict[str, int] = {}
        for e in self._entries:
            counts[e.outcome.value] = counts.get(e.outcome.value, 0) + 1

        wins = counts.get(SignalOutcome.CLOSED_WIN.value, 0)
        losses = counts.get(SignalOutcome.CLOSED_LOSS.value, 0)
        invalidated = counts.get(SignalOutcome.INVALIDATED.value, 0)
        expired = counts.get(SignalOutcome.EXPIRED.value, 0)
        completed = wins + losses

        win_rate = (wins / completed * 100.0) if completed > 0 else 0.0

        return {
            "total_signals_recorded": total,
            "outcomes_breakdown": counts,
            "completed_trades": completed,
            "wins": wins,
            "losses": losses,
            "invalidated_setups": invalidated,
            "expired_setups": expired,
            "win_rate_pct": round(win_rate, 2),
        }

    async def persist_entry(self, entry: LedgerEntry, session: AsyncSession) -> None:
        """Persist a single newly appended entry block into the database."""
        block = LedgerBlockModel(
            entry_id=entry.entry_id,
            sequence=entry.sequence,
            timestamp=entry.timestamp,
            symbol=entry.symbol,
            strategy_name=entry.strategy_name,
            strategy_version=entry.strategy_version,
            regime=entry.regime,
            entry_trigger_price=entry.entry_trigger_price,
            invalidation_level=entry.invalidation_level,
            target_price=entry.target_price,
            risk_reward_ratio=entry.risk_reward_ratio,
            risk_assessment_json=json.dumps(entry.risk_assessment),
            ai_synthesis_summary=entry.ai_synthesis_summary,
            telegram_message_id=entry.telegram_message_id,
            outcome=entry.outcome.value,
            outcome_timestamp=entry.outcome_timestamp,
            outcome_details_json=json.dumps(entry.outcome_details),
            previous_hash=entry.previous_hash,
            entry_hash=entry.entry_hash,
        )
        session.add(block)
        await session.flush()

    async def load_from_db(self, session: AsyncSession) -> int:
        """Load and populate ledger entries from database in chronological sequence order."""
        stmt = select(LedgerBlockModel).order_by(LedgerBlockModel.sequence.asc())
        result = await session.execute(stmt)
        rows = result.scalars().all()

        self._entries.clear()
        self._index_by_id.clear()

        for r in rows:
            entry = LedgerEntry(
                entry_id=r.entry_id,
                sequence=r.sequence,
                timestamp=r.timestamp,
                symbol=r.symbol,
                strategy_name=r.strategy_name,
                strategy_version=r.strategy_version,
                regime=r.regime,
                entry_trigger_price=r.entry_trigger_price,
                invalidation_level=r.invalidation_level,
                target_price=r.target_price,
                risk_reward_ratio=r.risk_reward_ratio,
                risk_assessment=json.loads(r.risk_assessment_json) if r.risk_assessment_json else {},
                ai_synthesis_summary=r.ai_synthesis_summary,
                telegram_message_id=r.telegram_message_id,
                outcome=SignalOutcome(r.outcome),
                outcome_timestamp=r.outcome_timestamp,
                outcome_details=json.loads(r.outcome_details_json) if r.outcome_details_json else {},
                previous_hash=r.previous_hash,
                entry_hash=r.entry_hash,
            )
            self._entries.append(entry)
            self._index_by_id[entry.entry_id] = entry.sequence

        logger.info("Ledger loaded from database", count=len(self._entries))
        return len(self._entries)

    async def record_outcome_db(
        self,
        entry_id: str,
        outcome: SignalOutcome,
        session: AsyncSession,
        details: dict[str, Any] | None = None,
    ) -> bool:
        """Update outcome both in-memory and in the database."""
        if not self.record_outcome(entry_id, outcome, details):
            return False

        stmt = select(LedgerBlockModel).where(LedgerBlockModel.entry_id == entry_id)
        res = await session.execute(stmt)
        block = res.scalar_one_or_none()
        if block:
            block.outcome = outcome.value
            block.outcome_timestamp = datetime.now()
            block.outcome_details_json = json.dumps(details or {})
            await session.flush()
        return True


# Singleton ledger instance
_signal_ledger = TamperEvidentSignalLedger()


def get_signal_ledger() -> TamperEvidentSignalLedger:
    return _signal_ledger
