"""Unit and integration tests for database persistence models and ledger sync."""

from datetime import datetime
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.audit.ledger import LedgerEntry, SignalOutcome, TamperEvidentSignalLedger
from app.db.base import Base
from app.db.models.entities import DailySnapshotModel, LedgerBlockModel, SetupRecordModel


@pytest.fixture
async def async_test_session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_ledger_database_persistence_and_reload(async_test_session):
    ledger = TamperEvidentSignalLedger()

    entry1 = ledger.append(
        symbol="RELIANCE",
        strategy_name="orb_v1",
        regime="trending_bullish",
        entry_price=2600.0,
        invalidation_level=2575.0,
        target_price=2650.0,
        risk_reward_ratio=2.0,
        ai_synthesis_summary="Bullish expansion",
    )
    entry2 = ledger.append(
        symbol="TCS",
        strategy_name="vwap_pullback_v1",
        regime="range_bound",
        entry_price=4100.0,
        invalidation_level=4070.0,
        target_price=4160.0,
        risk_reward_ratio=2.0,
        ai_synthesis_summary="VWAP bounce",
    )

    # Persist entries to DB
    await ledger.persist_entry(entry1, async_test_session)
    await ledger.persist_entry(entry2, async_test_session)
    await async_test_session.commit()

    # Create fresh empty ledger instance and reload from DB
    restored_ledger = TamperEvidentSignalLedger()
    loaded_count = await restored_ledger.load_from_db(async_test_session)
    assert loaded_count == 2

    # Verify cryptographic integrity of reloaded ledger
    is_valid, msg = restored_ledger.verify_integrity()
    assert is_valid is True
    assert "verified successfully" in msg

    # Update outcome in DB
    updated = await restored_ledger.record_outcome_db(
        entry1.entry_id,
        SignalOutcome.CLOSED_WIN,
        async_test_session,
        details={"exit_price": 2650.0},
    )
    assert updated is True
    await async_test_session.commit()

    # Verify DB reflected the outcome
    stmt = select(LedgerBlockModel).where(LedgerBlockModel.entry_id == entry1.entry_id)
    res = await async_test_session.execute(stmt)
    block = res.scalar_one()
    assert block.outcome == SignalOutcome.CLOSED_WIN.value


@pytest.mark.asyncio
async def test_setup_record_and_daily_snapshot_models(async_test_session):
    # Test SetupRecordModel
    setup = SetupRecordModel(
        id="setup-1234",
        symbol="INFY",
        sector="IT",
        timestamp=datetime.now(),
        strategy_name="momentum_breakout_v1",
        strategy_version="1.0",
        regime="trending_bullish",
        entry_trigger_price=1800.0,
        invalidation_level=1780.0,
        target_price=1840.0,
        risk_reward_ratio=2.0,
        status="candidate",
    )
    async_test_session.add(setup)

    # Test DailySnapshotModel
    snapshot = DailySnapshotModel(
        snapshot_date=datetime.now(),
        total_equity=1_050_000.0,
        cash=950_000.0,
        realized_pnl=50_000.0,
        unrealized_pnl=0.0,
        open_positions_count=1,
        completed_trades_count=4,
        win_rate_pct=75.0,
    )
    async_test_session.add(snapshot)
    await async_test_session.commit()

    # Query back
    res = await async_test_session.execute(select(SetupRecordModel).where(SetupRecordModel.id == "setup-1234"))
    saved_setup = res.scalar_one()
    assert saved_setup.symbol == "INFY"
    assert saved_setup.risk_reward_ratio == 2.0

    snap_res = await async_test_session.execute(select(DailySnapshotModel))
    saved_snap = snap_res.scalar_one()
    assert saved_snap.total_equity == 1_050_000.0
    assert saved_snap.win_rate_pct == 75.0
