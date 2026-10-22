"""Resilient Multi-Provider AI Service with Auto-Model Discovery & Dynamic Fallback.

Supports dynamic cascade across:
1. Groq (High-speed LLMs)
2. Google Gemini (Gemini 2.5/2.0/1.5 Flash with primary/backup key fallback)
3. Mistral AI (Mistral Large / Codestral)
4. NVIDIA NIM (Llama 3.3 / Nemotron)
5. OpenRouter (Multi-model routing)

Features:
- Live Model Auto-Discovery: Dynamically fetches current available models from provider endpoints.
- Auto Model Selection: Automatically selects working text/chat models and adapts when providers add or deprecate models.
- Multi-tier Fallback: Provider-level and model-level automatic cascading.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import AppSettings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AIResponse:
    """Standardized response from any AI provider."""

    content: str
    provider: str
    model: str
    latency_ms: float
    raw_response: dict[str, Any] | None = None


class AutoAIService:
    """Dynamic multi-provider LLM coordinator with automatic model discovery and fallback."""

    # Default fallback chains per provider (used if live discovery is unavailable)
    STATIC_FALLBACK_MODELS: dict[str, list[str]] = {
        "groq": [
            "openai/gpt-oss-20b",
            "openai/gpt-oss-120b",
            "qwen/qwen3.8-27b",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
        ],
        "gemini": [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-2.5-pro",
        ],
        "mistral": [
            "codestral-latest",
            "mistral-large-latest",
            "mistral-small-latest",
            "open-mistral-7b",
        ],
        "nvidia": [
            "meta/llama-3.3-70b-instruct",
            "mistralai/mistral-large-2-instruct",
            "nvidia/nemotron-4-340b-instruct",
            "01-ai/yi-large",
        ],
        "openrouter": [
            "meta-llama/llama-3.3-70b-instruct:free",
            "google/gemini-2.0-flash-exp:free",
            "mistralai/mistral-7b-instruct:free",
        ],
    }

    # In-memory cache for discovered models: provider -> (timestamp, [models])
    _model_cache: dict[str, tuple[float, list[str]]] = {}
    CACHE_TTL_SECONDS = 3600.0  # 1 hour cache

    def __init__(self, settings: AppSettings | None = None, timeout: float = 15.0):
        self.settings = settings or get_settings()
        self.timeout = timeout

    def get_available_providers(self) -> list[str]:
        """Return list of providers with configured API keys in priority order."""
        providers = []
        if self.settings.groq_api_key:
            providers.append("groq")
        if self.settings.gemini_api_key or self.settings.gemini_api_key_backup:
            providers.append("gemini")
        if self.settings.mistral_api_key:
            providers.append("mistral")
        if self.settings.nvidia_api_key:
            providers.append("nvidia")
        if self.settings.openrouter_api_key:
            providers.append("openrouter")
        return providers

    async def get_models_for_provider(self, provider: str) -> list[str]:
        """Dynamically fetch and filter available chat models for a provider, with caching."""
        now = time.time()
        if provider in self._model_cache:
            ts, cached_models = self._model_cache[provider]
            if now - ts < self.CACHE_TTL_SECONDS and cached_models:
                return cached_models

        discovered = await self._discover_models(provider)
        if discovered:
            self._model_cache[provider] = (now, discovered)
            return discovered

        # Fallback to static list
        fallback = self.STATIC_FALLBACK_MODELS.get(provider, [])
        self._model_cache[provider] = (now, fallback)
        return fallback

    async def _discover_models(self, provider: str) -> list[str]:
        """Query provider's live models endpoint to discover active text/chat models."""
        try:
            if provider == "groq":
                return await self._discover_groq()
            elif provider == "gemini":
                return await self._discover_gemini()
            elif provider == "mistral":
                return await self._discover_mistral()
            elif provider == "nvidia":
                return await self._discover_nvidia()
            elif provider == "openrouter":
                return await self._discover_openrouter()
        except Exception as err:
            logger.debug("Live model discovery failed, using fallback list", provider=provider, error=str(err))
        return []

    async def _discover_groq(self) -> list[str]:
        headers = {
            "Authorization": f"Bearer {self.settings.groq_api_key}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        }
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get("https://api.groq.com/openai/v1/models", headers=headers)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                candidates = [
                    m["id"] for m in data
                    if m.get("active", True)
                    and not any(x in m["id"].lower() for x in ["whisper", "guard", "embedding", "audio", "orpheus"])
                ]
                return candidates or self.STATIC_FALLBACK_MODELS["groq"]
        return []

    async def _discover_gemini(self) -> list[str]:
        key = self.settings.gemini_api_key or self.settings.gemini_api_key_backup
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json().get("models", [])
                models = []
                for m in data:
                    name = m.get("name", "").replace("models/", "")
                    methods = m.get("supportedGenerationMethods", [])
                    if "generateContent" in methods and "preview" not in name and "tts" not in name:
                        models.append(name)
                # Prioritize flash models
                models.sort(key=lambda x: (0 if "flash" in x else 1, 0 if "2." in x else 1))
                return models or self.STATIC_FALLBACK_MODELS["gemini"]
        return []

    async def _discover_mistral(self) -> list[str]:
        headers = {"Authorization": f"Bearer {self.settings.mistral_api_key}"}
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get("https://api.mistral.ai/v1/models", headers=headers)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                models = [
                    m["id"] for m in data
                    if not any(x in m["id"].lower() for x in ["embed", "moderation", "vision"])
                ]
                return models or self.STATIC_FALLBACK_MODELS["mistral"]
        return []

    async def _discover_nvidia(self) -> list[str]:
        headers = {"Authorization": f"Bearer {self.settings.nvidia_api_key}"}
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get("https://integrate.api.nvidia.com/v1/models", headers=headers)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                models = [
                    m["id"] for m in data
                    if any(x in m["id"].lower() for x in ["llama", "mistral", "nemotron", "instruct", "chat"])
                    and not any(x in m["id"].lower() for x in ["embed", "reward", "guard"])
                ]
                return models or self.STATIC_FALLBACK_MODELS["nvidia"]
        return []

    async def _discover_openrouter(self) -> list[str]:
        headers = {"Authorization": f"Bearer {self.settings.openrouter_api_key}"}
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get("https://openrouter.ai/api/v1/models", headers=headers)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                free_models = [m["id"] for m in data if ":free" in m.get("id", "")]
                return free_models or self.STATIC_FALLBACK_MODELS["openrouter"]
        return []

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "You are a professional quantitative financial analyst.",
        preferred_provider: str | None = None,
    ) -> AIResponse:
        """Generate response with automatic provider and model fallback."""
        providers = self.get_available_providers()

        if not providers:
            return AIResponse(
                content=f"[Local Deterministic Synthesis] Evaluated: {prompt[:80]}...",
                provider="mock",
                model="local-rule-engine",
                latency_ms=1.0,
            )

        if preferred_provider and preferred_provider in providers:
            providers = [preferred_provider] + [p for p in providers if p != preferred_provider]

        last_error: Exception | None = None

        for provider in providers:
            models = await self.get_models_for_provider(provider)
            for model in models:
                start_time = time.perf_counter()
                try:
                    content = await self._call_provider(
                        provider=provider,
                        model=model,
                        prompt=prompt,
                        system_prompt=system_prompt,
                    )
                    latency = (time.perf_counter() - start_time) * 1000.0
                    logger.info(
                        "AI Generation succeeded",
                        provider=provider,
                        model=model,
                        latency_ms=round(latency, 2),
                    )
                    return AIResponse(
                        content=content,
                        provider=provider,
                        model=model,
                        latency_ms=latency,
                    )
                except Exception as err:
                    last_error = err
                    logger.warning(
                        "Provider call failed, trying next model or provider",
                        provider=provider,
                        model=model,
                        error=str(err),
                    )
                    continue

        raise RuntimeError(f"All AI providers and fallback models failed. Last error: {last_error}")

    async def _call_provider(
        self,
        provider: str,
        model: str,
        prompt: str,
        system_prompt: str,
    ) -> str:
        """Dispatch call to specific provider implementation."""
        if provider == "groq":
            return await self._call_openai_compatible(
                base_url="https://api.groq.com/openai/v1/chat/completions",
                api_key=self.settings.groq_api_key,
                model=model,
                prompt=prompt,
                system_prompt=system_prompt,
                extra_headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )
        elif provider == "gemini":
            return await self._call_gemini(
                model=model,
                prompt=prompt,
                system_prompt=system_prompt,
            )
        elif provider == "mistral":
            return await self._call_openai_compatible(
                base_url="https://api.mistral.ai/v1/chat/completions",
                api_key=self.settings.mistral_api_key,
                model=model,
                prompt=prompt,
                system_prompt=system_prompt,
            )
        elif provider == "nvidia":
            return await self._call_openai_compatible(
                base_url="https://integrate.api.nvidia.com/v1/chat/completions",
                api_key=self.settings.nvidia_api_key,
                model=model,
                prompt=prompt,
                system_prompt=system_prompt,
            )
        elif provider == "openrouter":
            return await self._call_openai_compatible(
                base_url="https://openrouter.ai/api/v1/chat/completions",
                api_key=self.settings.openrouter_api_key,
                model=model,
                prompt=prompt,
                system_prompt=system_prompt,
                extra_headers={
                    "HTTP-Referer": "https://tradingtipsworld.com",
                    "X-Title": "Trading Tips World",
                },
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")

    async def _call_openai_compatible(
        self,
        base_url: str,
        api_key: str,
        model: str,
        prompt: str,
        system_prompt: str,
        extra_headers: dict[str, str] | None = None,
    ) -> str:
        """Call OpenAI-compatible chat completions endpoint."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 1024,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(base_url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _call_gemini(
        self,
        model: str,
        prompt: str,
        system_prompt: str,
    ) -> str:
        """Call Google Gemini REST API with primary and backup key support."""
        keys = [k for k in [self.settings.gemini_api_key, self.settings.gemini_api_key_backup] if k]
        if not keys:
            raise ValueError("No Gemini API key configured.")

        last_err: Exception | None = None
        for key in keys:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"System Context: {system_prompt}\n\nTask: {prompt}"}
                        ]
                    }
                ]
            }
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates and "content" in candidates[0]:
                            parts = candidates[0]["content"].get("parts", [])
                            if parts and "text" in parts[0]:
                                return parts[0]["text"]
                        return str(data)
                    else:
                        last_err = RuntimeError(f"Gemini HTTP {resp.status_code}: {resp.text[:150]}")
            except Exception as err:
                last_err = err
                continue

        raise RuntimeError(f"Gemini call failed with all available keys: {last_err}")
