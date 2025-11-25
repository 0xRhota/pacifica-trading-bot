"""Base DEX Adapter Interface - Defines contract for all DEX adapters"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class BaseAdapter(ABC):
    """Abstract base class for all DEX adapters"""
    
    @abstractmethod
    async def initialize(self):
        """Initialize adapter and fetch markets"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return adapter name (e.g., 'pacifica', 'lighter')"""
        pass
    
    @abstractmethod
    async def get_markets(self) -> List[Dict]:
        """Get all available markets from exchange"""
        pass
    
    @abstractmethod
    def get_market_id(self, symbol: str) -> Optional[int]:
        """Get market_id for symbol"""
        pass
    
    @abstractmethod
    def get_symbol(self, market_id: int) -> Optional[str]:
        """Get symbol for market_id"""
        pass
    
    @abstractmethod
    def get_active_markets(self) -> List[str]:
        """Get list of active market symbols"""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Dict]:
        """Get open positions with correct symbol mapping"""
        pass
    
    @abstractmethod
    async def get_balance(self) -> float:
        """Get account balance"""
        pass
    
    @abstractmethod
    async def place_order(self, symbol: str, side: str, amount: float, reduce_only: bool = False) -> Dict:
        """Place order"""
        pass
    
    @abstractmethod
    async def get_market_data(self, symbol: str) -> Optional[Dict]:
        """Get market data for symbol (OHLCV, indicators, etc.)"""
        pass


