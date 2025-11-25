"""
VWAP + Orderbook Strategy - Long and Short
6 symbols, both directions, high volume
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional, Tuple
from strategies.base_strategy import BaseStrategy
from utils.vwap import calculate_session_vwap
from config import BotConfig
import random
import math


class VWAPStrategy(BaseStrategy):
    """
    VWAP + Orderbook Strategy

    LONG Setup:
    - Price > VWAP (bullish bias)
    - Bid/Ask ratio > 1.3x (buying pressure)

    SHORT Setup:
    - Price < VWAP (bearish bias)
    - Ask/Bid ratio > 1.3x (selling pressure)

    Features:
    - Session VWAP (resets at midnight UTC)
    - Real-time orderbook signals
    - Both long and short trades
    """

    def __init__(self, imbalance_threshold: float = 1.3):
        self.imbalance_threshold = imbalance_threshold
        self.vwap_cache = {}  # Cache VWAP values (recalc every check)
        print(f"✅ VWAPStrategy initialized")
        print(f"   Imbalance threshold: {imbalance_threshold}x")
        print(f"   Trading: LONG and SHORT")

    def _analyze_market_direction(self, symbol: str, current_price: float,
                                  orderbook: dict) -> Optional[str]:
        """
        Analyze market using VWAP + orderbook

        Returns:
            'bid' for long, 'ask' for short, None for skip
        """
        try:
            # Get VWAP
            vwap = calculate_session_vwap(symbol)

            if vwap is None:
                print(f"⚠️  {symbol}: No VWAP, skipping")
                return None

            # Store in cache for position management
            self.vwap_cache[symbol] = vwap

            # Validate orderbook
            if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
                print(f"⚠️  {symbol}: No orderbook data")
                return None

            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])

            if len(bids) < 10 or len(asks) < 10:
                print(f"⚠️  {symbol}: Orderbook too thin")
                return None

            # Calculate orderbook depth (top 10 levels)
            bid_depth = sum(float(bid[1]) for bid in bids[:10])
            ask_depth = sum(float(ask[1]) for ask in asks[:10])

            if ask_depth == 0 or bid_depth == 0:
                print(f"⚠️  {symbol}: Zero depth")
                return None

            # Calculate imbalance ratios
            bid_ask_ratio = bid_depth / ask_depth
            ask_bid_ratio = ask_depth / bid_depth

            # Calculate spread
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            spread_pct = (best_ask - best_bid) / best_bid * 100

            # Determine VWAP bias
            price_vs_vwap = (current_price - vwap) / vwap * 100

            if current_price > vwap:
                bias = "BULLISH"
            else:
                bias = "BEARISH"

            # Log analysis
            print(f"📊 {symbol} @ ${current_price:.4f}")
            print(f"   VWAP: ${vwap:.4f} ({price_vs_vwap:+.2f}%) → {bias}")
            print(f"   Bid depth: {bid_depth:.2f} | Ask depth: {ask_depth:.2f}")
            print(f"   Bid/Ask: {bid_ask_ratio:.3f}x | Ask/Bid: {ask_bid_ratio:.3f}x")
            print(f"   Spread: {spread_pct:.4f}%")

            # LONG Setup: Price > VWAP + Strong buying pressure
            if current_price > vwap and bid_ask_ratio > self.imbalance_threshold:
                print(f"🟢 {symbol} LONG SIGNAL (bullish + {bid_ask_ratio:.2f}x buy pressure)")
                return "bid"

            # SHORT Setup: Price < VWAP + Strong selling pressure
            elif current_price < vwap and ask_bid_ratio > self.imbalance_threshold:
                print(f"🔴 {symbol} SHORT SIGNAL (bearish + {ask_bid_ratio:.2f}x sell pressure)")
                return "ask"

            # No clear signal
            else:
                print(f"⚪ {symbol} NEUTRAL (no confluence)")
                return None

        except Exception as e:
            print(f"❌ {symbol} analysis error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def should_open_position(self, symbol: str, current_price: float,
                            orderbook: dict, account: dict) -> Tuple[bool, Optional[str]]:
        """
        Determine if should open position and which direction

        Returns:
            (should_open, side) where side is 'bid' for long or 'ask' for short
        """
        direction = self._analyze_market_direction(symbol, current_price, orderbook)

        if direction is None:
            return False, None

        return True, direction

    def should_close_position(self, trade: dict, current_price: float,
                             time_held: float) -> Tuple[bool, str]:
        """
        Ladder take-profit system:
        - First exit at +1.5%
        - Second exit at +2.5%
        - Stop loss at -1%
        - Max hold: 60 minutes

        Returns:
            (should_close, reason)
        """
        entry_price = trade['entry_price']
        side = trade['side']

        # Calculate P&L percentage
        if side == "buy":  # Long
            pnl_pct = (current_price - entry_price) / entry_price
        else:  # Short
            pnl_pct = (entry_price - current_price) / entry_price

        # Ladder take-profit levels
        if pnl_pct >= 0.025:  # +2.5%
            return True, f"Take profit L2: {pnl_pct:.4%}"

        if pnl_pct >= 0.015:  # +1.5%
            return True, f"Take profit L1: {pnl_pct:.4%}"

        # Stop loss
        if pnl_pct <= -0.01:  # -1%
            return True, f"Stop loss: {pnl_pct:.4%}"

        # Time limit
        if time_held > 60 * 60:  # 60 minutes
            return True, f"Time limit: {time_held/60:.1f}min (P&L: {pnl_pct:.4%})"

        return False, ""

    def get_position_size(self, symbol: str, current_price: float,
                         account: dict) -> float:
        """
        Fixed position size: $20 per trade

        Returns:
            Size in base units (tokens)
        """
        position_value = 20.0  # Fixed $20 per trade

        size = position_value / current_price

        # Whole number tokens for certain symbols
        whole_number_tokens = ["PENGU", "XPL", "ASTER"]
        if symbol in whole_number_tokens:
            size = math.ceil(size)
        else:
            # Use lot size from config
            lot_size = getattr(BotConfig, 'LOT_SIZE', 0.01)
            size = math.ceil(size / lot_size) * lot_size

        return size
