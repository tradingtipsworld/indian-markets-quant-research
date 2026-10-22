# REFERENCE REPOSITORIES & RESEARCH CATALOG
**Target Platform:** AI Intraday Market Intelligence Platform (`indian-markets-quant-research`)  
**Auditor:** Quantitative Systems Engineering Team  
**Inspection Date:** 2026-10-22  

---

## 1. Multi-Agent AI Trading & Research

1. **TradingAgents**  
   - URL: https://github.com/TauricResearch/TradingAgents  
   - Default Branch: `main`  
   - Inspected Files: `tradingagents/agents/`, `tradingagents/graph/`  
   - Key Insight: Cyclical Bull/Bear debate loop with typed Pydantic outputs.

2. **AI Hedge Fund**  
   - URL: https://github.com/virattt/ai-hedge-fund  
   - Default Branch: `main`  
   - Inspected Files: `src/agents/`, `src/tools/`  
   - Key Insight: Independent Risk Manager persona holding absolute veto authority.

3. **FinRobot**  
   - URL: https://github.com/AI4Finance-Foundation/FinRobot  
   - Default Branch: `main`  
   - Inspected Files: `finrobot/agents/`, `finrobot/functional/`  
   - Key Insight: Hierarchical multi-agent report synthesis structure.

4. **QuantAgent**  
   - URL: https://github.com/fscheu/QuantAgent  
   - Default Branch: `main`  
   - Inspected Files: `quantagent/`  
   - Key Insight: Cautionary reference against unconstrained dynamic code execution.

5. **QuantSingularity — LLM-Powered Multi-Agent Frameworks for Algorithmic Trading**  
   - URL: https://github.com/QuantSingularity/LLM-Powered-Multi-Agent-Frameworks-for-Algorithmic-Trading  
   - Default Branch: `main`  
   - Inspected Files: Research notebooks and backtest scripts  
   - Key Insight: Temporal leak prevention across 5 research stages.

6. **AI-Trader**  
   - URL: https://github.com/HKUDS/AI-Trader  
   - Default Branch: `main`  
   - Inspected Files: `service/server/main.py`, `service/server/worker.py`  
   - Key Insight: Background polling worker decoupled from API request handlers.

7. **AI Trading Agents Stack**  
   - URL: https://github.com/anthonyjohn17/ai-trading-agents-stack  
   - Default Branch: `main`  
   - Inspected Files: Monorepo workspace config, strategy definitions  
   - Key Insight: Unified strategy interface across backtest, paper, and live modes.

8. **Algo Trading Agent**  
   - URL: https://github.com/kazelad/algo-trading-agent  
   - Status: **REJECTED (Security Flagged)**  
   - Threat intelligence note: Repository flagged for bot-inflated metrics. Strictly excluded.

---

## 2. Quantitative Research, Backtesting & Trading Engines

9. **FinRL-Trading**  
   - URL: https://github.com/AI4Finance-Foundation/FinRL-Trading  
   - Default Branch: `master`  
   - Inspected Files: `finrl/meta/env_stock_trading/`  
   - Key Insight: Rigorous out-of-sample reward and drawdown metrics.

10. **vectorbt**  
    - URL: https://github.com/polakowo/vectorbt  
    - Default Branch: `master`  
    - Inspected Files: `vectorbt/indicators/`, `vectorbt/portfolio/`  
    - Key Insight: High-performance vectorized indicator implementations in NumPy/Pandas.

11. **QuantConnect LEAN**  
    - URL: https://github.com/QuantConnect/Lean  
    - Default Branch: `master`  
    - Inspected Files: `Engine/DataFeeds/`, `Common/Securities/`  
    - Key Insight: Institutional point-in-time slice architecture with realistic fee models.

12. **Freqtrade**  
    - URL: https://github.com/freqtrade/freqtrade  
    - Default Branch: `develop`  
    - Inspected Files: `freqtrade/strategy/`, `freqtrade/optimize/lookahead_analysis.py`  
    - Key Insight: Formalized look-ahead detection methodology and protection handlers.

13. **Hummingbot**  
    - URL: https://github.com/hummingbot/hummingbot  
    - Default Branch: `master`  
    - Inspected Files: `hummingbot/connector/`, `hummingbot/strategy/`  
    - Key Insight: Decoupled paper broker state machine with explicit slippage simulation.

14. **OctoBot**  
    - URL: https://github.com/Drakkar-Software/OctoBot  
    - Default Branch: `master`  
    - Inspected Files: `tentacles/Evaluator/`  
    - Key Insight: Multi-evaluator sentiment and price convergence trees.

15. **QuantDinger**  
    - URL: https://github.com/OpenByteInc/QuantDinger  
    - Default Branch: `main`  
    - Inspected Files: `quantdinger/notifier/`  
    - Key Insight: Clean Telegram webhook/bot dispatching patterns with message queues.

---

## 3. Financial News, Data & Model Infrastructure

16. **FinGPT**  
    - URL: https://github.com/AI4Finance-Foundation/FinGPT  
    - Default Branch: `master`  
    - Inspected Files: `fingpt/FinGPT_Benchmark/`  
    - Key Insight: Separating raw corporate facts from sentiment polarity.

17. **OpenBB**  
    - URL: https://github.com/OpenBB-finance/OpenBB  
    - Default Branch: `main`  
    - Inspected Files: `openbb_platform/core/`  
    - Key Insight: Unified provider-agnostic data models and clean abstraction boundaries.

18. **yfinance**  
    - URL: https://github.com/ranaroussi/yfinance  
    - Default Branch: `main`  
    - Inspected Files: `yfinance/base.py`  
    - Key Insight: Historical data retrieval for Indian symbols (NSE `.NS`, BSE `.BO`).

---

## 4. Curated Discovery Collections

19. **Awesome Systematic Trading**  
    - URL: https://github.com/PyQuantSharp/awesome-systematic-trading  
    - Key Insight: Pure-Python calculation libraries avoiding Windows C++ build dependencies.

20. **Awesome Trading Agents**  
    - URL: https://github.com/LLMQuant/awesome-trading-agents  
    - Key Insight: Modern LLM council architectures, prompt structures, and evaluation standards.
