# Module Dependencies and Layering Rules

```mermaid
graph TD
    API["API Layer (app/api)"] --> AGENTS["AI Agents (app/agents)"]
    API --> QUANT["Quant Engine (app/quant)"]
    API --> RISK["Risk Engine (app/risk)"]
    API --> PORT["Portfolio & Paper Broker (app/portfolio)"]
    API --> AUDIT["Audit & Ledger (app/audit)"]

    AGENTS --> QUANT
    AGENTS --> CORE["Core Config & Logging (app/core)"]

    QUANT --> DATA["Market & News Data (app/data)"]
    QUANT --> PORT
    QUANT --> CORE

    RISK --> CORE
    PORT --> RISK
    PORT --> CORE

    AUDIT --> CORE
    DATA --> CORE
    NOTIF["Notifications (app/notifications)"] --> AUDIT
    NOTIF --> QUANT
    NOTIF --> CORE
```

---

## Architectural Rules

1. **Strict Dependency Unidirectionality:**
   Lower layers (`app/core`, `app/data`) must NEVER import from higher layers (`app/agents`, `app/api`).
2. **Independent Risk Isolation:**
   `app/risk` does not import from `app/agents`. AI agents cannot influence risk engine rules or thresholds.
3. **Paper Trading Isolation:**
   `app/portfolio` contains only simulated paper execution. It does not import or contain any live order execution broker adapters.
4. **Data Neutrality:**
   `app/data` implementations provide standardized `pd.DataFrame` and `Instrument` objects regardless of whether data originates from synthetic generators, historical CSVs, or future live broker websockets.
