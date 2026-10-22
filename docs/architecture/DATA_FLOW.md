# End-to-End Data Flow Specification

This document details the complete 12-stage data pipeline for the AI Intraday Market Intelligence Platform.

---

## The 12-Stage Pipeline

```
Raw Data Ingestion
       │
       ▼
[1] Session Calendar Gate (IST Check) ─── Closed / Holiday ───> Log & Sleep
       │ Active
       ▼
[2] Data Quality Validation (Gaps, Monotonicity, Outliers) ─── Invalid ───> Quarantine
       │ Valid
       ▼
[3] Market Regime Detection (Trend / Range / Vol / Unknown)
       │
       ▼
[4] Quantitative Scanner (Liquidity, Price & Spread Filters)
       │
       ├─ No Candidates Passed ───> [4a] "No-Trade Notice" ───> Telegram
       │
       ▼ Setups Found
[5] Setup DNA Formulation (Trigger, Invalidation, Target, Fees)
       │
       ▼
[6] News Intelligence Cross-Check (Dedup, Symbol Mapping, Fact Extraction)
       │
       ▼
[7] AI Research Council Deliberation (8 Roles, Bull/Bear Debate, LLM Synthesizer)
       │
       ▼
[8] Independent Risk Engine (Veto Gate — Position Size, Exposure, Kill-Switch)
       │
       ├─ Rejected ───> [8a] Audit Logged as REJECTED_RISK
       │
       ▼ Approved
[9] Cryptographic Append-Only Ledger Entry (SHA-256 Hash Chaining)
       │
       ├─────────────────────────────────┐
       ▼                                 ▼
[10] Telegram Alert Dispatch       [11] Paper Broker Execution
   (Setup DNA Template)               (Fills, Slippage, Statutory Taxes)
       │                                 │
       ▼                                 ▼
   Message ID Recorded               Portfolio Balance Updated
       │                                 │
       └─────────────────┬───────────────┘
                         ▼
[12] Outcome Tracking & Reconciler
   (Triggered / Invalidated / Expired / Win / Loss)
                         │
                         ▼
   Cryptographic Ledger Outcome Updated (Scorecard)
```

---

## Detailed Stage Descriptions

1. **Session Calendar Gate (`app/data/session.py`):**
   Validates timestamp against Indian Market Calendar (Asia/Kolkata timezone). Identifies whether current time corresponds to Pre-open (09:00 - 09:08), Regular Trading (09:15 - 15:30), or Closed/Holiday.

2. **Data Quality Validation (`app/data/validation.py`):**
   Verifies that OHLCV bars have strictly monotonic ascending timestamps, no missing columns, high >= low, valid volume, and flags any unexpected time gaps.

3. **Market Regime Detection (`app/quant/regime.py`):**
   Classifies market context into `TRENDING_BULLISH`, `TRENDING_BEARISH`, `RANGE_BOUND`, `HIGH_VOLATILITY`, `LOW_VOLATILITY`, or `UNKNOWN` using point-in-time moving average alignments and ATR volatility bands.

4. **Quantitative Whole-Market Scanner (`app/quant/scanner.py`):**
   Filters the defined NSE universe by daily turnover (>= 100k shares) and price range (₹50 - ₹15k). If no candidates pass, dispatches a **No-Trade Notice**.

5. **Setup DNA Formulation:**
   Constructs objective criteria: Entry Trigger Price, Hard Invalidation Level (Stop-loss), Target Projection, Risk/Reward Ratio (>= 1:1.5), and estimated Indian transaction costs.

6. **News Intelligence Cross-Check (`app/data/news.py`):**
   Retrieves permitted financial news, deduplicates via SHA-256 content hashes, resolves affected NSE companies, strips prompt injection attempts, and extracts factual statements.

7. **AI Council Deliberation (`app/agents/orchestration.py`):**
   Specialist agents (Market Context, Technical, Fundamental, News) analyze the data. Bull and Bear agents debate upside versus downside risks. The Synthesizer utilizes `AutoAIService` to summarize the consensus.

8. **Independent Risk Gate (`app/risk/engine.py`):**
   Evaluates proposed setup against strict statutory risk parameters. Holds absolute veto power independent of AI confidence.

9. **Cryptographic Ledger Chaining (`app/audit/ledger.py`):**
   Appends approved setup to the append-only ledger with SHA-256 hash chaining to the previous block hash.

10. **Telegram Delivery (`app/notifications/templates.py`):**
    Formats and broadcasts the Setup DNA alert to `@tradingtipsworld` with clear distinctions between facts, quantitative metrics, hypotheses, and disclaimers.

11. **Paper Broker Execution (`app/portfolio/manager.py`):**
    Simulates paper order execution with realistic slippage and statutory Indian intraday equity fees (STT 0.025%, ₹20 brokerage cap, Stamp Duty 0.003%, Turnover charges, GST).

12. **Outcome Reconciler:**
    Tracks subsequent price action to record verifiable outcomes: `TRIGGERED`, `INVALIDATED`, `EXPIRED`, `CLOSED_WIN`, `CLOSED_LOSS`, or `NO_TRADE`.
