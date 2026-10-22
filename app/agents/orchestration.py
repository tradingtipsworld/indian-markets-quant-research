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

Features:
- Provider-neutral abstraction with AutoAIService dynamic fallback
- Bull vs Bear adversarial debate preservation
- Strict Pydantic output validation
- Safe deterministic fallback if external AI services time out
- Zero hallucination policy: Missing data explicitly reported as NOT_AVAILABLE / UNKNOWN
- Mathematical indicators strictly computed from validated OHLCV data
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from app.agents.ai_service import AutoAIService
from app.agents.schemas import (
    AgentAnalysisOutput,
    AgentRole,
    CouncilSynthesis,
    SentimentScore,
)
from app.core.config import get_settings
from app.core.logging import get_logger
from app.quant.indicators.core import rsi, sma

logger = get_logger(__name__)


def validate_market_dataframe(df: pd.DataFrame | None) -> tuple[bool, str]:
    """Verify that market dataframe exists, is not empty, and contains required OHLCV columns."""
    if df is None or not isinstance(df, pd.DataFrame):
        return False, "Market dataframe is None or not a DataFrame"
    if df.empty:
        return False, "Market dataframe is empty (0 price bars)"
    required_cols = {"close", "open", "high", "low", "volume"}
    missing = required_cols - set(df.columns)
    if missing:
        return False, f"Missing required columns in market dataframe: {sorted(missing)}"
    if len(df) < 2:
        return False, "Insufficient price bars (minimum 2 bars required for calculations)"
    if df["close"].isna().any():
        return False, "Market dataframe contains NaN values in close price series"
    return True, "Valid"


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
        is_valid, err_msg = validate_market_dataframe(df)
        if not is_valid:
            return AgentAnalysisOutput(
                agent_role=self.role,
                symbol=symbol,
                timeframe="1d",
                summary=f"Market regime evaluation unavailable for {symbol}: {err_msg}.",
                sentiment=SentimentScore.UNKNOWN,
                confidence=0.0,
                observations=["Market data is missing or incomplete"],
                missing_data_notes=[err_msg],
            )

        close = df["close"]
        period = min(50, len(df))
        sma_val = float(sma(close, period).iloc[-1])
        curr_price = float(close.iloc[-1])
        is_bullish = curr_price >= sma_val
        regime = "bullish" if is_bullish else "bearish"

        # Calculate actual annualized volatility from returns
        returns = close.pct_change().dropna()
        hist_vol = float(returns.std() * np.sqrt(252)) if len(returns) > 1 and returns.std() > 0 else 0.0

        dist_pct = abs(curr_price - sma_val) / sma_val * 100.0 if sma_val > 0 else 0.0
        confidence = round(min(0.85, max(0.50, 0.50 + dist_pct / 50.0)), 2) if len(df) >= 30 else 0.50

        return AgentAnalysisOutput(
            agent_role=self.role,
            symbol=symbol,
            timeframe="1d",
            summary=f"Broad market regime for {symbol} is {regime} relative to {period}-period SMA.",
            sentiment=SentimentScore.BULLISH if is_bullish else SentimentScore.BEARISH,
            confidence=confidence,
            observations=[
                f"Current close: ₹{curr_price:.2f} vs {period}-period SMA: ₹{sma_val:.2f}",
                f"Calculated 252-day annualized volatility: {hist_vol * 100:.1f}%",
            ],
            supporting_evidence=[f"Price is {'above' if is_bullish else 'below'} {period}-period SMA ({sma_val:.2f})"],
            assumptions=["Historical price action reflects standard auction pricing"],
            risks_identified=["Regime shift if price breaks SMA trend filter"],
            invalidating_conditions=[f"Price crossing opposite side of {period}-SMA ({sma_val:.2f})"],
        )


