"""Unit tests for AI Research Council multi-agent deliberation and evidence grounding."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock
import pandas as pd
import pytest

from app.agents.orchestration import (
    AgentCouncilOrchestrator,
    FundamentalResearchAgent,
    MarketContextAgent,
    NewsSentimentAgent,
    TechnicalResearchAgent,
    validate_market_dataframe,
)
from app.agents.schemas import AgentRole, SentimentScore
from app.data.interfaces import Timeframe
from app.data.providers.synthetic import generate_synthetic_ohlcv


@pytest.mark.asyncio
async def test_council_deliberation(synthetic_ohlcv_df):
    council = AgentCouncilOrchestrator()
    synthesis = await council.deliberate("SYNTH_RELIANCE", synthetic_ohlcv_df)

    assert synthesis.symbol == "SYNTH_RELIANCE"
    assert synthesis.recommended_position_sizing_pct <= 10.0
    assert len(synthesis.participating_agents) == 8
    assert synthesis.invalidation_level is not None
    assert synthesis.consensus_sentiment in list(SentimentScore)


@pytest.mark.asyncio
async def test_council_empty_market_data():
    """Test 1: Empty market data returns safe NO_TRADE without raising exceptions."""
    council = AgentCouncilOrchestrator()
    empty_df = pd.DataFrame()
    synthesis = await council.deliberate("TEST_SYM", empty_df)

    assert synthesis.consensus_sentiment == SentimentScore.UNKNOWN
    assert synthesis.confidence == 0.0
    assert synthesis.proposed_action == "NO_TRADE_MISSING_DATA"
    assert synthesis.recommended_position_sizing_pct == 0.0
    assert len(synthesis.missing_data_notes) > 0


@pytest.mark.asyncio
async def test_council_missing_required_fields():
    """Test 2: Dataframe missing required OHLCV columns returns safe fallback."""
    council = AgentCouncilOrchestrator()
    bad_df = pd.DataFrame({"close": [100.0, 101.0, 102.0], "open": [99.0, 100.0, 101.0]})
    synthesis = await council.deliberate("TEST_SYM", bad_df)

    assert synthesis.consensus_sentiment == SentimentScore.UNKNOWN
    assert synthesis.confidence == 0.0
    assert "Missing required columns" in synthesis.missing_data_notes[0]


@pytest.mark.asyncio
async def test_council_invalid_ohlcv_nan():
    """Test 3: Dataframe with NaN values in close is caught by validation."""
    council = AgentCouncilOrchestrator()
    df = generate_synthetic_ohlcv("SYNTH_TCS", date(2025, 1, 1), date(2025, 2, 1), Timeframe.DAILY)
    df.loc[df.index[5], "close"] = float("nan")

    synthesis = await council.deliberate("SYNTH_TCS", df)
    assert synthesis.consensus_sentiment == SentimentScore.UNKNOWN
    assert "NaN values" in synthesis.missing_data_notes[0]


@pytest.mark.asyncio
async def test_missing_fundamental_and_news_data(synthetic_ohlcv_df):
    """Test 4: When context has no fundamentals or news, agents return NOT_AVAILABLE."""
    fund_agent = FundamentalResearchAgent()
    news_agent = NewsSentimentAgent()

    fund_report = await fund_agent.analyze("SYNTH_RELIANCE", synthetic_ohlcv_df, context={})
    assert fund_report.sentiment == SentimentScore.NOT_AVAILABLE
    assert fund_report.confidence == 0.0
    assert len(fund_report.missing_data_notes) > 0
    assert "not available" in fund_report.summary.lower()

    news_report = await news_agent.analyze("SYNTH_RELIANCE", synthetic_ohlcv_df, context=None)
    assert news_report.sentiment == SentimentScore.NOT_AVAILABLE
    assert news_report.confidence == 0.0
    assert len(news_report.missing_data_notes) > 0


@pytest.mark.asyncio
async def test_unavailable_evidence_not_fabricated(synthetic_ohlcv_df):
    """Test 5: Agents do not claim balance sheet stability or zero regulatory inquiries when data absent."""
    council = AgentCouncilOrchestrator()
    synthesis = await council.deliberate("SYNTH_RELIANCE", synthetic_ohlcv_df, context={})

    assert any("missing" in n.lower() or "not provided" in n.lower() for n in synthesis.missing_data_notes)
    assert "sound balance sheet fundamentals" not in synthesis.executive_summary.lower()


@pytest.mark.asyncio
async def test_valid_market_data_calculated_indicators(synthetic_ohlcv_df):
    """Test 6: Valid market data computes actual mathematical SMA, RSI, and volatility."""
    tech_agent = TechnicalResearchAgent()
    market_agent = MarketContextAgent()

    tech_report = await tech_agent.analyze("SYNTH_RELIANCE", synthetic_ohlcv_df)
    assert tech_report.sentiment in (SentimentScore.BULLISH, SentimentScore.BEARISH, SentimentScore.NEUTRAL)
    assert "14-period RSI is" in tech_report.observations[1]
    assert tech_report.confidence > 0.0

    market_report = await market_agent.analyze("SYNTH_RELIANCE", synthetic_ohlcv_df)
    assert market_report.sentiment in (SentimentScore.BULLISH, SentimentScore.BEARISH)
    assert "annualized volatility" in market_report.observations[1].lower()


@pytest.mark.asyncio
async def test_safe_handling_of_ai_provider_failure(synthetic_ohlcv_df):
    """Test 7: Safe fallback when live AI service times out or throws exception."""
    mock_ai = AsyncMock()
    mock_ai.get_available_providers = MagicMock(return_value=["groq"])
    mock_ai.generate.side_effect = RuntimeError("Upstream API rate limit or timeout")

    council = AgentCouncilOrchestrator(ai_service=mock_ai)
    synthesis = await council.deliberate("SYNTH_RELIANCE", synthetic_ohlcv_df)

    assert synthesis.symbol == "SYNTH_RELIANCE"
    assert synthesis.consensus_sentiment in list(SentimentScore)
    assert "Consensus evaluation" in synthesis.executive_summary
