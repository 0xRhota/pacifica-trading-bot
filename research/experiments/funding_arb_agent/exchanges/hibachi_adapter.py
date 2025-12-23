"""
Hibachi Exchange Adapter
========================
Implements ExchangeAdapter interface for Hibachi DEX (Arbitrum).
"""

import os
import logging
import aiohttp
from typing import Optional, List
from datetime import datetime, timezone

from .base import (
    ExchangeAdapter, Position, FundingInfo, OrderResult,
    AccountBalance, Side
)

logger = logging.getLogger(__name__)


class HibachiAdapter(ExchangeAdapter):
    """
    Hibachi DEX adapter for funding rate arbitrage.

    Uses:
    - data-api.hibachi.xyz for market data (no auth required)
    - api.hibachi.xyz for account/trading (requires auth)
    """

    # Symbol mapping: normalized -> exchange format
    SYMBOL_MAP = {
        "BTC": "BTC/USDT-P",
        "ETH": "ETH/USDT-P",
        "SOL": "SOL/USDT-P",
    }

    def __init__(self):
        self._api_key = os.getenv("HIBACHI_PUBLIC_KEY")
        self._api_secret = os.getenv("HIBACHI_PRIVATE_KEY")
        self._account_id = os.getenv("HIBACHI_ACCOUNT_ID")
        self._data_api_url = "https://data-api.hibachi.xyz"
        self._api_url = "https://api.hibachi.xyz"
        self._session: Optional[aiohttp.ClientSession] = None
        self._sdk = None  # Will hold HibachiSDK instance

    @property
    def name(self) -> str:
        return "Hibachi"

    @property
    def supported_symbols(self) -> List[str]:
        return list(self.SYMBOL_MAP.keys())

    async def initialize(self) -> bool:
        """Initialize Hibachi connection"""
        try:
            # Import SDK
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from dexes.hibachi.hibachi_sdk import HibachiSDK

            if not all([self._api_key, self._api_secret, self._account_id]):
                logger.error("Hibachi credentials not configured")
                return False

            self._sdk = HibachiSDK(
                api_key=self._api_key,
                api_secret=self._api_secret,
                account_id=self._account_id
            )

            self._session = aiohttp.ClientSession()
            logger.info(f"Hibachi adapter initialized (account: {self._account_id})")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Hibachi adapter: {e}")
            return False

    async def close(self) -> None:
        """Clean up resources"""
        if self._session:
            await self._session.close()
            self._session = None

    # ===== Market Data =====

    async def get_funding_info(self, symbol: str) -> Optional[FundingInfo]:
        """Get funding rate from Hibachi data API"""
        try:
            exchange_symbol = self.to_exchange_symbol(symbol)
            url = f"{self._data_api_url}/market/data/prices?symbol={exchange_symbol}"

            async with self._session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Hibachi funding rate request failed: {response.status}")
                    return None

                data = await response.json()
                funding_data = data.get("fundingRateEstimation", {})

                return FundingInfo(
                    symbol=symbol,
                    funding_rate=float(funding_data.get("estimatedFundingRate", 0)),
                    next_funding_time=datetime.fromtimestamp(
                        funding_data.get("nextFundingTimestamp", 0),
                        tz=timezone.utc
                    ) if funding_data.get("nextFundingTimestamp") else None,
                    mark_price=float(data.get("markPrice", 0)),
                    spot_price=float(data.get("spotPrice", 0)) if data.get("spotPrice") else None
                )

        except Exception as e:
            logger.error(f"Error fetching Hibachi funding info for {symbol}: {e}")
            return None

    async def get_mark_price(self, symbol: str) -> Optional[float]:
        """Get mark price from Hibachi"""
        funding_info = await self.get_funding_info(symbol)
        return funding_info.mark_price if funding_info else None

    # ===== Account Data =====

    async def get_balance(self) -> Optional[AccountBalance]:
        """Get account balance from Hibachi"""
        try:
            if not self._sdk:
                return None

            balance = await self._sdk.get_balance()
            if balance is None:
                return None

            return AccountBalance(
                equity=balance,
                available_balance=balance,
                margin_used=0
            )

        except Exception as e:
            logger.error(f"Error fetching Hibachi balance: {e}")
            return None

    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol"""
        try:
            if not self._sdk:
                return None

            positions = await self._sdk.get_positions()
            if not positions:
                return None

            exchange_symbol = self.to_exchange_symbol(symbol)

            for pos in positions:
                if pos.get("symbol") == exchange_symbol:
                    direction = pos.get("direction", "").lower()
                    side = Side.LONG if direction == "long" else Side.SHORT
                    size = float(pos.get("quantity", 0))
                    notional = float(pos.get("notionalValue", 0))
                    entry_notional = float(pos.get("entryNotional", 0))
                    entry_price = entry_notional / size if size > 0 else 0

                    # Get current mark price
                    mark_price = await self.get_mark_price(symbol) or entry_price

                    return Position(
                        symbol=symbol,
                        side=side,
                        size=abs(size),
                        entry_price=entry_price,
                        mark_price=mark_price,
                        unrealized_pnl=float(pos.get("unrealizedTradingPnl", 0)),
                        notional_value=notional
                    )

            return None  # No position for this symbol

        except Exception as e:
            logger.error(f"Error fetching Hibachi position for {symbol}: {e}")
            return None

    async def get_all_positions(self) -> List[Position]:
        """Get all open positions"""
        positions = []
        for symbol in self.supported_symbols:
            pos = await self.get_position(symbol)
            if pos:
                positions.append(pos)
        return positions

    # ===== Order Execution =====

    async def open_position(
        self,
        symbol: str,
        side: Side,
        size_usd: float,
        reduce_only: bool = False
    ) -> OrderResult:
        """Open a position on Hibachi"""
        try:
            if not self._sdk:
                return OrderResult(success=False, error="SDK not initialized")

            exchange_symbol = self.to_exchange_symbol(symbol)
            mark_price = await self.get_mark_price(symbol)
            if not mark_price:
                return OrderResult(success=False, error="Could not get mark price")

            # Calculate quantity
            quantity = self.calculate_position_size(size_usd, mark_price)

            # Place order via SDK - Hibachi uses create_market_order
            is_buy = side == Side.LONG

            result = await self._sdk.create_market_order(
                symbol=exchange_symbol,
                is_buy=is_buy,
                amount=quantity
            )

            if result and result.get("orderId"):
                logger.info(f"Hibachi {side.value} {symbol}: {quantity:.6f} @ ~${mark_price:,.2f}")
                return OrderResult(
                    success=True,
                    order_id=result.get("orderId"),
                    filled_size=quantity,
                    filled_price=mark_price
                )
            else:
                error = result.get("error", "Unknown error") if result else "No response"
                return OrderResult(success=False, error=error)

        except Exception as e:
            logger.error(f"Error opening Hibachi position: {e}")
            return OrderResult(success=False, error=str(e))

    async def close_position(self, symbol: str) -> OrderResult:
        """Close entire position for a symbol"""
        try:
            position = await self.get_position(symbol)
            if not position:
                return OrderResult(success=True)  # No position to close

            # Close by opening opposite side
            opposite_side = Side.SHORT if position.side == Side.LONG else Side.LONG
            return await self.open_position(
                symbol=symbol,
                side=opposite_side,
                size_usd=position.notional_value,
                reduce_only=True
            )

        except Exception as e:
            logger.error(f"Error closing Hibachi position: {e}")
            return OrderResult(success=False, error=str(e))

    async def adjust_position(
        self,
        symbol: str,
        target_size_usd: float,
        target_side: Side
    ) -> OrderResult:
        """Adjust position to target size and side"""
        try:
            current_pos = await self.get_position(symbol)

            # No current position - just open new one
            if not current_pos:
                if target_size_usd > 0:
                    return await self.open_position(symbol, target_side, target_size_usd)
                return OrderResult(success=True)  # Nothing to do

            # Same side - adjust size
            if current_pos.side == target_side:
                size_diff = target_size_usd - current_pos.notional_value

                if abs(size_diff) < 1:  # Less than $1 difference
                    return OrderResult(success=True)  # Close enough

                if size_diff > 0:
                    # Need to increase position
                    return await self.open_position(symbol, target_side, size_diff)
                else:
                    # Need to decrease position
                    opposite_side = Side.SHORT if target_side == Side.LONG else Side.LONG
                    return await self.open_position(symbol, opposite_side, abs(size_diff), reduce_only=True)

            # Different side - close and reopen
            else:
                # First close existing
                close_result = await self.close_position(symbol)
                if not close_result.success:
                    return close_result

                # Then open new side
                if target_size_usd > 0:
                    return await self.open_position(symbol, target_side, target_size_usd)

                return OrderResult(success=True)

        except Exception as e:
            logger.error(f"Error adjusting Hibachi position: {e}")
            return OrderResult(success=False, error=str(e))

    # ===== Symbol Mapping =====

    def normalize_symbol(self, exchange_symbol: str) -> str:
        """Convert Hibachi symbol to normalized format"""
        for normalized, hibachi in self.SYMBOL_MAP.items():
            if hibachi == exchange_symbol:
                return normalized
        return exchange_symbol

    def to_exchange_symbol(self, normalized_symbol: str) -> str:
        """Convert normalized symbol to Hibachi format"""
        return self.SYMBOL_MAP.get(normalized_symbol, normalized_symbol)
