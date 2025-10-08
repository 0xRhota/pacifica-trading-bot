"""Base strategy interface"""
from abc import ABC, abstractmethod
from typing import Optional, Tuple


class BaseStrategy(ABC):
    """Abstract base class for trading strategies"""

    @abstractmethod
    def should_open_position(self, symbol: str, current_price: float,
                            orderbook: dict, account: dict) -> Tuple[bool, Optional[str]]:
        """
        Determine if should open position

        Args:
            symbol: Trading symbol
            current_price: Current market price
            orderbook: Orderbook data
            account: Account info (balance, equity, etc)

        Returns:
            (should_open, side) where side is 'bid' for long or 'ask' for short
        """
        pass

    @abstractmethod
    def should_close_position(self, trade: dict, current_price: float,
                             time_held: float) -> Tuple[bool, str]:
        """
        Determine if should close position

        Args:
            trade: Trade data from tracker
            current_price: Current market price
            time_held: Seconds position has been held

        Returns:
            (should_close, reason)
        """
        pass

    @abstractmethod
    def get_position_size(self, symbol: str, current_price: float,
                         account: dict) -> float:
        """
        Calculate position size

        Args:
            symbol: Trading symbol
            current_price: Current market price
            account: Account info

        Returns:
            Position size in base units
        """
        pass
