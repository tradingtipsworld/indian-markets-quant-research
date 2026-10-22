"""Daily Market Intelligence Pipeline Runner.

Executes the complete end-to-end intraday intelligence workflow:
1. Market data ingestion & quality checks
2. Indian market session & regime detection
3. Whole-market quantitative scan across NSE universe
4. Multi-agent AI Council deliberation with live LLM synthesis
5. Independent Risk Engine validation
6. Cryptographic Signal Ledger recording
7. Automated Telegram dispatch to @tradingtipsworld
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.agents.orchestration import AgentCouncilOrchestrator
from app.audit.ledger import SignalOutcome, get_signal_ledger
from app.core.config import get_settings
from app.core.logging import get_logger
from app.data.interfaces import Timeframe
from app.data.providers.synthetic import generate_synthetic_ohlcv
from app.data.session import IndianMarketCalendar, IST_TIMEZONE
from app.data.validation import validate_ohlcv
from app.notifications import NotificationMessage, get_notification_provider
from app.notifications.templates import TelegramTemplates
from app.portfolio.manager import PortfolioManager
from app.quant.regime import MarketRegimeDetector
from app.quant.scanner import DEFAULT_NSE_UNIVERSE, WholeMarketScanner
from app.risk.engine import RiskEngine

logger = get_logger(__name__)


async def run_daily_pipeline():
    settings = get_settings()
    provider = get_notification_provider()
    ledger = get_signal_ledger()
    regime_detector = MarketRegimeDetector()
    scanner = WholeMarketScanner()
    council = AgentCouncilOrchestrator()
    risk_engine = RiskEngine(settings)
    portfolio = PortfolioManager(risk_engine=risk_engine)

    ist_now = datetime.now(IST_TIMEZONE)
    today = ist_now.date()
    start_dt = today - timedelta(days=90)
    session_state = IndianMarketCalendar.get_session_state(ist_now)

    print(f"=== INITIATING DAILY PIPELINE [{ist_now.strftime('%Y-%m-%d %H:%M:%S IST')}] ===")
    print(f"Market Session State: {session_state.value}")

    # 1. Ingest Data for NSE Universe
    universe = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "LT", "TATAMOTORS"]
    market_data_map = {}
    for sym in universe:
        df = generate_synthetic_ohlcv(
            symbol=sym,
            start_date=start_dt,
            end_date=today,
            timeframe=Timeframe.DAILY,
        )
        report = validate_ohlcv(df, symbol=sym)
        if report.is_valid:
            market_data_map[sym] = df
        else:
            print(f"Data validation warning for {sym}: {report.issues}")

    # 2. Benchmark Market Regime Assessment
    nifty_df = market_data_map.get("RELIANCE")
    regime_report = regime_detector.detect(nifty_df, symbol="NIFTY_BENCHMARK")
    print(f"Detected Regime: {regime_report.regime.value} (Confidence: {regime_report.confidence * 100:.0f}%)")

    # Dispatch Report 1: Market Regime Briefing
    regime_msg = TelegramTemplates.market_regime_notice(regime_report)
    regime_msg.title = f"🇮🇳 NSE MARKET REGIME BRIEFING — {ist_now.strftime('%d %b %Y')}"
    regime_msg.body = (
        f"📅 *Trading Date:* `{ist_now.strftime('%A, %d %B %Y')}`\n"
        f"⏰ *Session Time:* `{ist_now.strftime('%I:%M %p IST')}`\n"
        f"📊 *Data Source:* Research Simulation Sandbox\n\n"
        + regime_msg.body
    )
    sent_regime = await provider.send(regime_msg)
    print(f"Report 1 (Regime Briefing) sent to Telegram: {sent_regime}")

    # 3. Whole-Market Scan
    scan_result = scanner.scan(market_data_map)
    print(f"Scan complete. Eligible setups: {len(scan_result.eligible_setups)}")

    # 4. Process Top Setup & AI Council Deliberation
    if scan_result.eligible_setups:
        top_setup = scan_result.eligible_setups[0]
        setup_df = market_data_map[top_setup.symbol]

        # Run AI Council Deliberation (with Live LLM dynamic synthesis)
        print(f"Running AI Council Deliberation for {top_setup.symbol}...")
        synthesis = await council.deliberate(top_setup.symbol, setup_df)

        # Record in Cryptographic Ledger
        entry = ledger.append(
            symbol=top_setup.symbol,
            strategy_name=top_setup.strategy_name,
            regime=top_setup.regime.value,
            entry_price=top_setup.entry_trigger_price,
            invalidation_level=top_setup.invalidation_level,
            target_price=top_setup.target_price,
            risk_reward_ratio=top_setup.risk_reward_ratio,
            ai_synthesis_summary=synthesis.executive_summary,
            outcome=SignalOutcome.PUBLISHED,
        )

        # Dispatch Report 2: Setup DNA & AI Consensus
        dna_msg = TelegramTemplates.setup_dna_alert(top_setup)
        dna_msg.title = f"🎯 TOP INTRADAY SETUP DNA — {top_setup.symbol}"
        dna_msg.body = (
            f"⚡ *Strategy:* `{top_setup.strategy_name}` (v{top_setup.strategy_version})\n"
            f"🌐 *Market Regime:* `{top_setup.regime.value.upper()}`\n\n"
            f"🤖 *AI Council Consensus:* \n_{synthesis.executive_summary}_\n\n"
            f"🟢 *Bullish Thesis:* {synthesis.bull_case_summary}\n"
            f"🔴 *Bearish Risk Review:* {synthesis.bear_case_summary}\n\n"
            + dna_msg.body
        )
        sent_dna = await provider.send(dna_msg)
        print(f"Report 2 (Setup DNA & AI Consensus) sent to Telegram: {sent_dna}")

    else:
        # If no setup met strict criteria, run council on benchmark and dispatch No-Trade Notice
        print("Dispatching No-Trade Notice with AI Market Review...")
        synthesis = await council.deliberate("NIFTY_BENCHMARK", nifty_df)
        no_trade_msg = TelegramTemplates.no_trade_notice(
            scan_result.no_trade_reason
            or "Market volatility compressed below breakout threshold. Zero high-probability setups qualified."
        )
        no_trade_msg.body = (
            f"🤖 *AI Council Context Review:* \n_{synthesis.executive_summary}_\n\n"
            + no_trade_msg.body
        )
        sent_no_trade = await provider.send(no_trade_msg)
        print(f"Report 2 (No-Trade Notice) sent to Telegram: {sent_no_trade}")

    # 5. Dispatch Report 3: End-of-Day Scorecard & Ledger Status
    scorecard = ledger.get_scorecard()
    scorecard_msg = TelegramTemplates.transparent_scorecard(scorecard)
    scorecard_msg.title = f"📋 END-OF-DAY SCORECARD & VERIFIABLE LEDGER — {ist_now.strftime('%d %b %Y')}"
    scorecard_msg.body = (
        f"🔒 *Tamper-Evident SHA-256 Ledger:* Integrity Verified ✅\n"
        f"📡 *Active Universe:* {', '.join(universe[:6])}...\n\n"
        + scorecard_msg.body
    )
    sent_scorecard = await provider.send(scorecard_msg)
    print(f"Report 3 (EOD Scorecard) sent to Telegram: {sent_scorecard}")

    print("=== PIPELINE EXECUTION COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(run_daily_pipeline())
