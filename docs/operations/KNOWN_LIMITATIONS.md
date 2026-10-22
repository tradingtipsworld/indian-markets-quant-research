# Known Limitations & Validation Boundaries

**Platform:** `indian-markets-quant-research`  
**Last Updated:** 2026-10-22  

---

1. **Synthetic Market Data by Default:**
   - The default data provider generates deterministic synthetic random-walk price bars for development and testing.
   - **Never make real financial investment decisions based on synthetic data.**
   - Live licensed data feeds (e.g. TrueData, Zerodha Kite Connect, Angel One) belong to external integration and must be explicitly configured.

2. **No Real Money or Live Broker Connectivity:**
   - Orders are simulated purely in-memory via `PaperBroker`.
   - Real-money order execution is disabled and no live broker order placement code is active.
   - No capital is at risk.

3. **In-Memory Paper State Without Persistence Migrations:**
   - The paper trading singleton tracks portfolio state in memory across server runs. For persistent historical multi-day tracking, records are logged in SQLite via SQLAlchemy.

4. **Telegram Bot Channel Administrator Permissions:**
   - To deliver broadcast alerts to the public channel `@tradingtipsworld`, `@tradingtipsworld_bot` must be added as a Channel Administrator with the "Post Messages" permission.

5. **Regulatory Disclaimers:**
   - The platform is an educational quantitative research framework, NOT a SEBI-registered Investment Adviser (RIA) or Research Analyst (RA).
   - All published outputs must include statutory disclaimers.
