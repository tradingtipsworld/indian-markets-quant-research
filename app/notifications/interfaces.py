"""Notification interfaces and mock provider with future Telegram blueprint."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)


class NotificationMessage(BaseModel):
    """Notification message payload."""

    title: str
    body: str
    channel: str = "general"
    level: str = "info"  # info, warning, alert, emergency
    metadata: dict[str, Any] = Field(default_factory=dict)
    sent_at: datetime = Field(default_factory=datetime.now)


class NotificationProvider(ABC):
    """Abstract interface for notification channels."""

    @abstractmethod
    async def send(self, message: NotificationMessage) -> bool:
        ...


class MockNotificationProvider(NotificationProvider):
    """Mock notification provider for local development without credentials."""

    def __init__(self):
        self.sent_messages: list[NotificationMessage] = []

    async def send(self, message: NotificationMessage) -> bool:
        self.sent_messages.append(message)
        logger.info(
            "Notification dispatched [MOCK]",
            title=message.title,
            channel=message.channel,
            level=message.level,
        )
        return True


class TelegramNotifierBlueprint:
    """Blueprint for future Telegram bot adapter.

    Phase 5 ready — requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in production.
    """

    def __init__(self, bot_token: str = "", default_chat_id: str = ""):
        self.bot_token = bot_token
        self.default_chat_id = default_chat_id

    async def send_research_report(self, markdown_text: str, chat_id: str | None = None) -> bool:
        # Phase 5 integration point with python-telegram-bot or httpx
        logger.info("Telegram integration is scheduled for Phase 5", length=len(markdown_text))
        return False
