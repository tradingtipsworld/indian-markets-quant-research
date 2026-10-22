"""Indian Market Session Calendar and Timezone Management.

Handles NSE/BSE trading sessions, market timings, pre-open, regular trading,
and session validation in Asia/Kolkata timezone (IST, UTC+05:30).
"""

from __future__ import annotations

from datetime import date, datetime, time
from enum import Enum
from zoneinfo import ZoneInfo

IST_TIMEZONE = ZoneInfo("Asia/Kolkata")


class MarketSessionState(str, Enum):
    """Trading session phase."""

    CLOSED = "closed"
    PRE_OPEN = "pre_open"  # 09:00 - 09:08 IST
    PRE_OPEN_MATCH = "pre_open_match"  # 09:08 - 09:15 IST
    REGULAR_TRADING = "regular_trading"  # 09:15 - 15:30 IST
    CLOSING_SESSION = "closing_session"  # 15:40 - 16:00 IST
    HOLIDAY_WEEKEND = "holiday_weekend"


class IndianMarketCalendar:
    """Manages Indian cash equity market trading sessions (NSE/BSE)."""

    PRE_OPEN_START = time(9, 0)
    PRE_OPEN_END = time(9, 8)
    REGULAR_START = time(9, 15)
    REGULAR_END = time(15, 30)
    POST_CLOSE_START = time(15, 40)
    POST_CLOSE_END = time(16, 0)

    # Standard NSE Trading Holidays (extendable)
    STANDARD_HOLIDAYS_2026: set[date] = {
        date(2026, 1, 26),  # Republic Day
        date(2026, 3, 6),   # Mahashivratri
        date(2026, 3, 25),  # Holi
        date(2026, 4, 2),   # Good Friday
        date(2026, 4, 14),  # Dr. Baba Saheb Ambedkar Jayanti
        date(2026, 5, 1),   # Maharashtra Day
        date(2026, 8, 15),  # Independence Day
        date(2026, 10, 2),  # Mahatma Gandhi Jayanti
        date(2026, 10, 20), # Dussehra
        date(2026, 11, 8),  # Diwali Laxmi Pujan (Muhurat trading separate)
        date(2026, 11, 10), # Diwali Balipratipada
        date(2026, 11, 24), # Gurunanak Jayanti
        date(2026, 12, 25), # Christmas
    }

    @classmethod
    def get_ist_now(cls) -> datetime:
        """Return current datetime localized to Asia/Kolkata (IST)."""
        return datetime.now(IST_TIMEZONE)

    @classmethod
    def is_trading_day(cls, dt: date | datetime) -> bool:
        """Check if the given date is a weekday and not a known market holiday."""
        d = dt.date() if isinstance(dt, datetime) else dt
        # 5 = Saturday, 6 = Sunday
        if d.weekday() >= 5:
            return False
        if d in cls.STANDARD_HOLIDAYS_2026:
            return False
        return True

    @classmethod
    def get_session_state(cls, dt: datetime | None = None) -> MarketSessionState:
        """Evaluate the current market session state for Indian markets."""
        now = dt or cls.get_ist_now()
        if now.tzinfo is None:
            # Assume IST if naive
            now = now.replace(tzinfo=IST_TIMEZONE)
        else:
            now = now.astimezone(IST_TIMEZONE)

        if not cls.is_trading_day(now):
            return MarketSessionState.HOLIDAY_WEEKEND

        current_time = now.time()

        if current_time < cls.PRE_OPEN_START:
            return MarketSessionState.CLOSED
        elif cls.PRE_OPEN_START <= current_time < cls.PRE_OPEN_END:
            return MarketSessionState.PRE_OPEN
        elif cls.PRE_OPEN_END <= current_time < cls.REGULAR_START:
            return MarketSessionState.PRE_OPEN_MATCH
        elif cls.REGULAR_START <= current_time <= cls.REGULAR_END:
            return MarketSessionState.REGULAR_TRADING
        elif cls.POST_CLOSE_START <= current_time <= cls.POST_CLOSE_END:
            return MarketSessionState.CLOSING_SESSION
        else:
            return MarketSessionState.CLOSED

    @classmethod
    def is_market_open(cls, dt: datetime | None = None) -> bool:
        """Check if regular trading is currently active."""
        return cls.get_session_state(dt) == MarketSessionState.REGULAR_TRADING
