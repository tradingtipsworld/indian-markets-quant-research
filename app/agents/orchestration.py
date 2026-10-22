"""AI Research Council member agents and multi-agent debate orchestrator.

Coordinates 8 specialized council members:
1. Market Context Analyst
2. Technical Research Analyst
3. Fundamental Research Analyst
4. News & Sentiment Analyst
5. Bullish Reviewer
6. Bearish Reviewer
7. Independent Risk Reviewer
8. Research Synthesizer

Uses provider-neutral abstraction with deterministic mock providers
so the framework runs locally without paid API credentials.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import pandas as pd

from app.agents.schemas import (
    AgentAnalysisOutput,
    AgentRole,
    CouncilSynthesis,
    SentimentScore,
)
from app.core.logging import get_logger
from app.quant.indicators.core import rsi, sma

logger = get_logger(__name__)


class BaseAgent(ABC):
    """Abstract interface for all AI research agents."""

    @property
    @abstractmethod
    def role(self) -> AgentRole:
        ...

    @abstractmethod
    async def analyze(
        self,
        symbol: str,
        df: pd.DataFrame,
        context: dict[str, Any] | None = None,
    ) -> AgentAnalysisOutput:
        ...


class MarketContextAgent(BaseAgent):
    """Evaluates macro regime, benchmark trends, and volatility environment."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.MARKET_CONTEXT

    async def analyze(
        self, symbol: str, df: pd.DataFrame, context: dict[str, Any] | None = None
    ) -> AgentAnalysisOutput:
        close = df["close"]
        sma50 = sma(close, min(50, len(df))).iloc[-1]
        curr_price = close.iloc[-1]
        regime = "bullish" if curr_price > sma50 else "bearish"

        return AgentAnalysisOutput(
            agent_role=self.role,
            symbol=symbol,
            timeframe="1d",
            summary=f"Broad market regime for {symbol} is currently {regime}.",
            sentiment=SentimentScore.BULLISH if regime == "bullish" else SentimentScore.BEARISH,
            confidence=0.75,
            observations=[
                f"Current price is {curr_price:.2f} vs 50-period SMA {sma50:.2f}",
                "Macro volatility remains within normal historical bounds",
            ],
            supporting_evidence=[f"50-SMA trend direction: {regime}"],
            assumptions=["Historical price distribution remains stationary over near term"],
            risks_identified=["Sudden monetary policy or rate shifts"],
            invalidating_conditions=[f"Price crossing back below 50-SMA ({sma50:.2f})"],
        )


class TechnicalResearchAgent(BaseAgent):
    """Evaluates technical indicators, support/resistance, and momentum."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.TECHNICAL_RESEARCH

    async def analyze(
        self, symbol: str, df: pd.DataFrame, context: dict[str, Any] | None = None
    ) -> AgentAnalysisOutput:
        close = df["close"]
        rsi_val = float(rsi(close, 14).iloc[-1])
        sentiment = SentimentScore.NEUTRAL
        if rsi_val > 65:
            sentiment = SentimentScore.BULLISH
        elif rsi_val < 35:
            sentiment = SentimentScore.BEARISH

        return AgentAnalysisOutput(
            agent_role=self.role,
            symbol=symbol,
            timeframe="1d",
            summary=f"Technical momentum analysis for {symbol}: 14-day RSI is at {rsi_val:.1f}.",
            sentiment=sentiment,
            confidence=0.80,
            observations=[
                f"14-RSI index value: {rsi_val:.1f}",
                "Price structure forms series of higher swing highs on daily timeframe",
            ],
            supporting_evidence=[f"RSI reading: {rsi_val:.1f}"],
            assumptions=["Standard 14-period lookback remains representative"],
            risks_identified=["Potential momentum exhaustion near historical supply zones"],
            invalidating_conditions=["RSI breakdown below 40 support pivot"],
        )


class FundamentalResearchAgent(BaseAgent):
    """Evaluates valuation metrics, earnings stability, and capital structure."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.FUNDAMENTAL_RESEARCH

    async def analyze(
        self, symbol: str, df: pd.DataFrame, context: dict[str, Any] | None = None
    ) -> AgentAnalysisOutput:
        return AgentAnalysisOutput(
            agent_role=self.role,
            symbol=symbol,
            timeframe="1d",
            summary=f"Fundamental profile for {symbol} displays resilient balance sheet quality.",
            sentiment=SentimentScore.MODERATELY_BULLISH,
            confidence=0.70,
            observations=[
                "Consistent quarterly revenue expansion across past 4 quarters",
                "Operating cash flow comfortably covers capital expenditures",
            ],
            supporting_evidence=["Debt-to-equity ratio remains well below sector medians"],
            assumptions=["Operating margins sustained through subsequent fiscal year"],
            risks_identified=["Input cost inflation compression on EBITDA"],
            invalidating_conditions=["Margin decline exceeding 200 basis points in subsequent earnings"],
        )


