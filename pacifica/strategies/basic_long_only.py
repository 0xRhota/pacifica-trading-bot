"""Basic long-only strategy - Original working strategy"""
import math
import random
from typing import Optional, Tuple
from .base_strategy import BaseStrategy
from config import BotConfig


class BasicLongOnlyStrategy(BaseStrategy):
    """
    Simple long-only strategy:
    - Randomly picks symbols from allowed list
    - Always goes long (bid/buy)
    - Fixed position sizing ($10-20)
    - Closes on take-profit, stop-loss, or time limit
    """

    def should_open_position(self, symbol: str, current_price: float,
                            orderbook: dict, account: dict) -> Tuple[bool, Optional[str]]:
        """
        Always returns True for opening, always goes long

        Returns:
            (True, 'bid') to open long position
        """
        # Simple check: make sure we have orderbook data
        if not orderbook or "bids" not in orderbook:
            return False, None

        # Always open long positions
        return True, "bid"

    def should_close_position(self, trade: dict, current_price: float,
                             time_held: float) -> Tuple[bool, str]:
        """
        Close on take-profit, stop-loss, or time limit

        Returns:
            (should_close, reason)
        """
        entry_price = trade['entry_price']
        side = trade['side']

        # Calculate P&L percentage
        if side == "buy":
            pnl_pct = (current_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - current_price) / entry_price

        # Take profit
        if pnl_pct >= BotConfig.MIN_PROFIT_THRESHOLD:
            return True, f"Take profit: {pnl_pct:.4%}"

        # Stop loss
        if pnl_pct <= -BotConfig.MAX_LOSS_THRESHOLD:
            return True, f"Stop loss: {pnl_pct:.4%}"

        # Time limit
        if time_held > BotConfig.MAX_POSITION_HOLD_TIME:
            return True, f"Time limit: {time_held/60:.1f}min"

        return False, ""

    def get_position_size(self, symbol: str, current_price: float,
                         account: dict) -> float:
        """
        Calculate position size - random between min/max

        Returns:
            Size in base units (tokens)
        """
        # Random position value
        position_value = random.uniform(
            BotConfig.MIN_POSITION_SIZE_USD,
            BotConfig.MAX_POSITION_SIZE_USD
        )

        size = position_value / current_price

        # Some tokens require whole numbers (lot size 1)
        whole_number_tokens = ["PENGU", "XPL", "ASTER", "BTC"]
        if symbol in whole_number_tokens:
            size = math.ceil(size)
        else:
            size = math.ceil(size / BotConfig.LOT_SIZE) * BotConfig.LOT_SIZE

        return size
