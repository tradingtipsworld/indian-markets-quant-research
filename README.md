# AI Quant Trading Platform — Framework First

> **A modular, testable, secure-by-design quantitative trading research and paper-trading platform engineered for Indian Financial Markets (NSE/BSE).**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Tests Passing](https://img.shields.io/badge/tests-24%20passed-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ⚠️ Important Regulatory & Financial Disclaimers

> [!CAUTION]
> **RESEARCH & EDUCATIONAL FRAMEWORK ONLY — NOT INVESTMENT ADVICE**  
> 1. This platform does **NOT** place live orders, execute real-money trades, or connect to live broker accounts in its default configuration.
> 2. All initial market data is **SYNTHETIC** and labeled as such. Never use synthetic fixtures to make real trading or investment decisions.
> 3. No quantitative strategy or AI model prediction guarantees positive returns. Systematic trading carries substantial risk of capital loss.
> 4. For future Indian market operation, appropriate regulatory review and compliance (SEBI regulations for Research Analysts, Investment Advisers, or algorithmic execution) must be conducted.

---

## 🚀 Key Architectural Highlights

- **Sovereign Risk Engine:** Independent risk gatekeeper enforcing position limits (<=10%), concentration rules, drawdown caps (<=20%), available cash checks, and emergency **Kill Switch** controls.
- **AI Research Council:** Multi-agent collaborative council with 8 discrete roles (Market Context, Technical, Fundamental, News/Sentiment, Bullish Reviewer, Bearish Reviewer, Risk Reviewer, Synthesizer) producing structured Pydantic consensus reports.
- **Anti-Lookahead Backtesting:** Sequential bar-by-bar progression eliminating temporal leakage, with realistic slippage and Indian exchange tax modeling (STT, Turnover, Stamp Duty).
- **Zero Paid Dependencies for Dev:** Operates 100% locally out-of-the-box using Python 3.11+ and SQLite. No paid API keys or external services required.

---

## 🛠️ Quick Start on Windows PowerShell

### 1. Installation

```powershell
# Navigate to the project root
cd c:\Users\lenovo\Downloads\trading

# (Optional) Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install fastapi uvicorn pydantic-settings sqlalchemy aiosqlite greenlet numpy pandas structlog httpx pytest-asyncio

# Copy environment configuration
Copy-Item .env.example .env
```

### 2. Run Test Suite

```powershell
$env:PYTHONPATH="."
python -m pytest tests -v
```

Expected output: `24 passed in ~1.8s`.

### 3. Launch API Server

```powershell
$env:PYTHONPATH="."
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Interactive API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check:** [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)
- **Readiness Check:** [http://127.0.0.1:8000/api/v1/ready](http://127.0.0.1:8000/api/v1/ready)

---

## 📁 Repository Layout

```text
ai-quant-platform/
├── app/
│   ├── main.py                     # FastAPI application factory & routes wiring
│   ├── core/                       # App settings, structlog, platform exceptions
│   ├── api/                        # REST routes (system, data, quant, portfolio, agents, audit)
│   ├── data/                       # Market data interfaces, validation, synthetic fixtures
│   ├── quant/                      # Indicators (SMA, EMA, RSI, MACD, BB, ATR, VWAP) & strategies
│   ├── backtesting/                # Sequential anti-lookahead backtest engine & metrics
│   ├── agents/                     # 8-member AI research council & debate orchestration
│   ├── risk/                       # Autonomous risk engine, limits, and kill switch
│   ├── portfolio/                  # Paper broker, transaction costs (STT), portfolio manager
│   ├── reports/                    # Strategy & council research report generator
│   ├── notifications/              # Notification interfaces & mock provider
│   ├── audit/                      # Structured security & trade execution audit logger
│   └── db/                         # SQLAlchemy 2.0 async engine, models, session factory
├── tests/                          # 24 unit & integration tests covering all modules
├── docs/                           # Architecture, security, operational & research documentation
├── .env.example                    # Template environment variables
├── pyproject.toml                  # Project manifest & tool configurations
├── Dockerfile                      # Production container recipe
├── compose.yaml                    # Multi-container orchestration (App + Postgres)
└── README.md                       # Main project documentation
```

---

## 📚 Complete Documentation Suite

- [Repository Research & 10-Repo Matrix](docs/repository-research/REPOSITORY_COMPARISON.md)
- [System Architecture](docs/architecture/SYSTEM_ARCHITECTURE.md)
- [Data Flow & Anti-Lookahead Model](docs/architecture/DATA_FLOW.md)
- [Module Dependencies](docs/architecture/MODULE_DEPENDENCIES.md)
- [Architecture Decision Records (ADR)](docs/decisions/ARCHITECTURE_DECISIONS.md)
- [Security & Threat Model](docs/security/SECURITY_MODEL.md)
- [Windows Setup Guide](docs/operations/WINDOWS_SETUP.md)
- [Testing Verification Report](docs/operations/TESTING.md)
- [Future Integration Roadmap (Phase 5)](docs/operations/INTEGRATION_ROADMAP.md)
- [Known Limitations](docs/operations/KNOWN_LIMITATIONS.md)

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
