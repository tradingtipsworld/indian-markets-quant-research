# Module Dependencies & Permitted Calls

## 1. Permitted Dependency Rules

To prevent circular imports and architectural decay, this platform strictly enforces a unidirectional dependency hierarchy:

```
[ app.api ]
    │
    ▼
[ app.agents ] ──► [ app.quant ] ──► [ app.data ] ──► [ app.core ]
    │                      │                 │               ▲
    ▼                      ▼                 ▼               │
[ app.reports ]       [ app.risk ]     [ app.db ] ───────────┘
                           │
                           ▼
                     [ app.portfolio ]
                           │
                           ▼
                      [ app.audit ]
```

## 2. Forbidden Boundary Crossings

1. ❌ **`app.quant` MUST NEVER import `app.portfolio` or `app.broker`**: Quantitative indicators and strategies produce signals only; they must never initiate executions or modify portfolio states.
2. ❌ **`app.agents` MUST NEVER call `app.portfolio.manager.submit_order()` directly**: AI outputs are strictly non-authoritative advisory research. They have zero direct execution authority.
3. ❌ **`app.risk` MUST NEVER depend on `app.api` or external providers**: Risk checks must be pure, testable, and locally verifiable with standard memory snapshots.
4. ❌ **`app.db` MUST NEVER contain trading logic**: Database models are persistence records, not execution rules.