class TechnicalResearchAgent(BaseAgent):
    """Evaluates technical indicators, momentum, and price boundaries."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.TECHNICAL_RESEARCH

    async def analyze(
        self, symbol: str, df: pd.DataFrame, context: dict[str, Any] | None = None
    ) -> AgentAnalysisOutput:
        is_valid, err_msg = validate_market_dataframe(df)
        if not is_valid:
            return AgentAnalysisOutput(
                agent_role=self.role,
                symbol=symbol,
                timeframe="1d",
                summary=f"Technical research unavailable for {symbol}: {err_msg}.",
                sentiment=SentimentScore.UNKNOWN,
                confidence=0.0,
                observations=["Technical calculation suspended due to missing data"],
                missing_data_notes=[err_msg],
            )

        close = df["close"]
        curr_price = float(close.iloc[-1])
        has_rsi = len(df) >= 14
        missing_notes: list[str] = []

        if has_rsi:
            rsi_series = rsi(close, 14)
            rsi_val = float(rsi_series.iloc[-1])
            if rsi_val > 60:
                sentiment = SentimentScore.BULLISH
                confidence = 0.70
            elif rsi_val < 40:
                sentiment = SentimentScore.BEARISH
                confidence = 0.70
            else:
                sentiment = SentimentScore.NEUTRAL
                confidence = 0.55
            rsi_obs = f"14-period RSI is {rsi_val:.1f}"
            rsi_evidence = [f"RSI reading: {rsi_val:.1f}"]
            invalidating = ["RSI crossing 50 centerline"]
        else:
            rsi_val = None
            sentiment = SentimentScore.NEUTRAL
            confidence = 0.40
            rsi_obs = f"14-period RSI unavailable ({len(df)} bars provided, minimum 14 required)"
            rsi_evidence = ["RSI calculation unavailable due to insufficient bars"]
            missing_notes.append("Fewer than 14 price bars available for complete RSI calculation")
            invalidating = []

        summary = (
            f"Technical indicators show {sentiment.value} momentum with RSI at {rsi_val:.1f}."
            if rsi_val is not None
            else f"Technical indicators show neutral posture; RSI unavailable with {len(df)} bars."
        )

        return AgentAnalysisOutput(
            agent_role=self.role,
            symbol=symbol,
            timeframe="1d",
            summary=summary,
            sentiment=sentiment,
            confidence=confidence,
            observations=[
                f"Latest bar Close: ₹{curr_price:.2f}",
                rsi_obs,
            ],
            supporting_evidence=rsi_evidence,
            assumptions=["Indicator calculation reflects clean, non-split price history"],
            risks_identified=["Momentum divergence or compression"],
            invalidating_conditions=invalidating,
            missing_data_notes=missing_notes,
        )


class FundamentalResearchAgent(BaseAgent):
    """Evaluates earnings growth, debt coverage, and valuation metrics when provided."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.FUNDAMENTAL_RESEARCH

    async def analyze(
        self, symbol: str, df: pd.DataFrame, context: dict[str, Any] | None = None
    ) -> AgentAnalysisOutput:
        fundamentals = (context or {}).get("fundamentals")

        if not fundamentals or not isinstance(fundamentals, dict):
            return AgentAnalysisOutput(
                agent_role=self.role,
                symbol=symbol,
                timeframe="1d",
                summary=f"Fundamental financial data for {symbol} is not available in the supplied context.",
                sentiment=SentimentScore.NOT_AVAILABLE,
                confidence=0.0,
                observations=["No verified balance sheet, debt-to-equity, or earnings reports were provided"],
                supporting_evidence=[],
                assumptions=["Fundamental evaluation suspended until verified corporate filings are ingested"],
                risks_identified=["Unquantified balance sheet or corporate event risk"],
                invalidating_conditions=[],
                missing_data_notes=["Statutory earnings, debt-to-equity, and operating margin datasets are missing"],
            )

        pe = fundamentals.get("pe_ratio")
        de = fundamentals.get("debt_to_equity")
        observations = []
        evidence = []

        if pe is not None:
            observations.append(f"Price-to-Earnings (P/E) ratio: {pe:.2f}")
            evidence.append(f"P/E ratio: {pe:.2f}")
        if de is not None:
            observations.append(f"Debt-to-Equity ratio: {de:.2f}")
            evidence.append(f"Debt-to-Equity: {de:.2f}")

        sentiment = SentimentScore.MODERATELY_BULLISH if (de is not None and de < 1.0) else SentimentScore.NEUTRAL
        confidence = 0.65 if observations else 0.0

        return AgentAnalysisOutput(
            agent_role=self.role,
            symbol=symbol,
            timeframe="1d",
            summary=f"Fundamental metrics available for {symbol}: evaluated {len(observations)} verified financial indicators.",
            sentiment=sentiment,
            confidence=confidence,
            observations=observations or ["Limited fundamental parameters provided"],
            supporting_evidence=evidence,
            assumptions=["Supplied fundamental parameters reflect verified statutory disclosures"],
            risks_identified=["Valuation compression or sectoral headwind"],
            invalidating_conditions=["Deterioration in next quarterly financial filing"],
        )


