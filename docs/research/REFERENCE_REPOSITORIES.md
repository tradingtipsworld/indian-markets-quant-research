# REFERENCE REPOSITORIES RESEARCH DOSSIER
**Project:** `indian-markets-quant-research`  
**Date:** 2026-10-22  
**Target Environment:** Python 3.11+, Windows 11 / Linux, FastAPI, Pydantic v2  

---

## 1. Executive Summary

This dossier documents the deep architectural analysis of seven benchmark quantitative trading, multi-agent AI, and financial data projects:

1. **`TauricResearch/TradingAgents`**
2. **`freqtrade/freqtrade`**
3. **`polakowo/vectorbt`**
4. **`virattt/ai-hedge-fund`**
5. **`OpenBB-finance/OpenBB`**
6. **`ranaroussi/yfinance`**
7. **`QuantConnect/Lean`**

Each project has been evaluated for architectural patterns, license restrictions, stack compatibility, test design, and explicit reuse vs. adapt vs. reject decisions.

---

## 2. In-Depth Project Analysis

### 1. TauricResearch / TradingAgents
* **Repository:** `https://github.com/TauricResearch/TradingAgents`
* **License:** MIT License (Permissive)
* **Core Purpose:** Multi-agent autonomous financial research framework coordinating specialized LLM personas for market analysis and investment deliberation.
* **Architecture:**
  - Employs a multi-analyst council: Fundamental Analyst, Technical Analyst, Sentiment Analyst, Bull Researcher, Bear Researcher, and Risk Arbitrator.
  - Utilizes LangGraph / LangChain graph topologies with stateful message passing and evidence grounding.
* **Reusable Concepts:**
  - **Adversarial Bull vs. Bear Debate:** Structured adversarial round-table where the Bull Analyst constructs the upside thesis, the Bear Analyst rigorously seeks disconfirming evidence, and the Synthesizer reconciles both against hard data.
  - **Structured Pydantic Evidence Output:** Passing typed dataclasses rather than unstructured raw prompt strings between agents.
* **Compatibility & Stack Fit:** High. Compatible with FastAPI and Pydantic v2.
* **Limitations & Rejection Notes:**
  - Original implementation relies heavily on continuous multi-turn LLM calls which creates high latency (>15-30s) and token cost.
  - Lacks deterministic risk boundaries (cannot enforce hard circuit limits or broker margin caps).
* **Adoption Decision:** **ADAPT** the adversarial debate protocol and synthesis schema; implement deterministic numeric preprocessing before invoking LLM synthesis.

---

### 2. freqtrade / freqtrade
* **Repository:** `https://github.com/freqtrade/freqtrade`
* **License:** GPLv3 (Copyleft)
* **Core Purpose:** Mature, high-performance modular algorithmic trading bot with backtesting, hyperopt, data downloading, and Telegram RPC control.
* **Architecture:**
  - Monolithic asynchronous Python engine with clear separation: `DataHandler` -> `PairListManager` -> `IStrategy` -> `Wallets` -> `RPC`.
  - Deterministic strategy lifecycle callbacks: `populate_indicators()`, `populate_entry_trend()`, `populate_exit_trend()`.
* **Reusable Concepts:**
  - **Deterministic Strategy Interface:** Strict separation between numerical indicator calculation and boolean entry/exit signals.
  - **Telegram RPC Architecture:** Command parsing, safe markdown formatting, markdown escaping, and chunking for mobile viewports.
  - **Dynamic Invalidation:** Trailing stop-loss and time-based setup expiration rules.
* **Compatibility & Stack Fit:** High architectural conceptual fit.
* **License Alert (CRITICAL):**
  - **GPLv3 copyleft:** Any direct inclusion or static linking of freqtrade code requires the entire derivative work to be distributed under GPLv3.
* **Adoption Decision:** **ADAPT ARCHITECTURE ONLY (Clean-room reimplementation)**. Recreate the strategy interface (`BaseStrategy`), trailing stop mechanisms, and Telegram formatting from first principles with zero copied source code.

