"""Base Strategy Interface - Plug & Play"""

from abc import ABC, abstractmethod
from typing import Dict, List


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies"""
    
    @abstractmethod
    async def get_decisions(self, market_data: Dict, positions: List[Dict], context: Dict) -> List[Dict]:
        """
        Get trading decisions
        
        Args:
            market_data: Dict of symbol -> market data (OHLCV, indicators, etc.)
            positions: List of open positions
            context: Additional context (balance, trade history, etc.)
        
        Returns:
            List of decision dicts with keys: action, symbol, reason, confidence
        """
        pass