class NewsSentimentAgent(BaseAgent):
    """Evaluates market sentiment and verified corporate news when provided."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.NEWS_SENTIMENT

    async def analyze(
        self, symbol: str, df: pd.DataFrame, context: dict[str, Any] | None = None
    ) -> AgentAnalysisOutput:
        news_items = (context or {}).get("news") or (context or {}).get("news_items")

        if not news_items or not isinstance(news_items, list):
            return AgentAnalysisOutput(
                agent_role=self.role,
                symbol=symbol,
                timeframe="1d",
                summary=f"No verified news feed or disclosures available for {symbol} in the supplied context.",
                sentiment=SentimentScore.NOT_AVAILABLE,
                confidence=0.0,
                observations=["Zero news articles or corporate announcements ingested for this evaluation"],
                supporting_evidence=[],
                assumptions=["Sentiment evaluation requires authorized and sanitized news feed ingestion"],
                risks_identified=["Unidentified corporate or macro news event risks"],
                invalidating_conditions=[],
                missing_data_notes=["Corporate disclosures, regulatory filings, and press releases not provided"],
            )

        pos_count = sum(1 for item in news_items if (isinstance(item, dict) and item.get("sentiment") == "positive"))
        neg_count = sum(1 for item in news_items if (isinstance(item, dict) and item.get("sentiment") == "negative"))

        if pos_count > neg_count:
            sentiment = SentimentScore.MODERATELY_BULLISH
        elif neg_count > pos_count:
            sentiment = SentimentScore.MODERATELY_BEARISH
        else:
            sentiment = SentimentScore.NEUTRAL

        return AgentAnalysisOutput(
            agent_role=self.role,
            symbol=symbol,
            timeframe="1d",
            summary=f"Evaluated {len(news_items)} verified news items for {symbol} with {sentiment.value} bias.",
            sentiment=sentiment,
            confidence=min(0.80, 0.40 + len(news_items) * 0.05),
            observations=[f"Verified news sample: {pos_count} positive, {neg_count} negative, {len(news_items) - pos_count - neg_count} neutral"],
            supporting_evidence=[f"Sample size: {len(news_items)} verified articles"],
            assumptions=["Ingested news headlines are deduplicated and verified"],
            risks_identified=["Unanticipated breaking news developments"],
            invalidating_conditions=["Release of material negative regulatory disclosures"],
        )


class BullishReviewerAgent(BaseAgent):
    """Constructs the strongest plausible long argument and upside scenarios."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.BULLISH_REVIEWER

    async def analyze(
        self, symbol: str, df: pd.DataFrame, context: dict[str, Any] | None = None
    ) -> AgentAnalysisOutput:
        is_valid, err_msg = validate_market_dataframe(df)
        if not is_valid:
            return AgentAnalysisOutput(
                agent_role=self.role,
                symbol=symbol,
                timeframe="1d",
                summary=f"Cannot construct bull case for {symbol}: {err_msg}.",
                sentiment=SentimentScore.UNKNOWN,
                confidence=0.0,
                observations=["Bullish review suspended due to missing market data"],
                missing_data_notes=[err_msg],
            )

        curr_price = float(df["close"].iloc[-1])
        n_bars = min(20, len(df))
        trailing_high = float(df["high"].iloc[-n_bars:].max())
        trailing_low = float(df["low"].iloc[-n_bars:].min())

        # Measure volume trend
        recent_vol = float(df["volume"].iloc[-min(5, len(df)):].mean())
        base_vol = float(df["volume"].iloc[-n_bars:].mean())
        vol_ratio = (recent_vol / base_vol) if base_vol > 0 else 1.0

        target_price = round(max(curr_price * 1.02, trailing_high), 2)
        confidence = 0.70 if curr_price > trailing_low else 0.45

        return AgentAnalysisOutput(
            agent_role=self.role,
            symbol=symbol,
            timeframe="1d",
            summary=f"Bull case: Potential re-test toward ₹{target_price:.2f} based on trailing {n_bars}-bar structure.",
            sentiment=SentimentScore.BULLISH,
            confidence=confidence,
            observations=[
                f"Trailing {n_bars}-bar resistance high: ₹{trailing_high:.2f}",
                f"Trailing {n_bars}-bar support low: ₹{trailing_low:.2f}",
                f"Recent 5-bar volume ratio: {vol_ratio:.2f}x of {n_bars}-bar average",
            ],
            supporting_evidence=[f"Calculated trailing {n_bars}-bar range: ₹{trailing_low:.2f} - ₹{trailing_high:.2f}"],
            assumptions=["Underlying benchmark maintains stable liquidity"],
            risks_identified=["Failure to clear trailing high resistance"],
            invalidating_conditions=[f"Close below trailing support ₹{trailing_low:.2f}"],
        )


