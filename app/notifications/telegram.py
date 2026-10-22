"""Telegram notification provider for dispatching trade signals and reports."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import AppSettings, get_settings
from app.core.logging import get_logger
from app.notifications.interfaces import NotificationMessage, NotificationProvider

logger = get_logger(__name__)


class TelegramNotificationProvider(NotificationProvider):
    """Production Telegram Bot provider.

    Dispatches trading tips, council synthesis reports, and risk alerts
    directly to Telegram channels and direct chats.
    """

    TELEGRAM_API_BASE = "https://api.telegram.org"
    MAX_MESSAGE_LENGTH = 4000

    def __init__(self, settings: AppSettings | None = None, timeout: float = 10.0):
        self.settings = settings or get_settings()
        self.bot_token = self.settings.telegram_bot_token
        self.default_chat_id = self.settings.telegram_chat_id or self.settings.telegram_channel_username
        self.timeout = timeout

    async def send(self, message: NotificationMessage) -> bool:
        """Send formatted notification message to Telegram."""
        if not self.bot_token:
            logger.warning("Telegram dispatch skipped: TELEGRAM_BOT_TOKEN not configured.")
            return False

        chat_id = message.metadata.get("chat_id") or self.default_chat_id
        if not chat_id:
            logger.warning("Telegram dispatch skipped: No chat_id or channel specified.")
            return False

        formatted_text = self._format_message(message)
        chunks = self._chunk_text(formatted_text)

        success = True
        for chunk in chunks:
            chunk_sent = await self._send_raw_text(chat_id=str(chat_id), text=chunk)
            if not chunk_sent:
                success = False

        return success

    async def _send_raw_text(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "Markdown",
    ) -> bool:
        """Dispatch HTTP POST to Telegram sendMessage API."""
        url = f"{self.TELEGRAM_API_BASE}/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    logger.info("Telegram notification delivered", chat_id=chat_id)
                    return True
                elif resp.status_code == 403:
                    logger.error(
                        "Telegram 403 Forbidden: Ensure bot is added as Administrator to channel",
                        chat_id=chat_id,
                        response=resp.text,
                    )
                    return False
                else:
                    logger.warning(
                        "Telegram delivery warning",
                        status_code=resp.status_code,
                        response=resp.text[:200],
                    )
                    return False
        except Exception as err:
            logger.error("Failed to connect to Telegram API", error=str(err))
            return False

    def _format_message(self, message: NotificationMessage) -> str:
        """Format notification payload into clean Markdown for Telegram."""
        icon = {
            "info": "ℹ️",
            "warning": "⚠️",
            "alert": "🚨",
            "emergency": "🔥",
            "tip": "💡",
        }.get(message.level.lower(), "📢")

        lines = [
            f"{icon} *{message.title}*",
            "",
            message.body,
        ]

        if message.metadata:
            lines.append("")
            lines.append("📊 *Details:*")
            for k, v in message.metadata.items():
                if k != "chat_id":
                    lines.append(f"• `{k}`: {v}")

        lines.append("")
        lines.append(f"_Sent: {message.sent_at.strftime('%Y-%m-%d %H:%M:%S UTC')}_")
        return "\n".join(lines)

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into chunks below Telegram's 4096 character limit."""
        if len(text) <= self.MAX_MESSAGE_LENGTH:
            return [text]

        chunks = []
        while text:
            if len(text) <= self.MAX_MESSAGE_LENGTH:
                chunks.append(text)
                break
            split_idx = text.rfind("\n", 0, self.MAX_MESSAGE_LENGTH)
            if split_idx == -1:
                split_idx = self.MAX_MESSAGE_LENGTH
            chunks.append(text[:split_idx])
            text = text[split_idx:].lstrip("\n")
        return chunks
