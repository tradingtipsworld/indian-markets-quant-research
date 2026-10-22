"""Telegram Message Templates for Indian Market Intelligence.

Formatted for readability on mobile Telegram clients with explicit distinction between:
- Verified market facts
- Quantitative observations
- AI interpretation
- Invalidation / Stop-Loss conditions
- Statutory regulatory disclaimers
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.audit.ledger import SignalOutcome
from app.notifications.interfaces import NotificationMessage
from app.quant.regime import RegimeAssessment
from app.quant.scanner import IntradaySetupRecord


class TelegramTemplates:
    """Standardized message template builder for Telegram broadcasts."""

    DISCLAIMER = (
        "⚠️ *Educational Research Only.* Not an investment advice. "
        "Strictly adhere to your predefined risk and stop-loss limits."
    )

    @classmethod
    def market_regime_notice(cls, assessment: RegimeAssessment) -> NotificationMessage:
        """Template 1: Daily Market Regime & Macro Context."""
        regime_title = assessment.regime.value.upper().replace("_", " ")
        icon = {
            "trending_bullish": "🟢",
            "trending_bearish": "🔴",
            "range_bound": "🔄",
            "high_volatility": "⚡",
            "low_volatility": "💤",
            "unknown": "❓",
        }.get(assessment.regime.value, "📊")

        body_lines = [
            f"{icon} *Current Regime:* `{regime_title}`",
            f"🎯 *Confidence:* `{assessment.confidence * 100:.0f}%`",
            "",
            "*Quantitative Evidence:*",
        ]
        for r in assessment.rationale:
            body_lines.append(f"• {r}")

        if assessment.features:
            body_lines.append("")
            body_lines.append("*Key Market Indicators:*")
            for k, v in assessment.features.items():
                body_lines.append(f"• `{k}`: {v}")

        body_lines.append("")
        body_lines.append(cls.DISCLAIMER)

        return NotificationMessage(
            title=f"MARKET REGIME BRIEFING: {assessment.symbol}",
            body="\n".join(body_lines),
            channel="market_briefing",
            level="info",
        )

    @classmethod
    def setup_dna_alert(cls, setup: IntradaySetupRecord) -> NotificationMessage:
        """Template 2: Research Watchlist Candidate with Complete Setup DNA."""
        body_lines = [
            f"🎯 *Instrument:* `NSE:{setup.symbol}`",
            f"📐 *Setup Type:* `{setup.strategy_name}` (v{setup.strategy_version})",
            f"🌐 *Market Regime:* `{setup.regime.value}`",
            "",
            "💵 *Execution Matrix:*",
            f"• *Entry Trigger:* ₹{setup.entry_trigger_price:.2f}",
            f"• *Invalidation (SL):* ₹{setup.invalidation_level:.2f}",
            f"• *Target Projection:* ₹{setup.target_price:.2f}",
            f"• *Risk / Reward:* `1:{setup.risk_reward_ratio:.2f}`",
            f"• *Est. Indian Fees:* ₹{setup.estimated_transaction_cost:.2f} (STT/Turnover/Stamp)",
            "",
            "🔍 *Supporting Evidence:*",
        ]
        for s in setup.supporting_evidence:
            body_lines.append(f"• {s}")

        if setup.contradicting_evidence:
            body_lines.append("")
            body_lines.append("⚠️ *Contradictory / Downside Risks:*")
            for c in setup.contradicting_evidence:
                body_lines.append(f"• {c}")

        body_lines.append("")
        body_lines.append(cls.DISCLAIMER)

        return NotificationMessage(
            title=f"INTRADAY SETUP CANDIDATE: {setup.symbol}",
            body="\n".join(body_lines),
            channel="setups",
            level="tip",
            metadata={"setup_id": setup.id, "symbol": setup.symbol},
        )

    @classmethod
    def setup_activated(cls, setup: IntradaySetupRecord, trigger_price: float) -> NotificationMessage:
        """Template 3: Setup Triggered by Live Price Action."""
        body_lines = [
            f"🚀 *Triggered:* `NSE:{setup.symbol}` has crossed ₹{trigger_price:.2f}!",
            f"Strategy: `{setup.strategy_name}`",
            "",
            f"• *Current Fill Target:* ₹{setup.target_price:.2f}",
            f"• *Hard Invalidation:* ₹{setup.invalidation_level:.2f}",
            "",
            "🛑 *Rule:* If price breaches invalidation level, exit without hesitation.",
            "",
            cls.DISCLAIMER,
        ]
        return NotificationMessage(
            title=f"SETUP ACTIVATED: {setup.symbol}",
            body="\n".join(body_lines),
            channel="execution",
            level="alert",
            metadata={"setup_id": setup.id},
        )

    @classmethod
    def setup_invalidated(cls, setup: IntradaySetupRecord, breach_price: float, reason: str = "") -> NotificationMessage:
        """Template 4: Setup Weakened or Invalidated (Failure Intelligence)."""
        body_lines = [
            f"🛑 *Thesis Broken:* `NSE:{setup.symbol}` has breached invalidation level at ₹{breach_price:.2f}.",
            f"Reason: {reason or 'Price crossed stop-loss boundary'}",
            "",
            "📉 *Failure Intelligence:*",
            "This setup is formally marked INVALIDATED. Do not average down or hold through stop loss.",
            "",
            cls.DISCLAIMER,
        ]
        return NotificationMessage(
            title=f"SETUP INVALIDATED: {setup.symbol}",
            body="\n".join(body_lines),
            channel="risk",
            level="warning",
            metadata={"setup_id": setup.id},
        )

    @classmethod
    def no_trade_notice(cls, reason: str) -> NotificationMessage:
        """Template 5: No-Trade Intelligence Notice."""
        body_lines = [
            "🛡️ *Patience is a Position.*",
            "",
            f"*Reason:* {reason}",
            "",
            "• Preserving capital during choppy or low-probability regimes is essential.",
            "• The system will continue scanning and notify only when verifiable setups align.",
            "",
            cls.DISCLAIMER,
        ]
        return NotificationMessage(
            title="NO-TRADE NOTICE: Market Quality Filter Active",
            body="\n".join(body_lines),
            channel="market_briefing",
            level="info",
        )

    @classmethod
    def transparent_scorecard(cls, scorecard: dict[str, Any]) -> NotificationMessage:
        """Template 6: Transparent Performance & AI Scorecard."""
        body_lines = [
            "📋 *Verified Intraday Signal Ledger Summary:*",
            "",
            f"• *Total Setups Recorded:* `{scorecard.get('total_signals_recorded', 0)}`",
            f"• *Completed Trades:* `{scorecard.get('completed_trades', 0)}`",
            f"• *Winning Trades:* `{scorecard.get('wins', 0)}`",
            f"• *Losing Trades:* `{scorecard.get('losses', 0)}`",
            f"• *Invalidated Setups:* `{scorecard.get('invalidated_setups', 0)}`",
            f"• *Win Rate:* `{scorecard.get('win_rate_pct', 0.0)}%`",
            "",
            "All outcomes are cryptographically recorded in the append-only ledger.",
            "No historical signals were cherry-picked or retrospectively edited.",
            "",
            cls.DISCLAIMER,
        ]
        return NotificationMessage(
            title="END-OF-DAY SCORECARD & PERFORMANCE LEDGER",
            body="\n".join(body_lines),
            channel="scorecard",
            level="info",
        )
