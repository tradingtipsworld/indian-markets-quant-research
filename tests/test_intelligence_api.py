"""Integration tests for Market Intelligence and Dashboard API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.audit.ledger import SignalOutcome, get_signal_ledger
from app.main import app
from app.quant.regime import MarketRegime
from app.quant.scanner import IntradaySetupRecord, SetupStatus, get_setup_store


@pytest.mark.asyncio
async def test_market_pulse_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/market/pulse")
        assert resp.status_code == 200
        data = resp.json()
        assert "session_state" in data
        assert "is_trading_day" in data
        assert data["benchmark_symbol"] == "NIFTY50"
        assert "advances" in data
        assert "declines" in data


@pytest.mark.asyncio
async def test_setups_active_and_detail_endpoint():
    store = get_setup_store()
    store.clear()

    # Seed an active setup
    setup = IntradaySetupRecord(
        symbol="TCS",
        sector="IT",
        strategy_name="orb_v1",
        regime=MarketRegime.TRENDING_BULLISH,
        entry_trigger_price=3900.0,
        invalidation_level=3860.0,
        target_price=3980.0,
        risk_reward_ratio=2.0,
        estimated_transaction_cost=42.50,
        supporting_evidence=["Breakout above 15m high"],
        status=SetupStatus.CANDIDATE,
    )
    store.add_setup(setup)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test active setups list
        resp = await client.get("/api/v1/setups/active")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        found = any(s["symbol"] == "TCS" for s in data["setups"])
        assert found is True

        # Test setup by ID
        detail_resp = await client.get(f"/api/v1/setups/{setup.id}")
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        assert detail_data["symbol"] == "TCS"
        assert detail_data["entry_trigger_price"] == 3900.0
        assert detail_data["invalidation_level"] == 3860.0
        assert detail_data["status"] == "candidate"

        # Test setup 404
        not_found_resp = await client.get("/api/v1/setups/non-existent-id")
        assert not_found_resp.status_code == 404


@pytest.mark.asyncio
async def test_setups_failed_endpoint():
    store = get_setup_store()
    # Seed a rejected/failed setup
    failed_setup = IntradaySetupRecord(
        symbol="HDFCBANK",
        sector="BANKING",
        strategy_name="vwap_pullback_v1",
        regime=MarketRegime.RANGE_BOUND,
        entry_trigger_price=1650.0,
        invalidation_level=1640.0,
        target_price=1665.0,
        risk_reward_ratio=1.5,
        estimated_transaction_cost=20.0,
        rejection_reason="Breached stop-loss invalidation level",
        status=SetupStatus.INVALIDATED,
    )
    store.add_setup(failed_setup)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/setups/failed")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        found = any(s["symbol"] == "HDFCBANK" for s in data["setups"])
        assert found is True


@pytest.mark.asyncio
async def test_sector_performance_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/market/sectors")
        assert resp.status_code == 200
        data = resp.json()
        assert "sector_returns" in data
        assert "IT" in data["sector_returns"] or "BANKING" in data["sector_returns"]


@pytest.mark.asyncio
async def test_ledger_scorecard_endpoint():
    ledger = get_signal_ledger()
    ledger.append(
        symbol="INFY",
        strategy_name="orb_v1",
        regime="trending_bullish",
        entry_price=1850.0,
        invalidation_level=1830.0,
        target_price=1890.0,
        risk_reward_ratio=2.0,
        outcome=SignalOutcome.CLOSED_WIN,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/ledger/scorecard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["integrity_verified"] is True
        assert data["total_signals_recorded"] >= 1
        assert "wins" in data
        assert data["latest_block_hash"] is not None
