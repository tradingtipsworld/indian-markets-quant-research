"""Audit logging and security event tracking."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)


class AuditEventType(str, Enum):
    SYSTEM_STARTUP = "system_startup"
    CONFIGURATION_CHANGE = "configuration_change"
    RISK_CHECK_REJECTED = "risk_check_rejected"
    KILL_SWITCH_TOGGLED = "kill_switch_toggled"
    ORDER_SUBMITTED = "order_submitted"
    ORDER_FILLED = "order_filled"
    ORDER_REJECTED = "order_rejected"
    AUTH_FAILURE = "auth_failure"


class AuditEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: AuditEventType
    actor: str = "system"
    description: str
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class AuditTrailLogger:
    """In-memory and structured audit logger for security-relevant operations."""

    def __init__(self):
        self._events: list[AuditEvent] = []

    def record(
        self,
        event_type: AuditEventType,
        description: str,
        actor: str = "system",
        details: dict[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_type=event_type,
            actor=actor,
            description=description,
            details=details or {},
        )
        self._events.append(event)
        logger.info(
            "Audit event recorded",
            event_type=event.event_type.value,
            actor=event.actor,
            description=description,
        )
        return event

    def get_events(self, limit: int = 50) -> list[AuditEvent]:
        return self._events[-limit:]


_global_audit = AuditTrailLogger()


def get_audit_logger() -> AuditTrailLogger:
    return _global_audit
