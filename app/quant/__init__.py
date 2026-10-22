"""Quantitative research module — indicators, strategies, regimes, and scanners."""

from app.quant.regime import MarketRegime, MarketRegimeDetector, RegimeAssessment
from app.quant.scanner import (
    DEFAULT_NSE_UNIVERSE,
    NSE_SECTORS,
    IntradaySetupRecord,
    ScannerResult,
    SetupStatus,
    WholeMarketScanner,
    IntradaySetupStore,
    get_setup_store,
)
from app.quant.strategies.base import (
    BaseStrategy,
    Signal,
    SignalDirection,
    StrategyParameters,
    StrategyResult,
)
from app.quant.strategies.momentum import MomentumBreakoutParameters, MomentumBreakoutStrategy
from app.quant.strategies.orb import OpeningRangeBreakoutStrategy, ORBParameters
from app.quant.strategies.relative_strength import (
    RelativeStrengthParameters,
    RelativeStrengthStrategy,
)
from app.quant.strategies.sma_crossover import SMACrossoverParams, SMACrossoverStrategy
from app.quant.strategies.vwap_pullback import VWAPPullbackParameters, VWAPPullbackStrategy

__all__ = [
    "MarketRegime",
    "MarketRegimeDetector",
    "RegimeAssessment",
    "DEFAULT_NSE_UNIVERSE",
    "NSE_SECTORS",
    "IntradaySetupRecord",
    "ScannerResult",
    "SetupStatus",
    "WholeMarketScanner",
    "IntradaySetupStore",
    "get_setup_store",
    "BaseStrategy",
    "Signal",
    "SignalDirection",
    "StrategyParameters",
    "StrategyResult",
    "OpeningRangeBreakoutStrategy",
    "ORBParameters",
    "SMACrossoverStrategy",
    "SMACrossoverParams",
    "VWAPPullbackStrategy",
    "VWAPPullbackParameters",
    "MomentumBreakoutStrategy",
    "MomentumBreakoutParameters",
    "RelativeStrengthStrategy",
    "RelativeStrengthParameters",
]
