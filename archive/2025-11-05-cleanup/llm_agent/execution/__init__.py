"""
Trade execution module for LLM trading agent

Components (Phase 3):
- TradeExecutor: Execute LLM decisions using Pacifica SDK
- RiskManager integration: Enforce position limits
- TradeTracker integration: Log all trades
"""

from .trade_executor import TradeExecutor

__all__ = ['TradeExecutor']
