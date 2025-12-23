"""
Extended Exchange Adapter
=========================
Implements ExchangeAdapter interface for Extended DEX (Starknet).
Requires Python 3.11+ for the x10 SDK.
"""

import os
import logging
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from .base import (
    ExchangeAdapter, Position, FundingInfo, OrderResult,
    AccountBalance, Side
)

logger = logging.getLogger(__name__)


class ExtendedAdapter(ExchangeAdapter):
    """
    Extended DEX adapter for funding rate arbitrage.

    Uses the official x10-python-trading-starknet SDK.
    REQUIRES Python 3.11+
    """

    # Symbol mapping: normalized -> exchange format
    SYMBOL_MAP = {
        "BTC": "BTC-USD",
        "ETH": "ETH-USD",
        "SOL": "SOL-USD",
    }

    def __init__(self):
        self._api_key = os.getenv("EXTENDED_API_KEY")
        self._stark_private_key = os.getenv("EXTENDED_STARK_PRIVATE_KEY")
        self._stark_public_key = os.getenv("EXTENDED_STARK_PUBLIC_KEY")
        self._vault = os.getenv("EXTENDED_VAULT")
        self._trading_client = None
        self._initialized = False

    @property
    def name(self) -> str:
        return "Extended"

    @property
    def supported_symbols(self) -> List[str]:
        return list(self.SYMBOL_MAP.keys())

    async def initialize(self) -> bool:
        """Initialize Extended SDK connection"""
        try:
            # Import SDK (requires Python 3.11+)
            from x10.perpetual.accounts import StarkPerpetualAccount
            from x10.perpetual.configuration import MAINNET_CONFIG
            from x10.perpetual.trading_client import PerpetualTradingClient

            if not all([self._api_key, self._stark_private_key, self._stark_public_key, self._vault]):
                logger.error("Extended credentials not configured")
                return False

            stark_account = StarkPerpetualAccount(
                vault=int(self._vault),
                private_key=self._stark_private_key,
                public_key=self._stark_public_key,
                api_key=self._api_key,
            )

            self._trading_client = PerpetualTradingClient(
                endpoint_config=MAINNET_CONFIG,
                stark_account=stark_account
            )

            self._initialized = True
            logger.info(f"Extended adapter initialized (vault: {self._vault})")
            return True

        except ImportError as e:
            logger.error(f"Extended SDK not available (requires Python 3.11+): {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Extended adapter: {e}")
            return False

    async def close(self) -> None:
        """Clean up resources"""
        if self._trading_client:
            await self._trading_client.close()
            self._trading_client = None
            self._initialized = False

    # ===== Market Data =====

    async def get_funding_info(self, symbol: str) -> Optional[FundingInfo]:
        """Get funding rate from Extended"""
        try:
            if not self._trading_client:
                return None

            exchange_symbol = self.to_exchange_symbol(symbol)
            stats = await self._trading_client.markets_info.get_market_statistics(
                market_name=exchange_symbol
            )

            if not stats or not stats.data:
                return None

            return FundingInfo(
                symbol=symbol,
                funding_rate=float(stats.data.funding_rate),
                next_funding_time=None,  # Extended doesn't provide this easily
                mark_price=float(stats.data.mark_price)
            )

        except Exception as e:
            logger.error(f"Error fetching Extended funding info for {symbol}: {e}")
            return None

    async def get_mark_price(self, symbol: str) -> Optional[float]:
        """Get mark price from Extended"""
        funding_info = await self.get_funding_info(symbol)
        return funding_info.mark_price if funding_info else None

    # ===== Account Data =====

    async def get_balance(self) -> Optional[AccountBalance]:
        """Get account balance from Extended"""
        try:
            if not self._trading_client:
                return None

            balance = await self._trading_client.account.get_balance()
            if not balance or not balance.data:
                return None

            # x10 SDK BalanceModel uses: equity, available_margin, position_margin
            equity = float(balance.data.equity)
            available = float(balance.data.available_margin) if hasattr(balance.data, 'available_margin') else equity
            margin_used = float(balance.data.position_margin) if hasattr(balance.data, 'position_margin') else 0

            return AccountBalance(
                equity=equity,
                available_balance=available,
                margin_used=margin_used
            )

        except Exception as e:
            logger.error(f"Error fetching Extended balance: {e}")
            return None

    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol"""
        try:
            if not self._trading_client:
                return None

            positions = await self._trading_client.account.get_positions()
            if not positions or not positions.data:
                return None

            exchange_symbol = self.to_exchange_symbol(symbol)

            for pos in positions.data:
                if pos.market == exchange_symbol:
                    side_str = str(pos.side).upper()
                    side = Side.LONG if "LONG" in side_str or "BUY" in side_str else Side.SHORT
                    size = abs(float(pos.size))
                    # x10 SDK uses: open_price (entry), mark_price, unrealised_pnl (note: British spelling)
                    mark_price = float(pos.mark_price) if hasattr(pos, 'mark_price') else 0
                    entry_price = float(pos.open_price) if hasattr(pos, 'open_price') else 0

                    # Get mark price if not in position data
                    if mark_price == 0:
                        mark_price = await self.get_mark_price(symbol) or entry_price

                    notional = size * mark_price

                    return Position(
                        symbol=symbol,
                        side=side,
                        size=size,
                        entry_price=entry_price,
                        mark_price=mark_price,
                        unrealized_pnl=float(pos.unrealised_pnl) if hasattr(pos, 'unrealised_pnl') else 0,
                        notional_value=notional
                    )

            return None  # No position for this symbol

        except Exception as e:
            logger.error(f"Error fetching Extended position for {symbol}: {e}")
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
        """Open a position on Extended"""
        try:
            if not self._trading_client:
                return OrderResult(success=False, error="SDK not initialized")

            from x10.perpetual.orders import OrderSide, TimeInForce

            exchange_symbol = self.to_exchange_symbol(symbol)
            mark_price = await self.get_mark_price(symbol)
            if not mark_price:
                return OrderResult(success=False, error="Could not get mark price")

            # Calculate quantity
            quantity = Decimal(str(self.calculate_position_size(size_usd, mark_price)))

            # Extended order side
            order_side = OrderSide.BUY if side == Side.LONG else OrderSide.SELL

            # Price with slippage buffer for market-like execution
            if side == Side.LONG:
                order_price = Decimal(str(int(mark_price * 1.005)))  # 0.5% above
            else:
                order_price = Decimal(str(int(mark_price * 0.995)))  # 0.5% below

            # Place order
            order = await self._trading_client.place_order(
                market_name=exchange_symbol,
                amount_of_synthetic=quantity,
                price=order_price,
                side=order_side,
                time_in_force=TimeInForce.GTT,
                expire_time=datetime.now(timezone.utc) + timedelta(hours=1),
                reduce_only=reduce_only
            )

            if order and order.data:
                logger.info(f"Extended {side.value} {symbol}: {float(quantity):.6f} @ ~${mark_price:,.2f}")
                return OrderResult(
                    success=True,
                    order_id=str(order.data.id),
                    filled_size=float(quantity),
                    filled_price=float(mark_price)
                )
            else:
                return OrderResult(success=False, error="Order execution failed")

        except Exception as e:
            logger.error(f"Error opening Extended position: {e}")
            return OrderResult(success=False, error=str(e))

    async def close_position(self, symbol: str) -> OrderResult:
        """Close entire position for a symbol"""
        try:
            position = await self.get_position(symbol)
            if not position:
                return OrderResult(success=True)  # No position to close

            # Close by opening opposite side with reduce_only
            opposite_side = Side.SHORT if position.side == Side.LONG else Side.LONG
            return await self.open_position(
                symbol=symbol,
                side=opposite_side,
                size_usd=position.notional_value,
                reduce_only=True
            )

        except Exception as e:
            logger.error(f"Error closing Extended position: {e}")
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
            logger.error(f"Error adjusting Extended position: {e}")
            return OrderResult(success=False, error=str(e))

    # ===== Symbol Mapping =====

    def normalize_symbol(self, exchange_symbol: str) -> str:
        """Convert Extended symbol to normalized format"""
        for normalized, extended in self.SYMBOL_MAP.items():
            if extended == exchange_symbol:
                return normalized
        return exchange_symbol

    def to_exchange_symbol(self, normalized_symbol: str) -> str:
        """Convert normalized symbol to Extended format"""
        return self.SYMBOL_MAP.get(normalized_symbol, normalized_symbol)
