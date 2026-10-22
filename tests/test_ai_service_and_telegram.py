"""Unit tests for AutoAIService and Telegram notification provider."""

import pytest
from unittest.mock import AsyncMock, patch
from app.agents.ai_service import AutoAIService, AIResponse
from app.core.config import AppSettings
from app.notifications.interfaces import NotificationMessage
from app.notifications.telegram import TelegramNotificationProvider


@pytest.mark.asyncio
async def test_auto_ai_service_offline_fallback():
    # Empty settings: no keys -> deterministic local response
    settings = AppSettings(
        groq_api_key="",
        gemini_api_key="",
        gemini_api_key_backup="",
        mistral_api_key="",
        nvidia_api_key="",
        openrouter_api_key="",
    )
    service = AutoAIService(settings=settings)
    assert service.get_available_providers() == []

    resp = await service.generate("Evaluate NIFTY 50 trend")
    assert isinstance(resp, AIResponse)
    assert resp.provider == "mock"
    assert "Evaluate NIFTY 50" in resp.content


@pytest.mark.asyncio
async def test_auto_ai_service_provider_selection():
    settings = AppSettings(
        groq_api_key="mock_groq_key",
        gemini_api_key="mock_gemini_key",
        mistral_api_key="mock_mistral_key",
    )
    service = AutoAIService(settings=settings)
    providers = service.get_available_providers()
    assert "groq" in providers
    assert "gemini" in providers
    assert "mistral" in providers


@pytest.mark.asyncio
async def test_telegram_provider_formatting_and_chunking():
    settings = AppSettings(
        telegram_bot_token="test_bot_token",
        telegram_chat_id="-100123456789",
    )
    provider = TelegramNotificationProvider(settings=settings)

    msg = NotificationMessage(
        title="NIFTY Breakout Alert",
        body="Price has crossed 200 EMA with heavy volume.",
        level="alert",
        metadata={"Symbol": "NIFTY", "Entry": "24,500", "SL": "24,400"},
    )

    formatted = provider._format_message(msg)
    assert "NIFTY Breakout Alert" in formatted
    assert "Price has crossed" in formatted
    assert "• `Symbol`: NIFTY" in formatted

    # Test chunking of large text
    long_text = "A" * 9000
    chunks = provider._chunk_text(long_text)
    assert len(chunks) >= 3
    for chunk in chunks:
        assert len(chunk) <= provider.MAX_MESSAGE_LENGTH


@pytest.mark.asyncio
async def test_telegram_provider_dispatch_mock():
    settings = AppSettings(
        telegram_bot_token="fake_token",
        telegram_chat_id="fake_chat",
    )
    provider = TelegramNotificationProvider(settings=settings)

    with patch.object(provider, "_send_raw_text", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        msg = NotificationMessage(title="Test", body="Body content")
        success = await provider.send(msg)
        assert success is True
        mock_send.assert_called_once()
