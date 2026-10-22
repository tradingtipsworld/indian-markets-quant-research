# Security Model & Threat Mitigation

**Platform:** `indian-markets-quant-research`  
**Standard:** Institutional Security & Risk Governance  
**Last Updated:** 2026-10-22  

---

## 1. Secrets Management and Storage
- **Zero Raw Secrets in Source Control:** `.env` is explicitly declared in `.gitignore` and verified via `git check-ignore`.
- **GitHub Repository Actions Secrets:** All production API keys (`GROQ_API_KEY`, `OPENROUTER_API_KEY`, `MISTRAL_API_KEY`, `NVIDIA_API_KEY`, `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`) are encrypted using libsodium (`PyNaCl`) public-key cryptography and stored in GitHub Repository Actions Secrets.
- **Log Redaction:** `structlog` logging filters automatically redact sensitive tokens, passwords, and API keys.

---

## 2. Untrusted Content & Prompt Injection Defenses
- External financial news articles and social feeds are treated as **untrusted user input**.
- The `NewsPipeline` (`app/data/news.py`) scans for and strips adversarial prompt injection patterns (e.g. `"Ignore previous instructions"`, `"Bypass risk limits"`, `"Execute real order"`).
- System prompts enforce strict role boundaries, preventing external article text from altering risk thresholds, stop-loss rules, or strategy parameters.

---

## 3. Cryptographic Audit Ledger & Tamper Resistance
- Every trading setup, candidate DNA, AI council consensus, risk evaluation, and Telegram message ID is appended to the `TamperEvidentSignalLedger` (`app/audit/ledger.py`).
- Each entry is linked to the prior entry via a cryptographic SHA-256 block hash.
- The `verify_integrity()` routine mathematically validates that past alerts have not been altered or deleted retrospectively.

---

## 4. Execution Boundary & Live Trading Safeguards
- **No Live Order Capability:** The codebase strictly implements `PaperBroker` in `app/portfolio/manager.py`. No live broker API endpoints or order dispatch routes exist in the active platform.
- **Independent Risk Veto:** The `RiskEngine` operates as an independent gatekeeper with hardwired mathematical limits (position size <= 10%, exposure <= 80%, drawdown <= 20%). AI agents cannot bypass or weaken risk parameters.
- **Hardware/Global Kill Switch:** The `risk_kill_switch` setting instantly freezes all strategy evaluations and paper orders across the platform.
