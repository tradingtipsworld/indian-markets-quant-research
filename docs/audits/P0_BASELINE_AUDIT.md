# P0 BASELINE AUDIT — PRODUCTION CORRECTNESS & FIRST FIX
**Project:** `indian-markets-quant-research`  
**Audit Date:** 2026-10-22  
**Target Phase:** P0 Production Correctness  
**Environment:** Windows 11, PowerShell, Python 3.14.7, pytest 9.1.1  

---

## 1. Existing Architecture & Execution Flow

### Data & Execution Pipeline
1. **Market Data Ingestion:**
   `app/data/providers/synthetic.py` (`generate_synthetic_ohlcv`) generates synthetic OHLCV data using a random-walk algorithm.
2. **API Request Initiation:**
   `POST /api/v1/agents/council/deliberate` in `app/api/routes/agents.py` accepts `DeliberationRequest` (symbol, history_days).
3. **Data Retrieval:**
   `app/api/routes/agents.py` calls `data_provider.get_ohlcv(...)` returning a pandas DataFrame.
4. **Council Orchestration:**
   `council.deliberate(symbol, df)` in `app/agents/orchestration.py` coordinates 8 research agents:
   - `MarketContextAgent`
   - `TechnicalResearchAgent`
   - `FundamentalResearchAgent`
   - `NewsSentimentAgent`
   - `BullishReviewerAgent`
   - `BearishReviewerAgent`
   - `IndependentRiskReviewerAgent`
   - `ResearchSynthesizerAgent` (with `AutoAIService` dynamic fallback)
5. **Report Generation & API Response:**
   Returns `CouncilSynthesis` and formatted Markdown to the client.

---

## 2. Baseline Test Suite Results

The existing test suite was executed prior to any modifications:

- **Command Executed:** `python -m pytest -v`
- **Result:** **50 passed in 7.28s** (0 failed, 0 errors, 0 skipped).
- **Test Modules Passing:**
  - `tests/test_agents.py` (1 test)
  - `tests/test_ai_service_and_telegram.py` (4 tests)
  - `tests/test_api.py` (4 tests)
  - `tests/test_audit_ledger.py` (3 tests)
  - `tests/test_backtest.py` (1 test)
  - `tests/test_config.py` (4 tests)
  - `tests/test_data_validation.py` (3 tests)
  - `tests/test_db_persistence.py` (2 tests)
  - `tests/test_indicators.py` (4 tests)
  - `tests/test_intelligence_api.py` (5 tests)
  - `tests/test_news_pipeline.py` (3 tests)
  - `tests/test_portfolio.py` (3 tests)
  - `tests/test_regime_and_scanner.py` (4 tests)
  - `tests/test_risk.py` (4 tests)
  - `tests/test_session_calendar.py` (2 tests)
  - `tests/test_walk_forward.py` (3 tests)

---

## 3. Confirmed Defects with File Paths & Line References

