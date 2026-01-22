#!/usr/bin/env python3
"""
Grid Market Maker for Hibachi DEX
High-volume limit order strategy to farm early platform points

Strategy: Place limit orders on both sides of mid price
- Uses LIMIT orders (maker) to get 0% fee vs 0.045% taker
- Wide spread (20 bps) to ensure orders rest on book since no POST_ONLY
- ROC threshold for trend detection (pause in volatile markets)
- Conservative sizing for $60 balance

Hibachi Fee Structure:
- Maker: 0.000% (FREE!)
- Taker: 0.045%
- Goal: Farm volume with limit orders for points + zero fees

Parameters (aggressive volume farming):
- Asset: BTC-PERP (lower volatility than ETH)
- Spread: 20 bps (wide since no POST_ONLY)
- Order Size: $50 per order (matches Nado style)
- Levels: 3 per side ($150 per side)
- Refresh: 30 seconds
"""

import os
import sys
import time
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
from collections import deque

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load env
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key] = val.strip('"').strip("'")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

from dexes.hibachi.hibachi_sdk import HibachiSDK


class HibachiGridMM:
    """
    Grid Market Maker for Hibachi DEX
    Places limit orders on both sides for volume farming + spread capture
    """

    def __init__(
        self,
        symbol: str = "BTC/USDT-P",
        base_spread_bps: float = 20.0,      # Wide spread since no POST_ONLY
        order_size_usd: float = 100.0,      # $100 orders (matches Nado)
        num_levels: int = 3,                # 3 levels per side = $150 per side
        max_position_usd: float = 250.0,    # Max $250 position (reduced to share margin with LLM Supervisor)
        roc_threshold_bps: float = 10.0,    # Pause on trend
        min_pause_duration: int = 20,       # 20 second pause
        refresh_interval: float = 30.0,     # Refresh grid every 30 seconds
    ):
        self.symbol = symbol
        self.base_spread_bps = base_spread_bps
        self.order_size_usd = order_size_usd
        self.num_levels = num_levels
        self.max_position_usd = max_position_usd
        self.roc_threshold_bps = roc_threshold_bps
        self.min_pause_duration = min_pause_duration
        self.refresh_interval = refresh_interval

        # State
        self.sdk: Optional[HibachiSDK] = None
        self.price_history: deque = deque(maxlen=30)
        self.open_orders: Dict[str, Dict] = {}

        # Trend detection
        self.orders_paused = False
        self.pause_side = None
        self.pause_start_time = None

        # Stats
        self.total_volume = 0.0
        self.fills_count = 0
        self.start_time = None
        self.initial_balance = 0.0

        # Market info (BTC)
        self.tick_size = 0.1  # BTC tick size on Hibachi
        self.min_size = 0.0001  # ~$9 at 90k
        self.min_notional = 1.0  # $1 min notional

    async def initialize(self):
        """Initialize Hibachi SDK and get market info"""
        logger.info("=" * 70)
        logger.info("HIBACHI GRID MARKET MAKER - VOLUME FARMING")
        logger.info("=" * 70)
        logger.info(f"Symbol: {self.symbol}")
        logger.info(f"Spread: {self.base_spread_bps} bps (wide - no POST_ONLY)")
        logger.info(f"Order Size: ${self.order_size_usd}")
        logger.info(f"Levels: {self.num_levels} per side")
        logger.info(f"Max Position: ${self.max_position_usd}")
        logger.info(f"ROC Threshold: {self.roc_threshold_bps} bps")
        logger.info(f"Refresh Interval: {self.refresh_interval}s")
        logger.info(f"Fees: 0% maker / 0.045% taker")
        logger.info("=" * 70)

        # Initialize SDK
        api_key = os.getenv('HIBACHI_PUBLIC_KEY')
        api_secret = os.getenv('HIBACHI_PRIVATE_KEY')
        account_id = os.getenv('HIBACHI_ACCOUNT_ID')

        if not api_key or not api_secret or not account_id:
            raise ValueError("HIBACHI_PUBLIC_KEY, HIBACHI_PRIVATE_KEY, HIBACHI_ACCOUNT_ID required")

        self.sdk = HibachiSDK(api_key, api_secret, account_id)

        # Get balance
        balance = await self.sdk.get_balance()
        self.initial_balance = balance or 0
        logger.info(f"Account balance: ${self.initial_balance:.2f}")

        # Get market info
        market_info = await self.sdk.get_market_info(self.symbol)
        if market_info:
            self.tick_size = float(market_info.get('tickSize', 0.1))
            self.min_size = float(market_info.get('minOrderSize', 0.0001))
            self.min_notional = float(market_info.get('minNotional', 1.0))
            logger.info(f"Market: tick={self.tick_size}, min_size={self.min_size}, min_notional=${self.min_notional}")

        # Get initial price
        mid = await self._get_mid_price()
        if not mid:
            raise Exception("Cannot get initial price")
        logger.info(f"Initial price: ${mid:,.2f}")
        self.price_history.append(mid)

        self.start_time = datetime.now()
        return True

    async def _get_mid_price(self) -> Optional[float]:
        """Get current mid price from Hibachi"""
        try:
            orderbook = await self.sdk.get_orderbook(self.symbol)
            if not orderbook:
                return None

            bid_levels = orderbook.get('bid', {}).get('levels', [])
            ask_levels = orderbook.get('ask', {}).get('levels', [])

            if not bid_levels or not ask_levels:
                return None

            best_bid = float(bid_levels[0]['price'])
            best_ask = float(ask_levels[0]['price'])
            return (best_bid + best_ask) / 2
        except Exception as e:
            logger.error(f"Error getting mid price: {e}")
        return None

    def _round_price(self, price: float) -> float:
        """Round price to tick size"""
        ticks = round(price / self.tick_size)
        return round(ticks * self.tick_size, 6)

    def _round_size(self, size: float, price: float) -> float:
        """Round size to step size, ensuring min_notional is met"""
        # Ensure notional >= min_notional (with 10% buffer)
        min_size_for_notional = (self.min_notional * 1.1) / price
        size = max(size, min_size_for_notional, self.min_size)

        # Round to 4 decimal places for BTC
        return round(size, 4)

    def _calculate_roc(self) -> float:
        """Calculate Rate of Change in bps over ~30 samples"""
        if len(self.price_history) < 10:
            return 0.0
        prices = list(self.price_history)
        current = prices[-1]
        past = prices[-10]
        if past == 0:
            return 0.0
        return (current - past) / past * 10000

    def _calculate_dynamic_spread(self, roc: float) -> float:
        """
        Calculate dynamic spread based on ROC (volatility).

        HIB-003 (2026-01-22): Reduced spreads by 20% for more fills.
        Analysis showed orders being cancelled before fills with 10-25 bps.
        CLAUDE.md confirms: "Wider Grid MM spreads DON'T work (v2-v4 proved it)"

        Spread bands (reduced 20% from previous):
        | ROC (abs) | Spread | Rationale |
        |-----------|--------|-----------|
        | 0-5 bps   | 8 bps  | Calm market, tight for fills |
        | 5-10 bps  | 12 bps | Low volatility |
        | 10-20 bps | 16 bps | Moderate volatility |
        | > 20 bps  | 20 bps | High vol, still tighter |
        """
        abs_roc = abs(roc)
        if abs_roc < 5:
            spread = 8.0   # Calm (was 10)
        elif abs_roc < 10:
            spread = 12.0  # Low vol (was 15)
        elif abs_roc < 20:
            spread = 16.0  # Moderate vol (was 20)
        else:
            spread = 20.0  # High vol (was 25)
        return spread

    def _update_pause_state(self, roc: float):
        """Update order pause state based on trend"""
        old_paused = self.orders_paused

        strong_threshold = self.roc_threshold_bps * 2.0

        if abs(roc) > strong_threshold:
            if not self.orders_paused or self.pause_side != 'ALL':
                self.pause_start_time = datetime.now()
            self.orders_paused = True
            self.pause_side = 'ALL'
            direction = "UP" if roc > 0 else "DOWN"
            if not old_paused:
                logger.warning(f"  STRONG TREND {direction} - PAUSE ALL (ROC: {roc:+.2f} bps)")
        elif roc > self.roc_threshold_bps:
            if not self.orders_paused:
                self.pause_start_time = datetime.now()
            self.orders_paused = True
            self.pause_side = 'SELL'
        elif roc < -self.roc_threshold_bps:
            if not self.orders_paused:
                self.pause_start_time = datetime.now()
            self.orders_paused = True
            self.pause_side = 'BUY'
        else:
            if self.orders_paused and self.pause_start_time:
                elapsed = (datetime.now() - self.pause_start_time).total_seconds()
                if elapsed >= self.min_pause_duration:
                    self.orders_paused = False
                    self.pause_side = None
                    if old_paused:
                        logger.info(f"  RESUME orders (ROC: {roc:+.2f} bps)")

    async def _get_position(self) -> float:
        """Get current position size in USD"""
        try:
            pos_size = await self.sdk.get_position_size(self.symbol)
            mid = await self._get_mid_price()
            if mid:
                return abs(pos_size) * mid
            return 0.0
        except Exception as e:
            logger.error(f"Error getting position: {e}")
            return 0.0

    async def _cancel_all_orders(self):
        """Cancel all open orders"""
        try:
            cancelled = await self.sdk.cancel_all_orders(self.symbol)
            self.open_orders.clear()
            return cancelled
        except Exception as e:
            logger.error(f"Cancel error: {e}")
            self.open_orders.clear()
            return 0

    async def _place_grid_orders(self, mid_price: float, roc: float = 0.0):
        """Place limit orders on both sides of mid price with dynamic spread"""
        orders_placed = 0

        # Check position limit
        current_position = await self._get_position()
        if current_position >= self.max_position_usd:
            logger.warning(f"  Max position reached: ${current_position:.2f} >= ${self.max_position_usd}")
            return 0

        # Use dynamic spread based on ROC volatility
        dynamic_spread = self._calculate_dynamic_spread(roc)

        for level in range(1, self.num_levels + 1):
            # Spread increases with level, using dynamic base spread
            spread_multiplier = level * dynamic_spread / 10000

            # Calculate order size in base currency
            size = self._round_size(self.order_size_usd / mid_price, mid_price)

            # BUY order (below mid)
            if not self.orders_paused or self.pause_side not in ['BUY', 'ALL']:
                buy_price = self._round_price(mid_price * (1 - spread_multiplier))
                try:
                    result = await self.sdk.create_limit_order(
                        symbol=self.symbol,
                        is_buy=True,
                        amount=size,
                        price=buy_price
                    )
                    if result and 'orderId' in result:
                        orders_placed += 1
                        self.open_orders[result.get('orderId', str(time.time()))] = {
                            'side': 'BUY',
                            'price': buy_price,
                            'size': size
                        }
                        logger.debug(f"  BUY {size:.4f} @ ${buy_price:,.2f}")
                except Exception as e:
                    logger.debug(f"Buy order error: {e}")

            # SELL order (above mid)
            if not self.orders_paused or self.pause_side not in ['SELL', 'ALL']:
                sell_price = self._round_price(mid_price * (1 + spread_multiplier))
                try:
                    result = await self.sdk.create_limit_order(
                        symbol=self.symbol,
                        is_buy=False,
                        amount=size,
                        price=sell_price
                    )
                    if result and 'orderId' in result:
                        orders_placed += 1
                        self.open_orders[result.get('orderId', str(time.time()))] = {
                            'side': 'SELL',
                            'price': sell_price,
                            'size': size
                        }
                        logger.debug(f"  SELL {size:.4f} @ ${sell_price:,.2f}")
                except Exception as e:
                    logger.debug(f"Sell order error: {e}")

        return orders_placed

    async def run_cycle(self):
        """Run one grid cycle"""
        # Get current price
        mid = await self._get_mid_price()
        if not mid:
            logger.warning("Cannot get price, skipping cycle")
            return

        self.price_history.append(mid)

        # Calculate ROC and update pause state
        roc = self._calculate_roc()
        self._update_pause_state(roc)

        # Cancel existing orders
        await self._cancel_all_orders()

        # Place new grid with dynamic spread
        if not self.orders_paused or self.pause_side != 'ALL':
            orders_placed = await self._place_grid_orders(mid, roc)
            dynamic_spread = self._calculate_dynamic_spread(roc)
            pause_info = f" (paused: {self.pause_side})" if self.orders_paused else ""
            logger.info(
                f"Grid @ ${mid:,.2f} | ROC: {roc:+.2f} bps | Spread: {dynamic_spread:.0f} bps | "
                f"Orders: {orders_placed}{pause_info}"
            )
        else:
            logger.info(f"Grid PAUSED @ ${mid:,.2f} | ROC: {roc:+.2f} bps")

    async def run(self):
        """Main run loop"""
        logger.info("Starting Hibachi Grid MM loop...")
        logger.info(f"Refresh every {self.refresh_interval}s")

        cycle_count = 0
        while True:
            try:
                await self.run_cycle()
                cycle_count += 1

                # Log stats every 30 cycles
                if cycle_count % 30 == 0:
                    elapsed = (datetime.now() - self.start_time).total_seconds() / 60
                    balance = await self.sdk.get_balance() or 0
                    pnl = balance - self.initial_balance
                    logger.info(
                        f"Stats: {cycle_count} cycles in {elapsed:.1f} min | "
                        f"Balance: ${balance:.2f} | PnL: ${pnl:+.2f}"
                    )

                await asyncio.sleep(self.refresh_interval)

            except KeyboardInterrupt:
                logger.info("Shutting down...")
                await self._cancel_all_orders()
                break
            except Exception as e:
                logger.error(f"Cycle error: {e}")
                await asyncio.sleep(5)

    async def shutdown(self):
        """Clean shutdown"""
        logger.info("Cancelling all orders...")
        await self._cancel_all_orders()
        logger.info("Shutdown complete")


async def main():
    """Main entry point"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', default='BTC/USDT-P', help='Trading symbol')
    parser.add_argument('--spread', type=float, default=20.0, help='Spread in bps (20 recommended for no POST_ONLY)')
    parser.add_argument('--size', type=float, default=100.0, help='Order size in USD')
    parser.add_argument('--levels', type=int, default=3, help='Levels per side')
    parser.add_argument('--refresh', type=float, default=30.0, help='Refresh interval')
    parser.add_argument('--max-position', type=float, default=500.0, help='Max position in USD')
    args = parser.parse_args()

    mm = HibachiGridMM(
        symbol=args.symbol,
        base_spread_bps=args.spread,
        order_size_usd=args.size,
        num_levels=args.levels,
        refresh_interval=args.refresh,
        max_position_usd=args.max_position,
    )

    try:
        await mm.initialize()
        await mm.run()
    except KeyboardInterrupt:
        pass
    finally:
        await mm.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