class NewsSentimentAgent(BaseAgent):
    """Evaluates corporate disclosures, press releases, and news flow."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.NEWS_SENTIMENT

    async def analyze(
        self, symbol: str, df: pd.DataFrame, context: dict[str, Any] | None = None
    ) -> AgentAnalysisOutput:
        return AgentAnalysisOutput(
            agent_role=self.role,
            symbol=symbol,
            timeframe="1d",
            summary=f"Recent press announcements and sector media coverage remain balanced for {symbol}.",
            sentiment=SentimentScore.NEUTRAL,
            confidence=0.65,
            observations=["No immediate negative regulatory actions reported"],
            supporting_evidence=["Public regulatory filings show normal-course compliance"],
            assumptions=["News flow accurately reflects operational conditions without media bias"],
            risks_identified=["Unannounced policy changes or regulatory scrutiny"],
            invalidating_conditions=["Material adverse event disclosure"],
        )


class BullishReviewerAgent(BaseAgent):
    """Constructs the strongest evidence-backed bull case."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.BULLISH_REVIEWER

    async def analyze(
        self, symbol: str, df: pd.DataFrame, context: dict[str, Any] | None = None
    ) -> AgentAnalysisOutput:
        curr_price = float(df["close"].iloc[-1])
        return AgentAnalysisOutput(
            agent_role=self.role,
            symbol=symbol,
            timeframe="1d",
            summary=f"Bull case: Strong demand absorption with favorable risk-reward expansion.",
            sentiment=SentimentScore.BULLISH,
            confidence=0.75,
            observations=[
                f"Support holding firmly near {(curr_price * 0.95):.2f}",
                "Volume expanding during upward moves",
            ],
            supporting_evidence=["Accumulation signature visible in volume profile"],
            assumptions=["Sector rotation tailwinds continue"],
            risks_identified=["Failure to clear overhead resistance"],
            invalidating_conditions=[f"Closing break below {(curr_price * 0.93):.2f}"],
        )


class BearishReviewerAgent(BaseAgent):
    """Constructs the rigorous counter-thesis, downside risks, and failure modes."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.BEARISH_REVIEWER

    async def analyze(
        self, symbol: str, df: pd.DataFrame, context: dict[str, Any] | None = None
    ) -> AgentAnalysisOutput:
        curr_price = float(df["close"].iloc[-1])
        return AgentAnalysisOutput(
            agent_role=self.role,
            symbol=symbol,
            timeframe="1d",
            summary=f"Bear case: Multiple overhead supply levels with risk of bull-trap exhaustion.",
            sentiment=SentimentScore.MODERATELY_BEARISH,
            confidence=0.70,
            observations=[
                f"Stiff overhead resistance identified at {(curr_price * 1.05):.2f}",
                "Risk of broader market correction cascading into high-beta equities",
            ],
            supporting_evidence=["Deceleration in rate-of-change across recent bars"],
            assumptions=["General market beta will dominate idiosyncratic factors on drawdowns"],
            risks_identified=["Break of trailing stop loss causing rapid liquidation"],
            invalidating_conditions=[f"Volume breakout sustaining above {(curr_price * 1.08):.2f}"],
        )


class IndependentRiskReviewerAgent(BaseAgent):
    """Stress-tests both bull and bear arguments from a pure risk & capital preservation perspective."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.RISK_REVIEWER

    async def analyze(
        self, symbol: str, df: pd.DataFrame, context: dict[str, Any] | None = None
    ) -> AgentAnalysisOutput:
        return AgentAnalysisOutput(
            agent_role=self.role,
            symbol=symbol,
            timeframe="1d",
            summary="Risk assessment: Volatility is moderate; maximum single-position limit must not exceed 5%.",
            sentiment=SentimentScore.NEUTRAL,
            confidence=0.90,
            observations=[
                "Portfolio level drawdown constraint is 20%; position must use hard stop-loss",
                "Liquidity depth is sufficient for intended paper-trading sizing",
            ],
            supporting_evidence=["Historical ATR indicates typical daily swing within 2.5%"],
            assumptions=["Liquidity does not vanish on market-wide stress days"],
            risks_identified=["Gap-down risk over market weekend closures"],
            invalidating_conditions=["Daily volatility spike exceeding 4% ATR"],
        )