### Defect 1: Process-Randomized `hash()` in Synthetic Data Provider
- **File:** [`app/data/providers/synthetic.py`](file:///c:/Users/lenovo/Downloads/trading/app/data/providers/synthetic.py#L115-L117)
- **Line Reference:** Line 116:
  ```python
  symbol_seed = seed + hash(symbol) % 10000
  rng = np.random.default_rng(abs(symbol_seed))
  ```
- **Finding:** Python's built-in `hash()` is randomized on every Python process launch via SipHash/SipHash24 seeded by `PYTHONHASHSEED`. Calling `generate_synthetic_ohlcv("SYNTH_RELIANCE", ...)` in two separate processes produces differing numbers.
- **Risk:** Synthetic unit tests and deterministic simulation runs are not reproducible across test processes or CI runs.
- **Fix:** Replace `hash(symbol)` with deterministic cryptographic hashing (SHA-256) converted to an integer modulo $2^{32}$.

### Defect 2: Fabricated Balance Sheet & Fundamental Claims
- **File:** [`app/agents/orchestration.py`](file:///c:/Users/lenovo/Downloads/trading/app/agents/orchestration.py#L141-L156)
- **Line Reference:** Lines 145–152 (`FundamentalResearchAgent.analyze`):
  ```python
  summary=f"Balance sheet metrics for {symbol} indicate sustainable operational cash flow.",
  observations=[
      "Debt-to-equity ratio within sectoral safety bounds",
      "Operating margin expansion consistent over trailing quarters",
  ],
  supporting_evidence=["Sectoral peer comparison shows relative earnings resilience"],
  ```
- **Finding:** `FundamentalResearchAgent` completely hallucinates balance sheet stability, debt-to-equity safety, and margin expansion when no fundamental data was passed into `analyze()`.
- **Risk:** High-risk misleading information. Disseminating fabricated fundamental claims violates algorithmic transparency and financial audit standards.
- **Fix:** Check `context` for valid fundamental metrics. If missing or `None`, explicitly return `UNKNOWN`/`NOT_AVAILABLE`, neutral sentiment, zero confidence, and documented `missing_data_notes`.

### Defect 3: Fabricated News & Corporate Governance Claims
- **File:** [`app/agents/orchestration.py`](file:///c:/Users/lenovo/Downloads/trading/app/agents/orchestration.py#L169-L184)
- **Line Reference:** Lines 173–180 (`NewsSentimentAgent.analyze`):
  ```python
  summary=f"Recent public sentiment for {symbol} remains constructive without negative event catalysts.",
  observations=[
      "Zero corporate governance regulatory inquiries detected in audit period",
      "Institutional media mentions predominantly focus on operational capacity",
  ],
  supporting_evidence=["Neutral-to-positive press releases and filings"],
  ```
- **Finding:** `NewsSentimentAgent` asserts that zero corporate governance inquiries were detected and media mentions are positive when no verified news feed was supplied.
- **Risk:** False sense of security regarding regulatory exposure or litigation risk.
- **Fix:** Check `context` for verified news items (e.g. from `NewsPipeline`). If missing, declare `NOT_AVAILABLE`, neutral sentiment, zero confidence, and explicit `missing_data_notes`.

### Defect 4: Unhandled `IndexError` / `KeyError` on Empty or Invalid Data
- **File:** [`app/agents/orchestration.py`](file:///c:/Users/lenovo/Downloads/trading/app/agents/orchestration.py#L71-L74)
- **Line References:**
  - `MarketContextAgent.analyze`: Lines 71–74 (`close.iloc[-1]`)
  - `TechnicalResearchAgent.analyze`: Line 104 (`df["close"]`)
  - `BullishReviewerAgent.analyze`: Line 197 (`df["close"].iloc[-1]`)
  - `BearishReviewerAgent.analyze`: Line 228 (`df["close"].iloc[-1]`)
  - `AgentCouncilOrchestrator.deliberate`: Line 336 (`df["close"].iloc[-1]`)
- **Finding:** If an empty DataFrame (`len(df) == 0`) or DataFrame without a `"close"` column is passed, these methods raise unhandled `IndexError` or `KeyError` instead of returning a safe fallback.
- **Risk:** Server crashes (HTTP 500) on malformed or empty datasets.
- **Fix:** Add strict input validation at the agent and council boundaries. If `df` is empty, missing required columns, or invalid, return a safe `UNKNOWN` / `NO_TRADE` output with clear diagnostic notes.

### Defect 5: Uncalculated Claims in Bullish, Bearish, and Market Context Agents
- **File:** [`app/agents/orchestration.py`](file:///c:/Users/lenovo/Downloads/trading/app/agents/orchestration.py#L85-L86, #L207-L211, #L238-L242)
- **Finding:**
  - `MarketContextAgent` claims "Macro volatility remains within normal historical bounds" without calculating volatility.
  - `BullishReviewerAgent` claims "Higher lows established across trailing 20 sessions" and "Strong accumulation candles near recent swing low" without checking candle price action.
  - `BearishReviewerAgent` claims "Volume drying up on upward impulses" without calculating volume moving averages.
- **Fix:** Compute actual historical annualized volatility, 20-period price range, and volume ratios deterministically from `df`. Ground all observations strictly in calculated metrics.

### Defect 6: Hardcoded Bullish Bias in Council Synthesis Fallback
- **File:** [`app/agents/orchestration.py`](file:///c:/Users/lenovo/Downloads/trading/app/agents/orchestration.py#L347-L387)
- **Finding:** Even if market data is sharply declining or fundamental/news data is missing, the default synthesis text claims:
  `"The council notes positive structural momentum validated by sound balance sheet fundamentals."`
  and sets `consensus_sentiment=SentimentScore.MODERATELY_BULLISH` and `proposed_action="ACCUMULATE_ON_PULLBACK"`.
- **Fix:** Compute synthesized consensus deterministically based on participating agent sentiments and available evidence. If critical data is missing or data is bearish, default to `SentimentScore.NEUTRAL` or `SentimentScore.BEARISH`, action `"WAIT_FOR_DATA"` or `"REDUCE"`, with zero unverified claims.

---

## 4. Proposed Minimal Fix Plan (P0 Scope Only)
1. **`app/data/providers/synthetic.py`:** Replace `hash(symbol)` with deterministic SHA-256 integer seed.
2. **`app/agents/schemas.py`:** Ensure support for `UNKNOWN` / `NOT_AVAILABLE` states where appropriate.
3. **`app/agents/orchestration.py`:**
   - Add input validation helper `validate_market_dataframe(df)`.
   - Update `FundamentalResearchAgent` to inspect `context.get("fundamentals")`; if missing, return `UNKNOWN` / `NOT_AVAILABLE`.
   - Update `NewsSentimentAgent` to inspect `context.get("news")`; if missing, return `UNKNOWN` / `NOT_AVAILABLE`.
   - Update `MarketContextAgent`, `BullishReviewerAgent`, `BearishReviewerAgent` to compute real metrics (volatility, swing high/low, volume ratio) and handle empty/insufficient data safely.
   - Update `AgentCouncilOrchestrator.deliberate()` to handle empty data gracefully and synthesize consensus without fabricated claims.
4. **Tests:** Expand `tests/test_agents.py` and add `tests/test_synthetic_reproducibility.py` covering all 7 test cases specified in P0.