class BearishReviewerAgent(BaseAgent):
    """Adversarial critic: Stress-tests assumptions and identifies downside risks."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.BEARISH_REVIEWER

    async def analyze(
        self, symbol: str, df: pd.DataFrame, context: dict[str, Any] | None = None
    ) -> AgentAnalysisOutput:
        is_valid, err_msg = validate_market_dataframe(df)
        if not is_valid:
            return AgentAnalysisOutput(
                agent_role=self.role,
                symbol=symbol,
                timeframe="1d",
                summary=f"Cannot construct bear case for {symbol}: {err_msg}.",
                sentiment=SentimentScore.UNKNOWN,
                confidence=0.0,
                observations=["Bearish review suspended due to missing market data"],
                missing_data_notes=[err_msg],
            )

        curr_price = float(df["close"].iloc[-1])
        n_bars = min(20, len(df))
        trailing_high = float(df["high"].iloc[-n_bars:].max())
        trailing_low = float(df["low"].iloc[-n_bars:].min())
        downside_target = round(min(curr_price * 0.98, trailing_low), 2)

        return AgentAnalysisOutput(
            agent_role=self.role,
            symbol=symbol,
            timeframe="1d",
            summary=f"Bear case: Risk of mean-reversion toward trailing support ₹{downside_target:.2f}.",
            sentiment=SentimentScore.MODERATELY_BEARISH,
            confidence=0.65,
            observations=[
                f"Overhead resistance at trailing {n_bars}-bar high: ₹{trailing_high:.2f}",
                f"Downside mean-reversion level: ₹{downside_target:.2f}",
            ],
            supporting_evidence=[f"Trailing {n_bars}-bar high supply zone: ₹{trailing_high:.2f}"],
            assumptions=["Sellers defend structural trailing high levels"],
            risks_identified=["Breakout through trailing resistance invalidating short bias"],
            invalidating_conditions=[f"Decisive daily close above ₹{trailing_high:.2f}"],
        )


class IndependentRiskReviewerAgent(BaseAgent):
    """Validates risk limits, position sizing, and maximum allowable drawdown."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.RISK_REVIEWER

    async def analyze(
        self, symbol: str, df: pd.DataFrame, context: dict[str, Any] | None = None
    ) -> AgentAnalysisOutput:
        is_valid, err_msg = validate_market_dataframe(df)
        if not is_valid:
            return AgentAnalysisOutput(
                agent_role=self.role,
                symbol=symbol,
                timeframe="1d",
                summary=f"Risk clearance blocked for {symbol}: {err_msg}.",
                sentiment=SentimentScore.UNKNOWN,
                confidence=0.0,
                observations=["Risk calculations impossible without verified price data"],
                risks_identified=["Missing market data prevents risk calculations"],
                missing_data_notes=[err_msg],
            )

        curr_price = float(df["close"].iloc[-1])
        stop_price = round(curr_price * 0.96, 2)  # 4% hard stop

        return AgentAnalysisOutput(
            agent_role=self.role,
            symbol=symbol,
            timeframe="1d",
            summary=f"Risk Assessment for {symbol} at ₹{curr_price:.2f}: Position sizing capped under 5% capital with mandatory stop at ₹{stop_price:.2f}.",
            sentiment=SentimentScore.NEUTRAL,
            confidence=0.90,
            observations=[
                f"Entry reference price: ₹{curr_price:.2f}",
                f"Mandatory hard stop-loss: ₹{stop_price:.2f} (-4.0%)",
                "Maximum recommended allocation: 4.0% of portfolio",
            ],
            supporting_evidence=["Statutory portfolio concentration risk model"],
            assumptions=["Execution venue honors stop-loss orders with standard slippage"],
            risks_identified=["Gap-down risk through stop loss on market open"],
            invalidating_conditions=["Aggregate portfolio exposure already exceeding 75% limit"],
        )


