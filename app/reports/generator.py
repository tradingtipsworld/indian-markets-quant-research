"""Research reports generation module — templates, markdown, and summaries."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.agents.schemas import CouncilSynthesis
from app.backtesting.engine import BacktestResult
from app.portfolio.manager import PortfolioManager


class MarketReport(BaseModel):
    """Structured educational research report."""

    title: str
    symbol: str
    report_type: str
    generated_at: datetime = Field(default_factory=datetime.now)
    markdown_content: str
    disclaimer: str = (
        "CONFIDENTIAL & EDUCATIONAL RESEARCH ONLY. NOT INVESTMENT ADVICE. "
        "Neither past performance nor AI-generated analyses guarantee future outcomes."
    )


class ReportGenerator:
    """Generates markdown and structured quantitative research reports."""

    @staticmethod
    def generate_strategy_report(result: BacktestResult) -> MarketReport:
        """Produce full backtesting performance report in markdown."""
        md = f"""# Quantitative Strategy Research Report: {result.strategy_name}

**Target Symbol:** {result.symbol}  
**Evaluation Period:** {result.start_date} to {result.end_date}  
**Total Bars Analyzed:** {result.total_bars}  

---

## 1. Executive Performance Summary

| Metric | Result |
| :--- | :--- |
| **Initial Capital** | ₹{result.initial_capital:,.2f} |
| **Final Equity** | ₹{result.final_equity:,.2f} |
| **Total Net Return** | **{result.total_return_pct:+.2f}%** |
| **Maximum Drawdown** | **{result.max_drawdown_pct:.2f}%** |
| **Sharpe Ratio (Annualized)** | {result.sharpe_ratio:.2f} |
| **Sortino Ratio** | {result.sortino_ratio:.2f} |
| **Profit Factor** | {result.profit_factor:.2f} |
| **Win Rate** | {result.win_rate_pct:.1f}% ({result.winning_trades}/{result.total_trades} trades) |
| **Total Simulated Fees** | ₹{result.total_fees:,.2f} |

---

## 2. Risk & Robustness Assessment

> [!NOTE]
> All trade fills include simulated slippage and realistic Indian exchange transaction costs (STT, Turnover, Stamp Duty).

- **Look-Ahead Bias Protection:** Strict point-in-time calculation enforced.
- **Drawdown Risk:** Strategy peaked with a maximum historical drawdown of {result.max_drawdown_pct:.2f}%.
"""
        return MarketReport(
            title=f"Backtest Report: {result.strategy_name} ({result.symbol})",
            symbol=result.symbol,
            report_type="strategy_backtest",
            markdown_content=md,
        )

    @staticmethod
    def generate_council_report(synthesis: CouncilSynthesis) -> MarketReport:
        """Produce AI Council Consensus research report."""
        md = f"""# AI Research Council Consensus: {synthesis.symbol}

**Timeframe:** {synthesis.timeframe}  
**Consensus Sentiment:** {synthesis.consensus_sentiment.value.upper()}  
**Council Confidence:** {synthesis.confidence * 100:.1f}%  
**Recommended Max Allocation:** {synthesis.recommended_position_sizing_pct}%  
**Invalidation Price Level:** ₹{synthesis.invalidation_level if synthesis.invalidation_level else 'N/A'}  

---

## Executive Summary
{synthesis.executive_summary}

---

## Council Deliberation Breakdown

### 🟢 Bullish Thesis
{synthesis.bull_case_summary}

### 🔴 Bearish Cross-Examination
{synthesis.bear_case_summary}

### 🛡️ Independent Risk Verdict
{synthesis.risk_evaluation}

---

## Proposed Action
`{synthesis.proposed_action}`
"""
        return MarketReport(
            title=f"AI Research Council Review: {synthesis.symbol}",
            symbol=synthesis.symbol,
            report_type="ai_council_synthesis",
            markdown_content=md,
        )
