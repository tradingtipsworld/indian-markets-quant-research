"""Application exception hierarchy.

All platform exceptions inherit from PlatformError.
This enables consistent error handling and API responses.
"""

from __future__ import annotations


class PlatformError(Exception):
    """Base exception for all platform errors."""

    def __init__(self, message: str, *, code: str = "PLATFORM_ERROR", details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


# --- Configuration Errors ---

class ConfigurationError(PlatformError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="CONFIGURATION_ERROR", **kwargs)


# --- Data Errors ---

class DataError(PlatformError):
    """Base class for market data errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="DATA_ERROR", **kwargs)


class DataNotFoundError(DataError):
    """Requested market data was not found."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="DATA_NOT_FOUND", **kwargs)


class DataValidationError(DataError):
    """Market data failed validation checks."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="DATA_VALIDATION_ERROR", **kwargs)


class DataProviderError(DataError):
    """Error communicating with a data provider."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="DATA_PROVIDER_ERROR", **kwargs)


class StaleDataError(DataError):
    """Market data freshness exceeded threshold."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="STALE_DATA_ERROR", **kwargs)


class InvalidSessionError(DataError):
    """Action attempted outside valid market session boundaries."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="INVALID_SESSION_ERROR", **kwargs)


class DataGapError(DataError):
    """Critical gaps detected in chronological price bars."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="DATA_GAP_ERROR", **kwargs)


# --- Strategy Errors ---

class StrategyError(PlatformError):
    """Error in strategy execution or configuration."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="STRATEGY_ERROR", **kwargs)


# --- Risk Errors ---

class RiskError(PlatformError):
    """Base class for risk engine errors."""

    def __init__(self, message: str, *, code: str = "RISK_ERROR", **kwargs):
        super().__init__(message, code=code, **kwargs)


class RiskLimitExceededError(RiskError):
    """A risk limit was exceeded and the action was rejected."""

    def __init__(self, message: str, *, check_name: str = "", **kwargs):
        details = kwargs.pop("details", {})
        details["check_name"] = check_name
        super().__init__(message, code="RISK_LIMIT_EXCEEDED", details=details, **kwargs)


class KillSwitchActiveError(RiskError):
    """The kill switch is active — all trading is halted."""

    def __init__(self, message: str = "Kill switch is active. All trading halted.", **kwargs):
        super().__init__(message, code="KILL_SWITCH_ACTIVE", **kwargs)


# --- Portfolio Errors ---

class PortfolioError(PlatformError):
    """Error in portfolio or paper trading operations."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="PORTFOLIO_ERROR", **kwargs)


class InsufficientFundsError(PortfolioError):
    """Insufficient cash to execute the order."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="INSUFFICIENT_FUNDS", **kwargs)


# --- Agent Errors ---

class AgentError(PlatformError):
    """Error in AI agent execution."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="AGENT_ERROR", **kwargs)


class AgentProviderError(AgentError):
    """Error communicating with an AI provider."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="AGENT_PROVIDER_ERROR", **kwargs)


# --- Backtesting Errors ---

class BacktestError(PlatformError):
    """Error during backtesting."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="BACKTEST_ERROR", **kwargs)


class LookAheadBiasError(BacktestError):
    """Potential look-ahead bias detected in backtest."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="LOOKAHEAD_BIAS", **kwargs)


# --- Auth Errors (future) ---

class AuthenticationError(PlatformError):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication required.", **kwargs):
        super().__init__(message, code="AUTHENTICATION_ERROR", **kwargs)


class AuthorizationError(PlatformError):
    """User lacks permission for this action."""

    def __init__(self, message: str = "Insufficient permissions.", **kwargs):
        super().__init__(message, code="AUTHORIZATION_ERROR", **kwargs)