---

### 3. polakowo / vectorbt
* **Repository:** `https://github.com/polakowo/vectorbt`
* **License:** Apache 2.0 (VectorBT core) / Commercial (VectorBT Pro)
* **Core Purpose:** High-performance vectorized backtesting engine leveraging NumPy and Numba broadcast operations.
* **Architecture:**
  - Arrays-first paradigm: Converts historical OHLCV data into 2D/3D NumPy arrays and evaluates signals simultaneously across assets and parameters without iterative Python for-loops.
* **Reusable Concepts:**
  - **Vectorized Signal Matrix Evaluation:** Evaluating multiple indicators across entire universes in a single broadcast step.
  - **Deterministic Metrics Computation:** Precise mathematical formulas for Sharpe, Sortino, Max Drawdown, Expectancy, and Win Rate.
* **Compatibility & Stack Fit:** Moderate. Requires Numba compilation which can introduce Windows C++ build dependencies.
* **Limitations & Rejection Notes:**
  - Vectorized backtests cannot easily simulate state-dependent path logic (such as order cancel-replace, dynamic slippage, partial fills, or live council deliberation).
* **Adoption Decision:** **ADAPT** the vectorized metrics and performance calculation formulas; retain event-driven bar-by-bar execution for intraday simulation.

---

### 4. virattt / ai-hedge-fund
* **Repository:** `https://github.com/virattt/ai-hedge-fund`
* **License:** MIT License (Permissive)
* **Core Purpose:** Proof-of-concept autonomous hedge fund using famous investor personas (Warren Buffett, Charlie Munger, Cathie Wood, Bill Ackman) orchestrated via LangGraph.
* **Architecture:**
  - Sequential LangGraph pipeline where individual persona agents evaluate fundamentals, valuation, and technicals to emit signals, aggregated by a Risk Manager.
* **Reusable Concepts:**
  - **Typed Agent Output Schemas:** Strict JSON response format with `signal` (bullish/bearish/neutral), `confidence` (0.0 to 1.0), and `reasoning`.
  - **Evidence Grounding:** Enforcing that every agent output cites the specific financial metric driving its conclusion.
* **Compatibility & Stack Fit:** High. Uses Python, Pydantic, and modern async patterns.
* **Limitations & Rejection Notes:**
  - Highly US-centric: Prompts and metrics assume SEC 10-K/10-Q filing conventions and US market hours.
  - Fictional investor personas can produce promotional or hand-waving rhetoric rather than quantitative rigor.
* **Adoption Decision:** **ADAPT** the structured signal output schema; replace persona roleplay with objective institutional roles (Market Context Analyst, Technical Research Analyst, News Intelligence Analyst, Independent Risk Reviewer).

---

### 5. OpenBB-finance / OpenBB
* **Repository:** `https://github.com/OpenBB-finance/OpenBB`
* **License:** AGPLv3 (Platform Core) / Commercial Dual License
* **Core Purpose:** Unified, modular financial data access platform aggregating multi-asset providers (Yahoo, Polygon, FMP, AlphaVantage, FRED, SEC).
* **Architecture:**
  - Provider Router Pattern: Clean separation between standard data models (`openbb-core`) and provider extensions (`openbb-yfinance`, `openbb-fmp`).
  - Standardized normalization: All providers map external responses into unified Pydantic schemas.
* **Reusable Concepts:**
  - **Provider-Neutral Market Data Contract:** Standardized interfaces for historical data, company news, and live quotes.
  - **Graceful Provider Fallback & Circuit Breaking:** Handling rate limits, API key exhaustion, and upstream downtime seamlessly.
* **License Alert (CRITICAL):**
  - **AGPLv3 copyleft:** Network-triggered copyleft applies if deployed as a network service.
* **Adoption Decision:** **ADAPT DESIGN PATTERN ONLY**. Implement a clean, independent `MarketDataProvider` abstract base class and `DataProvenance` schema without importing any `openbb` packages.

