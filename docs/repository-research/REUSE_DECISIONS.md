# REUSE DECISIONS REGISTER
**Project:** AI Intraday Market Intelligence Platform (`indian-markets-quant-research`)  
**Auditor:** Quantitative Trading & Systems Engineering Team  
**Evaluation Standard:** Clean-Room Engineering, License Integrity, Indian Market Relevance  

---

## Decision Framework

For every feature or architecture candidate, one of five decisions is made:
1. **Reuse an existing working implementation**: Preserve and extend working code in our repository.
2. **Improve the existing implementation**: Refactor or enhance existing classes with tested features.
3. **Add a small independent module with a clear interface**: Create clean, single-purpose classes.
4. **Adapt a documented design pattern without copying code**: Re-implement pattern cleanly in Python with typing and tests.
5. **Reject it when it adds complexity or legal risk without measurable benefit**: Discard incompatible, bloated, or unsafe designs.

---

## Detailed Component Decisions

### 1. Market Data Layer
- **Candidate:** OpenBB provider extensions / yfinance scraper.
- **Decision:** **Improve Existing Implementation & Adapt Pattern**.
- **Rationale:** We retain our `MarketDataProvider` abstract base class and `SyntheticDataProvider`. We extend it with:
  1. Indian market session calendar (IST 09:15 to 15:30, pre-open 09:00 to 09:08).
  2. Data gap and stale bar detection.
  3. Provider-agnostic instrument universe loader for NSE equities.
- **Rejected:** Direct bundling of heavy OpenBB SDK (adds dozens of heavy dependencies and compilation overhead on Windows).

### 2. Multi-Agent AI Deliberation
- **Candidate:** LangGraph cyclic state machine (TradingAgents) vs AutoGen (FinRobot).
- **Decision:** **Improve Existing Implementation & Adapt Pattern**.
- **Rationale:** We retain our 8-member specialist council (`MarketContext`, `Technical`, `News`, `Bull`, `Bear`, `Risk`, `EvidenceValidator`, `Synthesizer`). We connect it to `AutoAIService` with Pydantic schema validation.
- **Rejected:** Heavy LangGraph / AutoGen dependencies. Our native async implementation avoids external framework lock-in, eliminates token overhead, and runs with sub-second latency.

### 3. Quantitative Scanning & Market Regimes
- **Candidate:** Vectorbt matrix scanning + Freqtrade strategy lifecycle.
- **Decision:** **Add Independent Modules with Clear Interfaces**.
- **Rationale:** Add:
  1. `MarketRegimeDetector` (`app/quant/regime.py`): Classifies market into `TRENDING_BULLISH`, `TRENDING_BEARISH`, `RANGE_BOUND`, `HIGH_VOLATILITY`, `LOW_VOLATILITY`, or `UNKNOWN`.
  2. `WholeMarketScanner` (`app/quant/scanner.py`): Scans NSE universe with liquidity, volume, and volatility filters.
  3. Intraday strategies: `OpeningRangeBreakoutStrategy`, `VWAPPullbackStrategy`, `MomentumBreakoutStrategy`.
- **Key Safety Guard:** The scanner can explicitly conclude **"No sufficiently strong setup today"**.

### 4. Risk Engine
- **Candidate:** Freqtrade protection handlers + Hummingbot risk controllers.
- **Decision:** **Improve Existing Implementation**.
- **Rationale:** Enhance `app/risk/engine.py` with setup candidate validation (independent of AI), checking risk/reward ratio (minimum 1:1.5), distance to invalidation, maximum intraday risk allocation, and circuit filter limits.
- **Rejected:** Letting AI agents override risk limits.

### 5. Indian Equity Cost Modeling & Backtesting
- **Candidate:** Generic backtesters with simple percentage fees.
- **Decision:** **Improve Existing Implementation**.
- **Rationale:** Implement exact statutory Indian intraday equity charges:
  - Brokerage: ₹20 / order or 0.03% (whichever is lower)
  - STT: 0.025% on sell side (intraday equity cash)
  - Exchange Turnover Fee: 0.00345% (NSE)
  - GST: 18% on (Brokerage + Turnover charges)
  - SEBI Charges: ₹10 per crore (0.0001%)
  - Stamp Duty: 0.003% on buy side
  - Explicit slippage model (default 0.05%)
- **Anti-Lookahead:** Sequential bar-by-bar execution, next-bar open fill simulation.

### 6. News Intelligence Pipeline
- **Candidate:** FinGPT news sentiment + FinRobot summarizer.
- **Decision:** **Add Small Independent Module (`app/data/news.py`)**.
- **Rationale:** Retrieves and deduplicates news, extracts source/URL/publication timestamp, maps affected NSE symbols, separates reported facts from sentiment interpretation, and includes untrusted prompt injection sanitization.

### 7. Telegram Product & Scorecard
- **Candidate:** QuantDinger Telegram alert engine.
- **Decision:** **Improve Existing Implementation (`app/notifications/`)**.
- **Rationale:** Build reusable message templates in `app/notifications/templates.py`:
  - Daily Market Regime & Context
  - Research Watchlist & Setup DNA
  - Setup Activated / Triggered
  - Setup Weakened / Invalidated / Expired
  - No-Trade Market Notice
  - End-of-Day Review & Transparent Scorecard
