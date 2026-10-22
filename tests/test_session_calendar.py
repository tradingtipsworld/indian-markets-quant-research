"""Unit tests for Indian Market Calendar and IST Session Validation."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.data.session import IndianMarketCalendar, MarketSessionState, IST_TIMEZONE


def test_market_calendar_trading_days():
    # Regular Wednesday
    wed = date(2026, 4, 15)
    assert IndianMarketCalendar.is_trading_day(wed) is True

    # Weekend (Sunday)
    sun = date(2026, 4, 19)
    assert IndianMarketCalendar.is_trading_day(sun) is False

    # Republic Day holiday (Jan 26, 2026)
    republic_day = date(2026, 1, 26)
    assert IndianMarketCalendar.is_trading_day(republic_day) is False


def test_market_session_states():
    # Regular trading hours: 10:30 AM IST on trading day
    trading_time = datetime(2026, 4, 15, 10, 30, tzinfo=IST_TIMEZONE)
    state = IndianMarketCalendar.get_session_state(trading_time)
    assert state == MarketSessionState.REGULAR_TRADING
    assert IndianMarketCalendar.is_market_open(trading_time) is True

    # Pre-open session: 09:05 AM IST
    pre_open_time = datetime(2026, 4, 15, 9, 5, tzinfo=IST_TIMEZONE)
    assert IndianMarketCalendar.get_session_state(pre_open_time) == MarketSessionState.PRE_OPEN
    assert IndianMarketCalendar.is_market_open(pre_open_time) is False

    # After-market closed: 08:00 PM IST
    night_time = datetime(2026, 4, 15, 20, 0, tzinfo=IST_TIMEZONE)
    assert IndianMarketCalendar.get_session_state(night_time) == MarketSessionState.CLOSED
    assert IndianMarketCalendar.is_market_open(night_time) is False
