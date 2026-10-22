"""User, membership tiers, and role authorization foundations."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MembershipTier(str, Enum):
    FREE = "free"
    PRO_RESEARCH = "pro_research"
    QUANT_ENTERPRISE = "quant_enterprise"


class UserRole(str, Enum):
    ANALYST = "analyst"
    RESEARCHER = "researcher"
    RISK_OFFICER = "risk_officer"
    ADMIN = "admin"


class UserProfile(BaseModel):
    """User account entity for future multi-tenant auth layer."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    email: str
    username: str
    tier: MembershipTier = MembershipTier.FREE
    role: UserRole = UserRole.RESEARCHER
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)

    def can_access_ai_council(self) -> bool:
        return self.tier in (MembershipTier.PRO_RESEARCH, MembershipTier.QUANT_ENTERPRISE)

    def can_access_backtesting(self) -> bool:
        return True  # Available in all tiers for education

    def can_toggle_kill_switch(self) -> bool:
        return self.role in (UserRole.RISK_OFFICER, UserRole.ADMIN)