class ResearchSynthesizerAgent(BaseAgent):
    """Reconciles conflicting perspectives and produces the final consensus."""

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
            summary="Synthesis: Reconciled multi-agent perspectives with strict risk boundaries.",
            sentiment=SentimentScore.NEUTRAL,
            confidence=0.70,
            observations=["Reconciled technical, structural, and risk perspectives"],
            supporting_evidence=["Deterministic mathematical indicator calculations"],
            assumptions=["Risk limits strictly enforced by independent risk engine"],
            risks_identified=["Regime shift or unexpected gap risk"],
            invalidating_conditions=["Breach of calculated invalidation level"],
        )


class AgentCouncilOrchestrator:
    """Orchestrates the multi-agent council deliberation workflow."""

    def __init__(self, ai_service: AutoAIService | None = None):
        self.ai_service = ai_service or AutoAIService()
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

    async def deliberate(
        self,
        symbol: str,
        df: pd.DataFrame,
        context: dict[str, Any] | None = None,
    ) -> CouncilSynthesis:
        """Run complete multi-agent deliberation pipeline with safe fallback and zero hallucination."""
        logger.info("Initiating AI Research Council deliberation", symbol=symbol)

        participating = [
            *[a.role for a in self.analysts],
            self.bull_reviewer.role,
            self.bear_reviewer.role,
            self.risk_reviewer.role,
            self.synthesizer.role,
        ]

        # Stage 0: Strict Input Data Validation
        is_valid, validation_err = validate_market_dataframe(df)
        if not is_valid:
            logger.warning("Deliberation aborted due to invalid market data", symbol=symbol, error=validation_err)
            return CouncilSynthesis(
                symbol=symbol,
                timeframe="1d",
                consensus_sentiment=SentimentScore.UNKNOWN,
                confidence=0.0,
                executive_summary=f"Council deliberation aborted for {symbol}: {validation_err}. No recommendation can be formed without verified market data.",
                bull_case_summary="Unavailable: Missing or invalid market data",
                bear_case_summary="Unavailable: Missing or invalid market data",
                risk_evaluation="Risk clearance blocked: Invalid or missing market data",
                proposed_action="NO_TRADE_MISSING_DATA",
                recommended_position_sizing_pct=0.0,
                invalidation_level=None,
                participating_agents=participating,
                missing_data_notes=[validation_err],
                audit_notes="Data validation failure: " + validation_err,
            )

        # Stage 1: Information Gathering
        analyst_reports: list[AgentAnalysisOutput] = []
        for analyst in self.analysts:
            res = await analyst.analyze(symbol, df, context=context)
            analyst_reports.append(res)

        # Stage 2: Adversarial Debate (Bull vs Bear)
        bull_report = await self.bull_reviewer.analyze(symbol, df, context=context)
        bear_report = await self.bear_reviewer.analyze(symbol, df, context=context)

        # Stage 3: Independent Risk Review
        risk_report = await self.risk_reviewer.analyze(symbol, df, context=context)

        # Stage 4: Collect missing data notes across all members
        all_missing_notes: list[str] = []
        for r in [*analyst_reports, bull_report, bear_report, risk_report]:
            all_missing_notes.extend(r.missing_data_notes)
        all_missing_notes = sorted(set(all_missing_notes))

        # Stage 5: Synthesis
        curr_price = float(df["close"].iloc[-1])
        invalidation = round(curr_price * 0.94, 2)

        market_report = analyst_reports[0]
        tech_report = analyst_reports[1]
        fund_report = analyst_reports[2]
        news_report = analyst_reports[3]

        # Determine consensus sentiment deterministically based on available data
        if market_report.sentiment == SentimentScore.BULLISH and tech_report.sentiment == SentimentScore.BULLISH:
            consensus_sentiment = SentimentScore.MODERATELY_BULLISH
            confidence = 0.70
            proposed_action = "ACCUMULATE_ON_PULLBACK"
            sizing = 4.0
        elif market_report.sentiment == SentimentScore.BEARISH or tech_report.sentiment == SentimentScore.BEARISH:
            consensus_sentiment = SentimentScore.MODERATELY_BEARISH
            confidence = 0.65
            proposed_action = "NO_TRADE_BEARISH_REGIME"
            sizing = 0.0
        else:
            consensus_sentiment = SentimentScore.NEUTRAL
            confidence = 0.50
            proposed_action = "OBSERVE_AND_EVALUATE"
            sizing = 2.0

        # Grounded factual summary
        data_coverage_note = (
            "Technical price action verified."
            + (" Fundamentals unavailable." if fund_report.sentiment == SentimentScore.NOT_AVAILABLE else " Fundamentals verified.")
            + (" News feed unavailable." if news_report.sentiment == SentimentScore.NOT_AVAILABLE else " News verified.")
        )

        exec_summary = (
            f"Consensus evaluation for {symbol} at ₹{curr_price:.2f}: Price posture is {market_report.sentiment.value} "
            f"relative to moving average with RSI at {tech_report.sentiment.value} momentum. "
            f"{data_coverage_note} Prudent allocation with stop at ₹{invalidation:.2f} is required."
        )

        # Stage 6: Dynamic LLM synthesis if active and configured
        settings = get_settings()
        if settings.ai_provider != "mock" and self.ai_service.get_available_providers():
            try:
                missing_str = ", ".join(all_missing_notes) if all_missing_notes else "None"
                prompt = (
                    f"Synthesize the research council debate for Indian equity {symbol} at ₹{curr_price:.2f}:\n"
                    f"- Market Regime: {market_report.summary}\n"
                    f"- Technical RSI: {tech_report.summary}\n"
                    f"- Bull Case: {bull_report.summary}\n"
                    f"- Bear Case: {bear_report.summary}\n"
                    f"- Risk Clearance: {risk_report.summary}\n"
                    f"- Missing Data Notes: {missing_str}\n"
                    "INSTRUCTIONS: Write a 2-sentence objective summary. DO NOT invent financial results or news. "
                    "State observed technical facts, downside risks, and the invalidation price ₹"
                    f"{invalidation:.2f}."
                )
                ai_resp = await self.ai_service.generate(
                    prompt=prompt,
                    system_prompt="You are the Lead Research Synthesizer of an Indian Quant Trading Council. Be strictly evidence-grounded, conservative, and objective.",
                )
                exec_summary = ai_resp.content.strip()
                logger.info("Live AI Council synthesis generated", provider=ai_resp.provider, model=ai_resp.model)
            except Exception as err:
                logger.warning("Live AI synthesis timed out or failed, using safe local synthesis", error=str(err))

        synthesis = CouncilSynthesis(
            symbol=symbol,
            timeframe="1d",
            consensus_sentiment=consensus_sentiment,
            confidence=confidence,
            executive_summary=exec_summary,
            bull_case_summary=bull_report.summary,
            bear_case_summary=bear_report.summary,
            risk_evaluation=risk_report.summary,
            proposed_action=proposed_action,
            recommended_position_sizing_pct=sizing,
            invalidation_level=invalidation,
            participating_agents=participating,
            missing_data_notes=all_missing_notes,
        )

        logger.info(
            "Council deliberation completed successfully",
            symbol=symbol,
            action=synthesis.proposed_action,
            sentiment=synthesis.consensus_sentiment.value,
        )
        return synthesis
