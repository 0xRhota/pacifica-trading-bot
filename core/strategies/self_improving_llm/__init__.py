"""
Self-Improving LLM Strategy

A multi-dimensional self-learning system for single-asset LLM-based trading.
Tracks outcomes by symbol, direction, and confidence to identify patterns
and automatically adjust trading filters.

Components:
- OutcomeTracker: Records trade outcomes with full context
- PerformanceAnalyzer: Analyzes performance by multiple dimensions
- StrategyAdjuster: Generates dynamic filters and prompt hints
- SelfImprovingLLMStrategy: Orchestrates the full system
"""

from .outcome_tracker import OutcomeTracker, TradeOutcome
from .performance_analyzer import PerformanceAnalyzer, DimensionAnalysis
from .strategy_adjuster import StrategyAdjuster, TradeFilter
from .strategy import SelfImprovingLLMStrategy, StrategyConfig

__all__ = [
    "OutcomeTracker",
    "TradeOutcome",
    "PerformanceAnalyzer",
    "DimensionAnalysis",
    "StrategyAdjuster",
    "TradeFilter",
    "SelfImprovingLLMStrategy",
    "StrategyConfig"
]
