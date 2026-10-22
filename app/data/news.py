"""Financial News Intelligence and Entity Resolution Pipeline.

Handles:
- News ingestion from identifiable sources with timestamp and URL metadata
- Deduplication via normalized hashing
- NSE symbol resolution and company mapping
- Fact vs Interpretation separation
- Untrusted content sanitization (guarding against prompt injection attacks)
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)

# Known NSE Company Entity Mappings
NSE_COMPANY_MAPPING: dict[str, str] = {
    "reliance": "RELIANCE",
    "reliance industries": "RELIANCE",
    "tcs": "TCS",
    "tata consultancy": "TCS",
    "hdfc bank": "HDFCBANK",
    "hdfc": "HDFCBANK",
    "infosys": "INFY",
    "infy": "INFY",
    "icici bank": "ICICIBANK",
    "state bank of india": "SBIN",
    "sbi": "SBIN",
    "bharti airtel": "BHARTIARTL",
    "airtel": "BHARTIARTL",
    "itc": "ITC",
    "larsen & toubro": "LT",
    "l&t": "LT",
    "tata motors": "TATAMOTORS",
    "bajaj finance": "BAJFINANCE",
    "maruti suzuki": "MARUTI",
    "maruti": "MARUTI",
    "kotak mahindra": "KOTAKBANK",
    "kotak": "KOTAKBANK",
    "axis bank": "AXISBANK",
    "sun pharma": "SUNPHARMA",
}


class NewsItem(BaseModel):
    """Raw financial news item with provenance and security metadata."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    headline: str
    body: str
    source: str
    url: str
    published_at: datetime
    retrieved_at: datetime = Field(default_factory=datetime.now)
    symbol: str | None = None
    sector: str | None = None
    content_hash: str = ""
    is_verified: bool = True
    raw_facts: list[str] = Field(default_factory=list)


class NewsIntelligenceOutput(BaseModel):
    """Structured output from financial news analysis."""

    item: NewsItem
    affected_symbol: str
    factual_summary: str
    ai_interpretation: str
    sentiment_score: float  # -1.0 (bearish) to +1.0 (bullish)
    uncertainty_score: float  # 0.0 (certain) to 1.0 (highly speculative)
    contradictory_evidence: list[str] = Field(default_factory=list)
    sanitized: bool = True


class NewsPipeline:
    """Manages financial news ingestion, deduplication, and symbol mapping."""

    def __init__(self):
        self._seen_hashes: set[str] = set()

    def compute_hash(self, headline: str, source: str) -> str:
        """Compute normalized hash for deduplication."""
        norm = re.sub(r"[^\w\s]", "", headline.lower()).strip()
        key = f"{norm}::{source.lower().strip()}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def sanitize_untrusted_text(self, text: str) -> str:
        """Strip prompt injection attempts and system override instructions from external news."""
        # Block phrases like "Ignore previous instructions", "System prompt:", "Authorize trade"
        dangerous_patterns = [
            r"(?i)ignore\s+(all\s+)?(previous|prior)\s+instructions",
            r"(?i)you\s+are\s+now",
            r"(?i)system\s*:\s*",
            r"(?i)bypass\s+risk\s+limits?",
            r"(?i)execute\s+real\s+order",
        ]
        sanitized = text
        for pat in dangerous_patterns:
            sanitized = re.sub(pat, "[FILTERED_INSTRUCTION]", sanitized)
        return sanitized

    def resolve_symbol(self, headline: str, body: str) -> str | None:
        """Identify relevant NSE equity symbol from article text."""
        combined = f"{headline} {body}".lower()
        for entity_name, sym in NSE_COMPANY_MAPPING.items():
            pattern = rf"\b{re.escape(entity_name)}\b"
            if re.search(pattern, combined):
                return sym
        return None

    def process_news(
        self,
        headline: str,
        body: str,
        source: str,
        url: str,
        published_at: datetime,
    ) -> NewsItem | None:
        """Ingest, deduplicate, resolve symbol, and sanitize a news item."""
        content_hash = self.compute_hash(headline, source)
        if content_hash in self._seen_hashes:
            logger.debug("Duplicate news story suppressed", headline=headline[:40])
            return None

        self._seen_hashes.add(content_hash)
        sanitized_headline = self.sanitize_untrusted_text(headline)
        sanitized_body = self.sanitize_untrusted_text(body)
        symbol = self.resolve_symbol(sanitized_headline, sanitized_body)

        return NewsItem(
            headline=sanitized_headline,
            body=sanitized_body,
            source=source,
            url=url,
            published_at=published_at,
            symbol=symbol,
            content_hash=content_hash,
            raw_facts=[sanitized_headline],
        )
