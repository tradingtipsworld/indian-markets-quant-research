# Known Limitations & Validation Boundaries

1. **Synthetic Market Data Only:**
   - The current data provider generates deterministic synthetic random-walk price bars.
   - **Never make financial investment decisions based on synthetic data.**

2. **No Real Money or Live Broker Connectivity:**
   - Orders are simulated purely in-memory via `PaperBroker`.
   - No capital is at risk.

3. **In-Memory Portfolio State in Development Mode:**
   - The paper trading singleton holds state in memory across server runs unless persisted to database tables via migration scripts.

4. **Deterministic Mock AI Agents:**
   - The 8 AI Council member agents evaluate deterministic rule formulas rather than querying live LLM APIs.
   - This ensures offline reproducibility and zero API costs during framework development.

5. **Regulatory Disclaimers:**
   - The platform is an educational software development framework, NOT a SEBI-registered Investment Adviser (RIA) or Research Analyst (RA).
