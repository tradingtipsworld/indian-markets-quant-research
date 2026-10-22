# Production Integration Roadmap (Prioritized P0 - P3)

**Platform:** `indian-markets-quant-research`  
**Last Updated:** 2026-10-22  

---

## P0: Critical Correctness, Security & Data Integrity (Completed ✅)
- [x] Zero hardcoded secrets; NaCl-encrypted GitHub Repository Secrets for all API keys.
- [x] Independent Risk Engine with absolute veto over AI and strategy signals.
- [x] Tamper-evident cryptographic SHA-256 signal audit ledger.
- [x] Input sanitization and prompt injection defense on news pipeline.
- [x] Anti-lookahead sequential simulation in backtesting.
- [x] Complete 40-test suite passing without failures.

---

## P1: Core Research, Market Scanner & Paper Trading (Completed ✅)
- [x] Indian market calendar & session state validation (IST 09:15 - 15:30).
- [x] Market regime detection engine (Bullish, Bearish, Range, High/Low Vol, Unknown).
- [x] Whole-market scanner for liquid NSE equity universe with "No-Trade" capability.
- [x] Intraday strategies: Opening Range Breakout (ORB) and VWAP Pullback.
- [x] Multi-provider AI auto-model selection and dynamic fallback (Groq, Gemini, Mistral, Nvidia, OpenRouter).
- [x] Realistic statutory Indian intraday equity transaction cost modeling (STT 0.025%, ₹20 brokerage cap, Stamp Duty, Turnover, GST).
- [x] Standardized mobile Telegram templates (Regime, Setup DNA, Activated, Invalidated, No-Trade, Scorecard).

---

## P2: Live Data Ingestion & Automated Scheduling
- [ ] Connect authorized live Indian market data feed:
  - Zerodha Kite Connect WebSocket / REST API, OR
  - Angel One SmartAPI, OR
  - DhanHQ API / TrueData commercial feed.
- [ ] Automated cron scheduling for intraday market scans:
  - 09:00 IST: Pre-open market scan and daily regime notice.
  - 09:30 IST: Opening Range Breakout (ORB 15m/30m) scan.
  - 11:30 & 14:00 IST: VWAP pullback and midday momentum scan.
  - 15:45 IST: End-of-Day transparent scorecard and performance ledger broadcast.

---

## P3: Cloud Infrastructure & Deployment
- [ ] Managed PostgreSQL database migration for multi-year historical setup tracking.
- [ ] Redis caching layer for live tick buffering and WebSocket deduplication.
- [ ] Dockerized deployment on Linux VPS / AWS EC2 with systemd process supervision.
