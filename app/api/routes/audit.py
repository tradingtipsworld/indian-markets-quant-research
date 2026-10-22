"""Audit and system monitoring API routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.audit.logger import get_audit_logger

router = APIRouter(prefix="/audit", tags=["audit"])
audit_logger = get_audit_logger()


@router.get("/logs")
async def get_audit_logs(limit: int = 50):
    """Retrieve security and risk event audit trail."""
    events = audit_logger.get_events(limit=limit)
    return {
        "count": len(events),
        "events": [e.model_dump() for e in events],
    }
