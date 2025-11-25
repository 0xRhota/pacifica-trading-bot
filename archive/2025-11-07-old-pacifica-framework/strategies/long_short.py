"""Intelligent long/short strategy - Makes directional decisions"""
import math
import random
from typing import Optional, Tuple
from .base_strategy import BaseStrategy
from config import BotConfig


class LongShortStrategy(BaseStrategy):
    """
    Intelligent long/short strategy:
    - Analyzes market conditions to decide long vs short
    - Uses REAL-TIME Pacifica orderbook imbalance as signal
    - Same position sizing and risk management as basic strategy
    - Can go both long (bid) and short (ask)
    """

    def __init__(self):
        """Initialize strategy with data sources"""
        print("✅ LongShortStrategy initialized with Pacifica orderbook analysis")

    def _analyze_market_direction(self, symbol: str, current_price: float,
                                  orderbook: dict) -> Optional[str]:
        """
        Analyze market to determine if should go long or short
        Uses ENHANCED Pacifica orderbook analysis with quality filters

        Args:
            symbol: Trading symbol
            current_price: Current market price
            orderbook: Orderbook data (REAL-TIME from Pacifica)

        Returns:
            'bid' for long, 'ask' for short, or None for no position
        """
        try:
            # Validate orderbook data
            if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
                print(f"⚠️  No orderbook data for {symbol}, skipping trade")
                return None

            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])

            if len(bids) < 10 or len(asks) < 10:
                print(f"⚠️  {symbol} orderbook too thin, skipping trade")
                return None

            # Calculate best bid/ask and spread
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            spread_pct = (best_ask - best_bid) / best_bid * 100

            # FILTER 1: Spread quality check (avoid low liquidity)
            if spread_pct > BotConfig.MAX_SPREAD_PCT:
                print(f"⚠️  {symbol} spread too wide ({spread_pct:.4f}% > {BotConfig.MAX_SPREAD_PCT}%), skipping")
                return None

            # Calculate weighted orderbook depth (closer orders = stronger signal)
            if BotConfig.WEIGHTED_DEPTH:
                bid_depth = 0
                ask_depth = 0
                for i, (bid, ask) in enumerate(zip(bids[:10], asks[:10])):
                    # Weight decreases with distance from best price
                    weight = 1.0 / (1 + i * 0.2)  # 1.0, 0.83, 0.71, 0.63...
                    bid_depth += float(bid[1]) * weight
                    ask_depth += float(ask[1]) * weight
            else:
                # Simple sum (original method)
                bid_depth = sum(float(bid[1]) for bid in bids[:10])
                ask_depth = sum(float(ask[1]) for ask in asks[:10])

            # FILTER 2: Order count check (detect manipulation)
            bid_order_count = sum(1 for bid in bids[:10] if float(bid[1]) > 0)
            ask_order_count = sum(1 for ask in asks[:10] if float(ask[1]) > 0)

            if bid_order_count < BotConfig.MIN_ORDER_COUNT or ask_order_count < BotConfig.MIN_ORDER_COUNT:
                print(f"⚠️  {symbol} too few orders (bids: {bid_order_count}, asks: {ask_order_count}), skipping")
                return None

            # Calculate imbalance ratio
            if ask_depth == 0:
                print(f"⚠️  {symbol} no ask depth, skipping trade")
                return None

            imbalance_ratio = bid_depth / ask_depth

            # Log the analysis
            print(f"📊 {symbol} Orderbook Analysis:")
            print(f"   Bid Depth (weighted): {bid_depth:.2f}")
            print(f"   Ask Depth (weighted): {ask_depth:.2f}")
            print(f"   Imbalance Ratio: {imbalance_ratio:.4f}")
            print(f"   Spread: {spread_pct:.4f}%")
            print(f"   Orders: {bid_order_count} bids, {ask_order_count} asks")

            # Strong buying pressure (more bids than asks) → go long
            if imbalance_ratio > 1.3:
                print(f"🟢 {symbol} BULLISH signal (ratio {imbalance_ratio:.4f}) → Going LONG")
                return "bid"

            # Strong selling pressure (more asks than bids) → go short
            elif imbalance_ratio < 0.7:
                print(f"🔴 {symbol} BEARISH signal (ratio {imbalance_ratio:.4f}) → Going SHORT")
                return "ask"

            # Neutral → skip trade
            else:
                print(f"⚪ {symbol} NEUTRAL signal (ratio {imbalance_ratio:.4f}) → Skipping")
                return None

        except Exception as e:
            print(f"❌ Error analyzing {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return None  # Skip on error

    def should_open_position(self, symbol: str, current_price: float,
                            orderbook: dict, account: dict) -> Tuple[bool, Optional[str]]:
        """
        Determine if should open position and which direction

        Returns:
            (should_open, side) where side is 'bid' for long or 'ask' for short
        """
        # Basic validation
        if not orderbook or "bids" not in orderbook or "asks" not in orderbook:
            return False, None

        # Analyze market to get directional bias
        direction = self._analyze_market_direction(symbol, current_price, orderbook)

        if direction is None:
            return False, None

        return True, direction

    def should_close_position(self, trade: dict, current_price: float,
                             time_held: float) -> Tuple[bool, str]:
        """
        Close on ladder take-profit or stop-loss
        No time limit - let winners run!

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

        # Stop loss (always check first)
        if pnl_pct <= -BotConfig.MAX_LOSS_THRESHOLD:
            return True, f"Stop loss: {pnl_pct:.4%}"

        # Ladder take-profit system
        if BotConfig.USE_LADDER_TP:
            # Check which ladder level we've hit
            for level_pct in reversed(BotConfig.LADDER_TP_LEVELS):  # Check highest first
                if pnl_pct >= level_pct:
                    return True, f"Ladder TP L{BotConfig.LADDER_TP_LEVELS.index(level_pct)+1}: {pnl_pct:.4%}"
        else:
            # Simple take-profit (legacy)
            if pnl_pct >= BotConfig.MIN_PROFIT_THRESHOLD:
                return True, f"Take profit: {pnl_pct:.4%}"

        # Time limit (only if configured)
        if BotConfig.MAX_POSITION_HOLD_TIME is not None and time_held > BotConfig.MAX_POSITION_HOLD_TIME:
            return True, f"Time limit: {time_held/60:.1f}min"

        return False, ""

    def get_position_size(self, symbol: str, current_price: float,
                         account: dict) -> float:
        """
        Calculate position size - same as basic strategy

        Returns:
            Size in base units (tokens)
        """
        # Random position value
        position_value = random.uniform(
            BotConfig.MIN_POSITION_SIZE_USD,
            BotConfig.MAX_POSITION_SIZE_USD
        )

        size = position_value / current_price

        # Symbol-specific lot sizes
        if symbol in ["PENGU", "XPL", "ASTER"]:
            # Whole number tokens (lot size 1)
            size = math.ceil(size)
        elif symbol == "BTC":
            # BTC uses 0.001 lot size
            size = math.ceil(size / 0.001) * 0.001
        else:
            # SOL, ETH use 0.01 lot size
            size = math.ceil(size / BotConfig.LOT_SIZE) * BotConfig.LOT_SIZE

        return size
