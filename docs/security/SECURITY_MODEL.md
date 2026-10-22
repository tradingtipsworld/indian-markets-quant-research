# Security & Threat Model

## 1. Threat Matrix

| Asset | Threat | Vector | Mitigation Implemented |
|---|---|---|---|
| **API Keys & Secrets** | Accidental credential leakage | Logs, Git commits, API error payloads | Pydantic secret isolation, Structlog automated key redaction (`_redact_secrets`), `.gitignore` shielding, safe summary endpoints |
| **Trading Capital** | Uncontrolled or rogue order submission | Prompt injection, strategy bugs, stale signals | Sovereign `RiskEngine` validation, Paper-Only enforcement in Phase 1, emergency `Kill Switch`, max position limits (10%) |
| **Market Data** | Erroneous or poisoned price feeds | Data provider corruption, NaN spikes | `validate_ohlcv()` checking for duplicates, negative prices, NaN values, high-low inversions |
| **Backtest Validity** | Curve-fitting & look-ahead bias | Indicator future data leakage | Sequential bar-by-bar progression, point-in-time calculation constraints |
| **Execution Safety** | Unauthorized live trading | Misconfiguration | `risk_paper_only=True` hard-coded default; cannot be disabled without broker configuration |

## 2. Safe Secret-Handling Rules

1. All secrets are loaded through environment variables or `.env`.
2. `.env` is permanently excluded in `.gitignore`.
3. The `/api/v1/config` endpoint invokes `get_safe_summary()` which scrubs all API keys and credentials.
4. Structlog processors scrub sensitive tokens from all console and JSON log records.
