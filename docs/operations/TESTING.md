# Verified Testing Report & Procedures

## 1. Automated Test Execution Commands

Run all tests via Windows PowerShell:

```powershell
$env:PYTHONPATH="."
python -m pytest tests -v
```

## 2. Verified Test Results (2026-10-21)

```text
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\lenovo\Downloads\trading
configfile: pyproject.toml
plugins: anyio-4.15.1, asyncio-1.4.0

tests/test_agents.py::test_council_deliberation PASSED                   [  4%]
tests/test_api.py::test_health_endpoint PASSED                           [  8%]
tests/test_api.py::test_config_endpoint_masks_secrets PASSED             [ 12%]
tests/test_api.py::test_instruments_list_endpoint PASSED                 [ 16%]
tests/test_api.py::test_backtest_api_execution PASSED                    [ 20%]
tests/test_backtest.py::test_backtest_execution_flow PASSED              [ 25%]
tests/test_config.py::test_default_development_config PASSED             [ 29%]
tests/test_config.py::test_safe_summary_does_not_leak_secrets PASSED     [ 33%]
tests/test_config.py::test_production_mode_requires_secret_key PASSED    [ 37%]
tests/test_config.py::test_invalid_log_level_rejected PASSED             [ 41%]
tests/test_data_validation.py::test_validate_ohlcv_detects_nan PASSED    [ 45%]
tests/test_data_validation.py::test_validate_ohlcv_detects_high_less_than_low PASSED [ 50%]
tests/test_data_validation.py::test_validate_clean_synthetic_data PASSED [ 54%]
tests/test_indicators.py::test_sma_calculation PASSED                    [ 58%]
tests/test_indicators.py::test_rsi_bounds PASSED                         [ 62%]
tests/test_indicators.py::test_macd_structure PASSED                     [ 66%]
tests/test_indicators.py::test_bollinger_bands_ordering PASSED           [ 70%]
tests/test_portfolio.py::test_paper_buy_order_execution PASSED           [ 75%]
tests/test_portfolio.py::test_paper_sell_order_execution PASSED          [ 79%]
tests/test_portfolio.py::test_cannot_sell_unowned_shares PASSED          [ 83%]
tests/test_risk.py::test_risk_approves_safe_order PASSED                 [ 87%]
tests/test_risk.py::test_risk_rejects_oversized_position PASSED          [ 91%]
tests/test_risk.py::test_risk_rejects_insufficient_cash PASSED           [ 95%]
tests/test_risk.py::test_kill_switch_blocks_all_actions PASSED           [100%]

============================= 24 passed in 1.77s ==============================
```

## 3. Test Coverage Highlights
- **Risk Verification:** Confirmed that oversized orders (>10%), orders exceeding cash, and all trading while kill switch is active are completely rejected.
- **Paper Trading:** Confirmed order fills debit cash and update position quantities with accurate Indian STT & turnover fees. Selling unowned assets is blocked.
- **Anti-Lookahead Engine:** Verified point-in-time calculation and equity curve tracking across sequential bars.
- **AI Council:** Verified 8-role council deliberation, consensus calculation, and 10% maximum allocation cap.
- **Security:** Verified that secrets are masked and omitted in `/api/v1/config`.
