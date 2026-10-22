"""Notifications package."""

from app.core.config import get_settings
from app.notifications.interfaces import (
    MockNotificationProvider,
    NotificationMessage,
    NotificationProvider,
)
from app.notifications.telegram import TelegramNotificationProvider
from app.notifications.templates import TelegramTemplates


def get_notification_provider() -> NotificationProvider:
    """Return configured notification provider singleton."""
    settings = get_settings()
    if settings.notification_provider.lower() == "telegram" and settings.telegram_bot_token:
        return TelegramNotificationProvider(settings)
    return MockNotificationProvider()


__all__ = [
    "NotificationMessage",
    "NotificationProvider",
    "MockNotificationProvider",
    "TelegramNotificationProvider",
    "TelegramTemplates",
    "get_notification_provider",
]
