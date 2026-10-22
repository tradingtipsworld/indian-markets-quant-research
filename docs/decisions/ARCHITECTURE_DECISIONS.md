# Architecture Decision Records (ADR)

## ADR-001: Modular Monolith vs. Microservices
- **Decision:** Build as a strictly modular monolith within a single clean Python codebase.
- **Rationale:** Microservices introduce operational latency, network failures, complex RPC serialization, and multi-service deployment overhead unnecessary for Phase 1. Clean internal Python module boundaries (`app.risk`, `app.portfolio`, `app.quant`) allow future microservice extraction if needed.

## ADR-002: Provider-Neutral AI Layer with Mock Fallbacks
- **Decision:** Model the AI council using abstract interfaces with deterministic mock fallbacks.
- **Rationale:** The system must install, run, and test completely locally on Windows without requiring paid OpenAI, Anthropic, or Gemini API keys. Production LLM providers can be plugged in during Phase 5 by subclassing `BaseAgent`.

## ADR-003: Pure-Python Indicators vs TA-Lib C-Extensions
- **Decision:** Implement core indicators natively via vector operations (`pandas`, `numpy`).
- **Rationale:** TA-Lib requires compiling C-binaries on Windows which frequently breaks across developer setups and different Python minor versions. Pure vectorized calculations are deterministic, fast, and 100% portable.

## ADR-004: Dual-Database Strategy (SQLite Dev / PostgreSQL Production)
- **Decision:** Support SQLite with `aiosqlite` for local dev/testing and PostgreSQL with `asyncpg` for production via SQLAlchemy 2.0 ORM.
- **Rationale:** Eliminates prerequisites for local developers while ensuring production readiness.

## ADR-005: Sovereign Independent Risk Gatekeeper
- **Decision:** Position the `RiskEngine` as an autonomous, un-bypassable gatekeeper between strategy/agent signals and the `PortfolioManager`.
- **Rationale:** Financial safety requires that automated signals (especially LLM outputs) cannot unilaterally trigger order execution. Every proposed trade must pass 7 independent risk tests.
