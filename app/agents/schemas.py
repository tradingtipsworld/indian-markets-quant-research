"""AI Research Council schemas and structured output contracts.

Enforces strict Pydantic structures for all agent analyses:
- Market context
- Technical findings
- Fundamental metrics
- News / Sentiment analysis
- Bullish thesis with evidence and invalidation
- Bearish thesis with downside catalysts
- Independent risk review
- Research synthesis

AI outputs are strictly non-authoritative recommendations and can NEVER
bypass the independent risk engine.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    MARKET_CONTEXT = "market_context_analyst"
    TECHNICAL_RESEARCH = "technical_research_analyst"
    FUNDAMENTAL_RESEARCH = "fundamental_research_analyst"
    NEWS_SENTIMENT = "news_sentiment_analyst"
    BULLISH_REVIEWER = "bullish_reviewer"
    BEARISH_REVIEWER = "bearish_reviewer"
    RISK_REVIEWER = "independent_risk_reviewer"
    RESEARCH_SYNTHESIZER = "research_synthesizer"


class SentimentScore(str, Enum):
    BULLISH = "bullish"
    MODERATELY_BULLISH = "moderately_bullish"
    NEUTRAL = "neutral"
    MODERATELY_BEARISH = "moderately_bearish"
    BEARISH = "bearish"
    UNKNOWN = "unknown"
    NOT_AVAILABLE = "not_available"


class AgentAnalysisOutput(BaseModel):
    """Base structured output format for all individual agent evaluations."""

    agent_role: AgentRole
    symbol: str
    timeframe: str
    timestamp: datetime = Field(default_factory=datetime.now)
    summary: str
    sentiment: SentimentScore
    confidence: float = Field(ge=0.0, le=1.0, description="0.0 to 1.0 confidence score")
    observations: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risks_identified: list[str] = Field(default_factory=list)
    invalidating_conditions: list[str] = Field(default_factory=list)
    missing_data_notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BullishThesis(BaseModel):
    """Detailed thesis prepared by the Bullish Reviewer."""

    catalysts: list[str]
    upside_targets: list[float] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    key_supports: list[float] = Field(default_factory=list)


class BearishThesis(BaseModel):
    """Detailed thesis prepared by the Bearish Reviewer."""

    downside_catalysts: list[str]
    downside_targets: list[float] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    key_resistances: list[float] = Field(default_factory=list)


class CouncilSynthesis(BaseModel):
    """Final multi-agent synthesized consensus report."""

    symbol: str
    timeframe: str
    consensus_sentiment: SentimentScore
    confidence: float = Field(ge=0.0, le=1.0)
    executive_summary: str
    bull_case_summary: str
    bear_case_summary: str
    risk_evaluation: str
    proposed_action: str  # e.g., "ACCUMULATE", "WAIT_FOR_DIP", "REDUCE", "HOLD", "NO_TRADE_MISSING_DATA"
    recommended_position_sizing_pct: float = Field(
        ge=0.0, le=10.0, description="Recommended max allocation <= 10%"
    )
    invalidation_level: float | None = None
    participating_agents: list[AgentRole] = Field(default_factory=list)
    missing_data_notes: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    audit_notes: str = (
        "Educational research report only. Not financial advice. "
        "Any trade execution requires independent risk engine clearance."
    )
