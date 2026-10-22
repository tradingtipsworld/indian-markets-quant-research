# Testing Framework & Verification Guide

## 1. Overview
The platform enforces comprehensive testing covering unit logic, data validation, market regime classification, quantitative strategies, AI multi-agent orchestration, independent risk governance, statutory cost calculations, cross-process data reproducibility, and Telegram notification formatting.

---

## 2. Running Tests (Windows PowerShell)

Run the full test suite:
```powershell
$env:PYTHONPATH="."
python -m pytest -v
```

Run specific test modules:
```powershell
# Synthetic data determinism & cross-process reproducibility
python -m pytest tests/test_synthetic_reproducibility.py -v

# AI council evidence grounding and failure handling tests
python -m pytest tests/test_agents.py -v

# Market regime and whole-market scanner tests
python -m pytest tests/test_regime_and_scanner.py -v

# Cryptographic audit ledger and tamper resistance tests
python -m pytest tests/test_audit_ledger.py -v

# Indian market calendar and session state tests
python -m pytest tests/test_session_calendar.py -v

# Independent risk engine and kill-switch tests
python -m pytest tests/test_risk.py -v

# Paper broker execution and Indian cost modeling tests
python -m pytest tests/test_portfolio.py -v

# Anti-lookahead backtesting and walk-forward tests
python -m pytest tests/test_backtest.py tests/test_walk_forward.py -v
```

---

## 3. Test Suite Breakdown (62 Tests Total — 100% Passing)

- `tests/test_agents.py` (8 tests): AI Council deliberation, empty market data safety, missing fields, invalid NaN handling, unavailable evidence handling, calculated indicators, and AI provider fallback.
- `tests/test_synthetic_reproducibility.py` (5 tests): In-process determinism, cross-process bit-for-bit reproducibility via subprocess, symbol independence, output schema, and provider interface conformance.
- `tests/test_ai_service_and_telegram.py` (4 tests): Multi-provider auto-model selection and fallback.
- `tests/test_api.py` (4 tests): FastAPI endpoints (health, config masking, backtest API).
- `tests/test_audit_ledger.py` (3 tests): Append-only SHA-256 block chaining, tamper detection, and scorecarding.
- `tests/test_backtest.py` (1 test): Sequential anti-lookahead backtest execution.
- `tests/test_config.py` (4 tests): Environment settings validation and secret masking.
- `tests/test_data_validation.py` (3 tests): Data quality, gap detection, and monotonic order checks.
- `tests/test_db_persistence.py` (2 tests): Database models and ledger block persistence across restarts.
- `tests/test_indicators.py` (4 tests): Pure-function indicators (SMA, RSI, MACD, Bollinger Bands).
- `tests/test_intelligence_api.py` (5 tests): Market pulse, active setups, failed setups, sectors, and scorecard endpoints.
- `tests/test_news_pipeline.py` (3 tests): Deduplication, NSE entity resolution, and prompt injection defense.
- `tests/test_portfolio.py` (3 tests): Paper order execution, Indian fee caps, and cash accounting.
- `tests/test_regime_and_scanner.py` (4 tests): Regime classification (Trend, Range, Vol, Unknown) and whole-market scanner.
- `tests/test_risk.py` (4 tests): Independent risk gate, exposure thresholds, and emergency kill switch.
- `tests/test_session_calendar.py` (2 tests): Indian trading calendar, weekend, holiday, and session state validation.
- `tests/test_walk_forward.py` (3 tests): Walk-forward evaluation, IS/OOS split, and robustness ratios.
