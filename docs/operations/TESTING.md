# Testing Framework & Verification Guide

## 1. Overview
The platform enforces comprehensive testing covering unit logic, data validation, market regime classification, quantitative strategies, AI multi-agent orchestration, independent risk governance, statutory cost calculations, and Telegram notification formatting.

---

## 2. Running Tests (Windows PowerShell)

Run the full test suite:
```powershell
$env:PYTHONPATH="."
python -m pytest -v
```

Run specific test modules:
```powershell
# Market regime and whole-market scanner tests
python -m pytest tests/test_regime_and_scanner.py -v

# AI council and dynamic provider tests
python -m pytest tests/test_agents.py tests/test_ai_service_and_telegram.py -v

# News intelligence, deduplication, and sanitization tests
python -m pytest tests/test_news_pipeline.py -v

# Cryptographic audit ledger and tamper resistance tests
python -m pytest tests/test_audit_ledger.py -v

# Indian market calendar and session state tests
python -m pytest tests/test_session_calendar.py -v

# Independent risk engine and kill-switch tests
python -m pytest tests/test_risk.py -v

# Paper broker execution and Indian cost modeling tests
python -m pytest tests/test_portfolio.py -v

# Anti-lookahead backtesting tests
python -m pytest tests/test_backtest.py -v
```

---

## 3. Test Suite Breakdown (40 Tests Total — 100% Passing)

- `tests/test_agents.py`: AI Council deliberation and consensus formulation.
- `tests/test_ai_service_and_telegram.py`: Multi-provider auto-model selection and fallback.
- `tests/test_api.py`: FastAPI endpoints (health, config masking, backtest API).
- `tests/test_audit_ledger.py`: Append-only SHA-256 block chaining, tamper detection, and scorecarding.
- `tests/test_backtest.py`: Sequential anti-lookahead backtest execution.
- `tests/test_config.py`: Environment settings validation and secret masking.
- `tests/test_data_validation.py`: Data quality, gap detection, and monotonic order checks.
- `tests/test_indicators.py`: Pure-function indicators (SMA, RSI, MACD, Bollinger Bands, ATR, VWAP).
- `tests/test_news_pipeline.py`: Deduplication, NSE entity resolution, and prompt injection defense.
- `tests/test_portfolio.py`: Paper order execution, Indian fee caps, and cash accounting.
- `tests/test_regime_and_scanner.py`: Regime classification (Trend, Range, Vol, Unknown) and whole-market scanner.
- `tests/test_risk.py`: Independent risk gate, exposure thresholds, and emergency kill switch.
- `tests/test_session_calendar.py`: Indian trading calendar, weekend, holiday, and session state validation.