class ResearchSynthesizerAgent(BaseAgent):
    """Synthesizes all individual perspectives into an actionable, balanced consensus report."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.RESEARCH_SYNTHESIZER

    async def analyze(
        self, symbol: str, df: pd.DataFrame, context: dict[str, Any] | None = None
    ) -> AgentAnalysisOutput:
        return AgentAnalysisOutput(
            agent_role=self.role,
            symbol=symbol,
            timeframe="1d",
            summary=f"Synthesis for {symbol}: Constructive medium-term setup with strict risk boundaries.",
            sentiment=SentimentScore.MODERATELY_BULLISH,
            confidence=0.75,
            observations=["Bullish structural momentum offset by moderate valuation and resistance nearby"],
            supporting_evidence=["Consensus among technical and fundamental reviewers"],
            assumptions=["Risk limits strictly enforced"],
            risks_identified=["Macro risk factors"],
            invalidating_conditions=["Breakdown below support zone"],
        )


class AgentCouncilOrchestrator:
    """Orchestrates the multi-agent council deliberation workflow."""

    def __init__(self):
        self.analysts: list[BaseAgent] = [
            MarketContextAgent(),
            TechnicalResearchAgent(),
            FundamentalResearchAgent(),
            NewsSentimentAgent(),
        ]
        self.bull_reviewer = BullishReviewerAgent()
        self.bear_reviewer = BearishReviewerAgent()
        self.risk_reviewer = IndependentRiskReviewerAgent()
        self.synthesizer = ResearchSynthesizerAgent()

    async def deliberate(self, symbol: str, df: pd.DataFrame) -> CouncilSynthesis:
        """Run complete multi-agent deliberation pipeline."""
        logger.info("Initiating AI Research Council deliberation", symbol=symbol)

        # Stage 1: Parallel Information Gathering
        analyst_reports: list[AgentAnalysisOutput] = []
        for analyst in self.analysts:
            res = await analyst.analyze(symbol, df)
            analyst_reports.append(res)

        # Stage 2: Adversarial Debate (Bull vs Bear)
        bull_report = await self.bull_reviewer.analyze(symbol, df)
        bear_report = await self.bear_reviewer.analyze(symbol, df)

        # Stage 3: Independent Risk Review
        risk_report = await self.risk_reviewer.analyze(symbol, df)

        # Stage 4: Synthesis
        curr_price = float(df["close"].iloc[-1])
        invalidation = round(curr_price * 0.94, 2)

        participating = [
            *[a.role for a in self.analysts],
            self.bull_reviewer.role,
            self.bear_reviewer.role,
            self.risk_reviewer.role,
            self.synthesizer.role,
        ]

        synthesis = CouncilSynthesis(
            symbol=symbol,
            timeframe="1d",
            consensus_sentiment=SentimentScore.MODERATELY_BULLISH,
            confidence=0.74,
            executive_summary=(
                f"Consensus evaluation for {symbol}: The council notes positive structural momentum "
                f"validated by sound balance sheet fundamentals. However, the bearish review warns "
                f"of overhead resistance. Prudent allocation is advised."
            ),
            bull_case_summary=bull_report.summary,
            bear_case_summary=bear_report.summary,
            risk_evaluation=risk_report.summary,
            proposed_action="ACCUMULATE_ON_PULLBACK",
            recommended_position_sizing_pct=4.0,  # 4% safe allocation
            invalidation_level=invalidation,
            participating_agents=participating,
        )

        logger.info(
            "Council deliberation completed successfully",
            symbol=symbol,
            action=synthesis.proposed_action,
        )
        return synthesis
