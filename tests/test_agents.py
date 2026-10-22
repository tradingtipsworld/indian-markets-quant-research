"""Unit tests for AI Research Council multi-agent deliberation."""

import pytest
from app.agents.orchestration import AgentCouncilOrchestrator
from app.agents.schemas import SentimentScore


@pytest.mark.asyncio
async def test_council_deliberation(synthetic_ohlcv_df):
    council = AgentCouncilOrchestrator()
    synthesis = await council.deliberate("SYNTH_RELIANCE", synthetic_ohlcv_df)

    assert synthesis.symbol == "SYNTH_RELIANCE"
    assert synthesis.recommended_position_sizing_pct <= 10.0
    assert len(synthesis.participating_agents) == 8
    assert synthesis.invalidation_level is not None
    assert synthesis.consensus_sentiment in list(SentimentScore)
