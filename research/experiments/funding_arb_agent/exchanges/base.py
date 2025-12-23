"""
Abstract Exchange Adapter Interface
====================================
Defines the contract that all exchange adapters must implement
for the funding rate arbitrage strategy.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict
from enum import Enum
from datetime import datetime


class Side(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class Position:
    """Represents an open position on an exchange"""
    symbol: str
    side: Side
    size: float  # Absolute size (always positive)
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    notional_value: float  # USD value of position

    @property
    def signed_size(self) -> float:
        """Positive for LONG, negative for SHORT"""
        return self.size if self.side == Side.LONG else -self.size


@dataclass
class FundingInfo:
    """Funding rate information for a market"""
    symbol: str
    funding_rate: float  # Per-period rate (typically 8h)
    next_funding_time: Optional[datetime]
    mark_price: float
    spot_price: Optional[float] = None

    @property
    def annualized_rate(self) -> float:
        """Annualized funding rate (assuming 8h periods = 1095/year)"""
        return self.funding_rate * 1095 * 100


@dataclass
class OrderResult:
    """Result of an order execution"""
    success: bool
    order_id: Optional[str] = None
    filled_size: float = 0.0
    filled_price: float = 0.0
    error: Optional[str] = None


@dataclass
class AccountBalance:
    """Account balance information"""
    equity: float  # Total equity including unrealized PnL
    available_balance: float  # Available for trading
    margin_used: float = 0.0


class ExchangeAdapter(ABC):
    """
    Abstract base class for exchange adapters.

    Each exchange adapter must implement these methods to enable
    the funding arbitrage strategy to work across different DEXes.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Exchange name for logging/display"""
        pass

    @property
    @abstractmethod
    def supported_symbols(self) -> List[str]:
        """List of supported trading symbols (normalized format)"""
        pass

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the exchange connection.
        Returns True if successful.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Clean up resources"""
        pass

    # ===== Market Data =====

    @abstractmethod
    async def get_funding_info(self, symbol: str) -> Optional[FundingInfo]:
        """
        Get current funding rate information for a symbol.

        Args:
            symbol: Normalized symbol (e.g., "BTC", "ETH", "SOL")

        Returns:
            FundingInfo or None if unavailable
        """
        pass

    @abstractmethod
    async def get_mark_price(self, symbol: str) -> Optional[float]:
        """Get current mark price for a symbol"""
        pass

    # ===== Account Data =====

    @abstractmethod
    async def get_balance(self) -> Optional[AccountBalance]:
        """Get account balance information"""
        pass

    @abstractmethod
    async def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get current position for a symbol.

        Args:
            symbol: Normalized symbol (e.g., "BTC")

        Returns:
            Position or None if no position exists
        """
        pass

    @abstractmethod
    async def get_all_positions(self) -> List[Position]:
        """Get all open positions"""
        pass

    # ===== Order Execution =====

    @abstractmethod
    async def open_position(
        self,
        symbol: str,
        side: Side,
        size_usd: float,
        reduce_only: bool = False
    ) -> OrderResult:
        """
        Open a new position or add to existing.

        Args:
            symbol: Normalized symbol
            side: LONG or SHORT
            size_usd: Position size in USD
            reduce_only: If True, only reduce existing position

        Returns:
            OrderResult with execution details
        """
        pass

    @abstractmethod
    async def close_position(self, symbol: str) -> OrderResult:
        """
        Close entire position for a symbol.

        Args:
            symbol: Normalized symbol

        Returns:
            OrderResult with execution details
        """
        pass

    @abstractmethod
    async def adjust_position(
        self,
        symbol: str,
        target_size_usd: float,
        target_side: Side
    ) -> OrderResult:
        """
        Adjust position to target size and side.

        This is the key method for rebalancing. It should:
        1. Close existing position if changing sides
        2. Adjust size to match target

        Args:
            symbol: Normalized symbol
            target_size_usd: Target position size in USD (absolute value)
            target_side: Target side (LONG or SHORT)

        Returns:
            OrderResult with execution details
        """
        pass

    # ===== Symbol Mapping =====

    @abstractmethod
    def normalize_symbol(self, exchange_symbol: str) -> str:
        """Convert exchange-specific symbol to normalized format"""
        pass

    @abstractmethod
    def to_exchange_symbol(self, normalized_symbol: str) -> str:
        """Convert normalized symbol to exchange-specific format"""
        pass

    # ===== Utility Methods =====

    def calculate_position_size(self, size_usd: float, price: float) -> float:
        """Calculate asset quantity from USD size and price"""
        if price <= 0:
            return 0.0
        return size_usd / price
