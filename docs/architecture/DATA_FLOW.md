# Data Flow & Decision Process

## 1. End-to-End Decision Lifecycle

The architecture maintains strict boundaries across 5 sequential gates:

```mermaid
sequenceDiagram
    autonumber
    participant D as Market Data Provider
    participant Q as Quant Strategy / Indicator
    participant A as AI Research Council
    participant R as Independent Risk Engine
    participant P as Paper Portfolio & Broker
    participant L as Audit Log

    D->>Q: Historical OHLCV Series (Point-in-Time)
    Q->>Q: Calculate Indicators (SMA, RSI, etc.)
    Q->>R: Propose Trading Signal / Order
    
    rect rgb(240, 248, 255)
    Note over A: Educational & Qualitative Review
    D->>A: OHLCV + Market Context
    A->>A: Multi-Agent Council Deliberation (Bull vs Bear)
    A->>R: Research Recommendation (Non-Authoritative)
    end

    R->>R: Evaluate 7 Risk Guardrails
    alt Risk Check Fails OR Kill Switch Active
        R->>L: Record Rejection Audit Event
        R-->>Q: Reject Proposed Action
    else All Risk Checks Pass
        R->>P: Dispatch Approved Paper Order
        P->>P: Simulate Execution (Slippage + STT/Taxes)
        P->>P: Update Cash & Position Ledger
        P->>L: Record Trade Audit Log
    end
```

## 2. Temporal Isolation (Anti-Lookahead Policy)

1. **Step-by-Step Backtest Progression:**
   The backtest loop iterates chronologically over bar index $i \in [0, N-1]$. Indicator calculations and decisions at bar $i$ can only access data from $[0, i]$.
2. **Execution Timing:**
   Signals triggered at the close of bar $i$ are filled at either:
   - Bar $i$ close + simulated slippage buffer, or
   - Bar $i+1$ open price.
3. **No In-Sample Contamination:**
   Research council and strategy parameter tuning are separated into walk-forward validation windows.
