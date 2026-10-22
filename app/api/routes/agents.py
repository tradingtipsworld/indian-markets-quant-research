"""AI Research Council deliberation API routes."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.orchestration import AgentCouncilOrchestrator
from app.data.interfaces import Exchange, Timeframe
from app.data.providers.synthetic import SyntheticDataProvider
from app.reports.generator import ReportGenerator

router = APIRouter(prefix="/agents", tags=["ai_agents"])
council = AgentCouncilOrchestrator()
data_provider = SyntheticDataProvider()


class DeliberationRequest(BaseModel):
    symbol: str = "SYNTH_RELIANCE"
    history_days: int = 90


@router.post("/council/deliberate")
async def run_council_deliberation(req: DeliberationRequest):
    """Trigger full multi-agent research council debate and synthesis."""
    end = date.today()
    start = end - timedelta(days=req.history_days)

    df = await data_provider.get_ohlcv(
        symbol=req.symbol,
        exchange=Exchange.SYNTHETIC,
        timeframe=Timeframe.DAILY,
        start_date=start,
        end_date=end,
    )

    if df.empty or len(df) < 30:
        raise HTTPException(status_code=400, detail="Insufficient data to conduct research review")

    synthesis = await council.deliberate(symbol=req.symbol, df=df)
    report = ReportGenerator.generate_council_report(synthesis)

    return {
        "synthesis": synthesis.model_dump(),
        "report_markdown": report.markdown_content,
    }
