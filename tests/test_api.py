"""Integration tests for FastAPI endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_config_endpoint_masks_secrets():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "risk_paper_only" in data
        assert "secret_key" not in data


@pytest.mark.asyncio
async def test_instruments_list_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/data/instruments")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_synthetic"] is True
        assert data["count"] > 0


@pytest.mark.asyncio
async def test_backtest_api_execution():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "symbol": "SYNTH_RELIANCE",
            "fast_period": 5,
            "slow_period": 15,
            "days": 60,
            "initial_capital": 500000.0,
        }
        resp = await client.post("/api/v1/quant/backtest/run", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "result" in data
        assert "report_markdown" in data
