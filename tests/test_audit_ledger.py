"""Unit tests for Tamper-Evident Signal Ledger and Cryptographic Chaining."""

from app.audit.ledger import TamperEvidentSignalLedger, SignalOutcome


def test_ledger_append_and_hash_chain():
    ledger = TamperEvidentSignalLedger()

    entry1 = ledger.append(
        symbol="RELIANCE",
        strategy_name="orb_v1",
        regime="trending_bullish",
        entry_price=2500.0,
        invalidation_level=2480.0,
        target_price=2540.0,
        risk_reward_ratio=2.0,
    )
    assert entry1.sequence == 0
    assert entry1.previous_hash == "0" * 64
    assert len(entry1.entry_hash) == 64

    entry2 = ledger.append(
        symbol="TCS",
        strategy_name="vwap_pullback_v1",
        regime="trending_bullish",
        entry_price=3800.0,
        invalidation_level=3770.0,
        target_price=3860.0,
        risk_reward_ratio=2.0,
    )
    assert entry2.sequence == 1
    assert entry2.previous_hash == entry1.entry_hash

    # Verify integrity
    is_valid, msg = ledger.verify_integrity()
    assert is_valid is True
    assert "verified successfully" in msg


def test_ledger_detects_tampering():
    ledger = TamperEvidentSignalLedger()

    entry = ledger.append(
        symbol="INFY",
        strategy_name="orb_v1",
        regime="trending_bullish",
        entry_price=1800.0,
        invalidation_level=1780.0,
        target_price=1840.0,
        risk_reward_ratio=2.0,
    )

    # Maliciously attempt to mutate entry data directly
    entry.entry_trigger_price = 9999.0

    # Integrity verification must catch the tamper
    is_valid, msg = ledger.verify_integrity()
    assert is_valid is False
    assert "tampered" in msg.lower()


def test_ledger_outcome_and_scorecard():
    ledger = TamperEvidentSignalLedger()

    entry1 = ledger.append(
        symbol="SBIN",
        strategy_name="orb_v1",
        regime="trending_bullish",
        entry_price=800.0,
        invalidation_level=790.0,
        target_price=820.0,
        risk_reward_ratio=2.0,
    )
    entry2 = ledger.append(
        symbol="LT",
        strategy_name="vwap_pullback_v1",
        regime="range_bound",
        entry_price=3500.0,
        invalidation_level=3470.0,
        target_price=3560.0,
        risk_reward_ratio=2.0,
    )

    ledger.record_outcome(entry1.entry_id, SignalOutcome.CLOSED_WIN)
    ledger.record_outcome(entry2.entry_id, SignalOutcome.INVALIDATED)

    scorecard = ledger.get_scorecard()
    assert scorecard["total_signals_recorded"] == 2
    assert scorecard["wins"] == 1
    assert scorecard["invalidated_setups"] == 1
    assert scorecard["win_rate_pct"] == 100.0