---

### 6. ranaroussi / yfinance
* **Repository:** `https://github.com/ranaroussi/yfinance`
* **License:** Apache 2.0 (Permissive)
* **Core Purpose:** Python library for downloading historical market data, fundamental info, and option chains from Yahoo Finance.
* **Architecture:**
  - HTTP client scraping Yahoo Finance endpoints with automatic crumb and session management, pandas DataFrame parsing, and multi-threading.
* **Reusable Concepts:**
  - **Indian NSE/BSE Ticker Formatting:** Mapping Indian equity symbols (e.g. `RELIANCE.NS`, `TCS.BO`).
  - **Multi-timeframe Historical Ingestion:** Standardizing daily and hourly OHLCV parsing.
* **Compatibility & Stack Fit:** High compatibility with pandas.
* **Data License & Reliability Alert:**
  - **Yahoo Finance ToS:** Prohibits commercial redistribution and real-time trading automation.
  - **Data Delay:** Intraday data is delayed by 15 minutes and subject to frequent schema breaks without SLA.
* **Adoption Decision:** **RESERVE FOR BENCHMARK / HISTORICAL VALIDATION ONLY**. Never label `yfinance` as a live or real-time intraday feed.

---

### 7. QuantConnect / Lean
* **Repository:** `https://github.com/QuantConnect/Lean`
* **License:** Apache 2.0 (Permissive)
* **Core Purpose:** Enterprise-grade multi-asset algorithmic trading engine running institutional backtests and live algorithmic broker execution.
* **Architecture:**
  - C# core with Python bindings. Modular execution pipeline: Data Feed -> Algorithm Manager -> Universe Selection -> Alpha Model -> Portfolio Construction -> Execution Model -> Risk Management Model.
* **Reusable Concepts:**
  - **Statutory Indian Transaction Cost Modeling:** Exact modeling of STT (Securities Transaction Tax), Exchange turnover charges, GST, SEBI turnover fees, and Stamp Duty.
  - **Brokerage Constraint Modeling:** Hard-coded brokerage caps (e.g. ₹20 per executed order standard in Indian discount brokers like Zerodha, Groww, AngelOne).
  - **Separation of Concerns:** Hard separation between signal generation (Alpha) and risk validation (RiskManagementModel).
* **Compatibility & Stack Fit:** Low runtime fit (C# engine requires mono/.NET runtime); extremely high theoretical and modeling fit.
* **Adoption Decision:** **ADAPT TRANSACTION COST & RISK MODELS** into pure Python classes (`TransactionCostModel`, `RiskEngine`).

---

## 3. Reference Synthesis Matrix

| Repository | License | Key Strengths | Critical Limitation | Our Architectural Action |
| :--- | :--- | :--- | :--- | :--- |
| **TradingAgents** | MIT | Adversarial Bull/Bear debate | High token latency; no deterministic risk | **ADAPT:** Structured debate & synthesis schema |
| **freqtrade** | GPLv3 | Robust strategy lifecycle & Telegram RPC | GPLv3 license copyleft | **ADAPT ARCHITECTURE:** Clean-room interface rewrite |
| **vectorbt** | Apache 2.0 | High-speed vectorized metrics | Cannot handle stateful path-dependent execution | **ADAPT:** Performance metrics formulas |
| **ai-hedge-fund** | MIT | Persona-grounded structured schemas | US-centric; persona roleplay hallucinations | **ADAPT:** Strict institutional schema validation |
| **OpenBB** | AGPLv3 | Unified provider abstraction router | AGPLv3 license copyleft | **ADAPT DESIGN:** Provider-neutral contract |
| **yfinance** | Apache 2.0 | Easy Indian equity historical lookup | Delayed 15m; ToS redistribution limits | **RESTRICT:** Offline historical research only |
| **QuantConnect/Lean** | Apache 2.0 | Institutional transaction cost & risk models | Heavy C# runtime | **ADAPT:** Indian statutory fee & risk engine |
