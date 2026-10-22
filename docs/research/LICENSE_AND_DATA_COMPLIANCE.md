# SOFTWARE LICENSES, DATA REDISTRIBUTION & REGULATORY COMPLIANCE
**Project:** `indian-markets-quant-research`  
**Date:** 2026-10-22  
**Target Environment:** Python 3.11+, Windows 11 / Linux, FastAPI, Pydantic v2  

---

## 1. Software Open-Source License Compliance

Our platform strictly adheres to modern open-source software intellectual property rules and copyleft isolation boundaries.

### Comparative License Analysis

| Repository | Declared License | Permissiveness | Copyleft Contagion Risk | Permitted Use in this Project |
| :--- | :--- | :--- | :--- | :--- |
| **TauricResearch / TradingAgents** | MIT | Permissive | **None** | Full reuse of ideas, schemas, and prompt structure with copyright attribution. |
| **virattt / ai-hedge-fund** | MIT | Permissive | **None** | Full reuse of concepts and prompt architectures with copyright attribution. |
| **polakowo / vectorbt** | Apache 2.0 | Permissive | **None** | Reusable algorithms and formulas; must maintain Apache notices. Note: VectorBT Pro is proprietary. |
| **ranaroussi / yfinance** | Apache 2.0 | Permissive | **None** | Software is Apache 2.0; underlying data has separate redistribution restrictions. |
| **QuantConnect / Lean** | Apache 2.0 | Permissive | **None** | Reusable transaction cost and fee calculation logic with Apache 2.0 attribution. |
| **freqtrade / freqtrade** | **GPLv3** | Strong Copyleft | **HIGH** | **DO NOT COPY CODE.** Direct inclusion or static linking causes entire repository to become GPLv3. **Clean-room architectural reimplementation only.** |
| **OpenBB-finance / OpenBB** | **AGPLv3** | Network Copyleft | **CRITICAL** | **DO NOT IMPORT / VENDOR.** Triggered over network execution. **Clean-room provider router pattern only.** |

### Copyleft Quarantine Policy
1. **Clean-Room Implementation:** No source code, docstrings, or unit test fixtures from `freqtrade` (GPLv3) or `OpenBB` (AGPLv3) are copied into this repository. All strategy bases, data contracts, and Telegram formatters were engineered from scratch using standard Python 3.11+ and Pydantic v2.
2. **Third-Party Package Boundaries:** All external Python packages listed in `pyproject.toml` are licensed under MIT, BSD-3-Clause, or Apache 2.0.

---

## 2. Market Data Sourcing & Terms of Service Compliance

### A. Yahoo Finance (`yfinance`) Constraints
- **Commercial Redistribution Prohibition:** Yahoo Finance Terms of Service expressly forbid using its scraped data feeds for commercial resale, public data redistribution, or direct automated order execution.
- **Data Latency Notice:** Data feeds for Indian equities (`.NS`, `.BO`) provided via Yahoo Finance are subject to an exchange-mandated **15-minute delay** during live market hours.
- **Platform Policy:**
  - `yfinance` is restricted to historical backtesting and offline researcher calibration.
  - All public outputs (Telegram reports, API schemas) must explicitly declare the data mode:
    ```json
    {
      "data_mode": "delayed_or_synthetic",
      "exchange": "NSE",
      "staleness_warning": "15m delayed feed. Not authorized for live real-time execution."
    }
    ```

### B. Indian Exchange Regulations (NSE / BSE & SEBI)
- **Market Data Feeds:** Real-time Level-1 (L1) and Level-2 (L2) tick data from the National Stock Exchange of India (NSE) and Bombay Stock Exchange (BSE) requires an authorized data vendor agreement (e.g. via NSE Data & Analytics Ltd or authorized brokers such as Zerodha Kite Connect, AngelOne SmartAPI, Upstox, Dhan).
- **Redistribution Prohibitions:** Disseminating raw tick data or real-time order-book feeds over public channels (such as public Telegram groups or websites) without exchange vendor clearance is strictly prohibited by SEBI and exchange regulations.
- **Platform Policy:**
  - Real-time order execution is permanently disabled by default (`RISK_PAPER_ONLY=true`).
  - Telegram broadcasts must disseminate **research models, educational analyses, and quantitative observations**, never real-time unauthorized price-feed streaming.

---

## 3. SEBI Regulatory Framing & Mandatory Disclaimers

### A. SEBI (Research Analysts) Regulations, 2014 & Investment Advisers Regulations
Under Indian law, automated or manual recommendations to buy or sell securities delivered to the public can fall under SEBI (Research Analysts) Regulations or SEBI (Investment Advisers) Regulations.

### B. Platform Operational Safeguards
To comply with regulatory standards:
1. **Educational & Quantitative Research Stance:** All generated setups are labeled as **Hypothetical Algorithmic Scenarios** for research and paper-trading evaluation.
2. **No Guaranteed Return Claims:** The platform never uses promotional terminology ("sure-shot tips", "jackpot calls", "100% target hit").
3. **Transparent Failure Intelligence:** The platform explicitly broadcasts:
   - Breached invalidation levels (stop-loss hits).
   - "No-Trade" decisions when market regimes are unsupportive.
   - Comprehensive win-loss scorecards with verifiable cryptographic hashes.

### C. Standard Mandatory Telegram Notice
Every automated Telegram transmission must include the statutory regulatory disclosure:

> **⚠️ STATUTORY RESEARCH DISCLAIMER:**  
> This analysis is automatically generated by an experimental quantitative research algorithm for educational and paper-simulation purposes only. It does not constitute investment advice, financial advisory, or an invitation to buy/sell securities under SEBI regulations. Intraday equity trading involves substantial financial risk. Past simulated performance does not guarantee future results.
