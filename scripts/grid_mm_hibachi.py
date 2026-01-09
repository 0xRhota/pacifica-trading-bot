#!/usr/bin/env python3
"""
Grid Market Maker for Hibachi DEX
Same strategy as Paradex Grid MM - place limit orders on both sides

Strategy: Place limit orders on both sides of mid price
- Earns spread when both sides fill
- Uses ROC trend detection to pause orders during strong moves
"""

import os
import sys
import time
import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, '.env'))

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
    Places limit orders on both sides to earn spread
    """

    def __init__(
        self,
        symbol: str = "ETH/USDT-P",
        base_spread_bps: float = 2.0,       # 2 bps spread (Hibachi has fees)
        order_size_usd: float = 100.0,      # $100 per order
        num_levels: int = 2,                # 2 levels per side
        max_inventory_pct: float = 300.0,   # Allow 3x leverage
        capital: float = 70.0,              # ~$70 account
        roc_threshold_bps: float = 5.0,     # Pause on 5 bps move (more conservative)
        min_pause_duration: int = 30,       # 30 second pause
    ):
        self.symbol = symbol
        self.base_spread_bps = base_spread_bps
        self.order_size_usd = order_size_usd
        self.num_levels = num_levels
        self.max_inventory_pct = max_inventory_pct
        self.capital = capital
        self.roc_threshold_bps = roc_threshold_bps
        self.min_pause_duration = min_pause_duration

        # State
        self.client = None
        self.grid_center = None
        self.open_orders: Dict[str, Dict] = {}
        self.price_history: deque = deque(maxlen=30)

        # Trend detection
        self.orders_paused = False
        self.pause_side = None
        self.pause_start_time = None

        # Stats
        self.total_volume = 0.0
        self.fills_count = 0
        self.start_time = None
        self.initial_balance = 0.0
        self.current_balance = 0.0

        # Position tracking
        self.position_size = 0.0
        self.position_notional = 0.0

        # Market info
        self.tick_size = 0.01
        self.step_size = 0.0001
        self.min_notional = 10.0

    async def initialize(self):
        """Initialize Hibachi client"""
        logger.info("=" * 70)
        logger.info("HIBACHI GRID MARKET MAKER - LIVE TRADING")
        logger.info("=" * 70)
        logger.info(f"Symbol: {self.symbol}")
        logger.info(f"Spread: {self.base_spread_bps} bps")
        logger.info(f"Order Size: ${self.order_size_usd}")
        logger.info(f"Levels: {self.num_levels} per side")
        logger.info(f"Capital: ${self.capital}")
        logger.info(f"Max Inventory: {self.max_inventory_pct}%")
        logger.info(f"ROC Threshold: {self.roc_threshold_bps} bps")
        logger.info("=" * 70)

        # Initialize client
        api_key = os.getenv("HIBACHI_PUBLIC_KEY")
        api_secret = os.getenv("HIBACHI_PRIVATE_KEY")
        account_id = os.getenv("HIBACHI_ACCOUNT_ID")

        if not all([api_key, api_secret, account_id]):
            logger.error("Missing Hibachi credentials in .env")
            return False

        logger.info("Connecting to Hibachi...")
        self.client = HibachiSDK(
            api_key=api_key,
            api_secret=api_secret,
            account_id=account_id
        )

        # Get account balance
        try:
            account = await self.client.get_account_info()
            if account:
                self.initial_balance = float(account.get('equity', account.get('balance', 0)))
                self.current_balance = self.initial_balance
                logger.info(f"Account balance: ${self.initial_balance:.2f}")
        except Exception as e:
            logger.error(f"Failed to get account: {e}")
            return False

        # Get market info
        try:
            market = await self.client.get_market_info(self.symbol)
            if market:
                self.tick_size = float(market.get('tickSize', 0.01))
                self.step_size = float(market.get('stepSize', 0.0001))
                logger.info(f"Market: tick={self.tick_size}, step={self.step_size}")
        except Exception as e:
            logger.warning(f"Could not get market info: {e}")

        # Get initial price - try orderbook first, then price endpoint
        try:
            orderbook = await self.client.get_orderbook(self.symbol)
            if orderbook:
                # Try different response formats
                bids = orderbook.get('bids') or orderbook.get('buy') or []
                asks = orderbook.get('asks') or orderbook.get('sell') or []

                if bids and asks:
                    # Handle both [[price, size]] and [{price, size}] formats
                    if isinstance(bids[0], list):
                        bid = float(bids[0][0])
                        ask = float(asks[0][0])
                    elif isinstance(bids[0], dict):
                        bid = float(bids[0].get('price', 0))
                        ask = float(asks[0].get('price', 0))
                    else:
                        bid = float(bids[0])
                        ask = float(asks[0])

                    if bid > 0 and ask > 0:
                        self.grid_center = (bid + ask) / 2
                        logger.info(f"Initial price: ${self.grid_center:,.2f} (bid: ${bid:,.2f}, ask: ${ask:,.2f})")
        except Exception as e:
            logger.warning(f"Orderbook error: {e}")

        # Fallback to price endpoint
        if not self.grid_center:
            try:
                price = await self.client.get_price(self.symbol)
                if price and price > 0:
                    self.grid_center = price
                    logger.info(f"Initial price (from ticker): ${self.grid_center:,.2f}")
            except Exception as e:
                logger.warning(f"Price endpoint error: {e}")

        if not self.grid_center:
            logger.error("Could not determine initial price")
            return False

        self.start_time = datetime.now()
        return True

    def _round_price(self, price: float) -> Decimal:
        """Round price to tick size"""
        return Decimal(str(round(price / self.tick_size) * self.tick_size))

    def _round_size(self, size: float) -> Decimal:
        """Round size to step size"""
        return Decimal(str(round(size / self.step_size) * self.step_size))

    def _calculate_roc(self) -> float:
        """Calculate rate of change in basis points"""
        if len(self.price_history) < 10:
            return 0.0
        old_price = self.price_history[0]
        new_price = self.price_history[-1]
        if old_price == 0:
            return 0.0
        return (new_price - old_price) / old_price * 10000

    def _update_pause_state(self, roc: float):
        """Update order pause state based on ROC"""
        old_paused = self.orders_paused
        old_side = self.pause_side

        # Strong trend - pause ALL orders
        if abs(roc) > self.roc_threshold_bps * 2:
            if not self.orders_paused or self.pause_side != 'ALL':
                self.pause_start_time = datetime.now()
            self.orders_paused = True
            self.pause_side = 'ALL'
            direction = "UP" if roc > 0 else "DOWN"
            if not old_paused or old_side != 'ALL':
                logger.warning(f"  STRONG TREND {direction} - PAUSE ALL (ROC: {roc:+.2f} bps)")
        elif roc > self.roc_threshold_bps:
            if not self.orders_paused or self.pause_side != 'SELL':
                self.pause_start_time = datetime.now()
            self.orders_paused = True
            self.pause_side = 'SELL'
        elif roc < -self.roc_threshold_bps:
            if not self.orders_paused or self.pause_side != 'BUY':
                self.pause_start_time = datetime.now()
            self.orders_paused = True
            self.pause_side = 'BUY'
        else:
            if self.orders_paused and self.pause_start_time:
                elapsed = (datetime.now() - self.pause_start_time).total_seconds()
                if elapsed >= self.min_pause_duration:
                    self.orders_paused = False
                    self.pause_side = None
                    self.pause_start_time = None
            else:
                self.orders_paused = False
                self.pause_side = None

        if self.orders_paused and not old_paused and self.pause_side != 'ALL':
            logger.info(f"  PAUSE {self.pause_side} orders (ROC: {roc:+.2f} bps)")
        elif not self.orders_paused and old_paused:
            logger.info(f"  RESUME orders (ROC: {roc:+.2f} bps)")

    async def _cancel_all_orders(self):
        """Cancel all open orders"""
        try:
            orders = await self.client.get_orders(self.symbol)
            if orders:
                for order in orders:
                    order_id = order.get('orderId')
                    if order_id:
                        try:
                            await self.client.cancel_order(order_id)
                        except Exception as e:
                            logger.debug(f"Cancel error: {e}")
            self.open_orders.clear()
        except Exception as e:
            logger.error(f"Cancel all orders error: {e}")

    async def _place_grid_orders(self, mid_price: float):
        """Place grid of limit orders"""
        # First cancel existing orders
        await self._cancel_all_orders()

        if self.orders_paused and self.pause_side == 'ALL':
            logger.info(f"  Grid SKIPPED: Strong trend, all orders paused")
            return

        spread_pct = self.base_spread_bps / 10000
        max_inventory = self.capital * (self.max_inventory_pct / 100)

        orders_placed = 0

        # Place BUY orders (below mid)
        if not (self.orders_paused and self.pause_side == 'BUY'):
            for i in range(1, self.num_levels + 1):
                price = mid_price * (1 - spread_pct * i)
                price_dec = float(self._round_price(price))

                size = self.order_size_usd / price_dec
                size_dec = float(self._round_size(size))

                actual_notional = price_dec * size_dec
                if actual_notional < self.min_notional:
                    continue

                try:
                    result = await self.client.create_limit_order(
                        symbol=self.symbol,
                        is_buy=True,
                        amount=size_dec,
                        price=price_dec
                    )
                    if result and not result.get('error'):
                        order_id = result.get('orderId', f'buy_{i}')
                        self.open_orders[order_id] = {
                            'side': 'BUY',
                            'price': price_dec,
                            'size': size_dec,
                            'level': i
                        }
                        orders_placed += 1
                except Exception as e:
                    logger.warning(f"BUY error L{i}: {e}"[:80])

        # Place SELL orders (above mid)
        if not (self.orders_paused and self.pause_side == 'SELL'):
            for i in range(1, self.num_levels + 1):
                price = mid_price * (1 + spread_pct * i)
                price_dec = float(self._round_price(price))

                size = self.order_size_usd / price_dec
                size_dec = float(self._round_size(size))

                actual_notional = price_dec * size_dec
                if actual_notional < self.min_notional:
                    continue

                try:
                    result = await self.client.create_limit_order(
                        symbol=self.symbol,
                        is_buy=False,
                        amount=size_dec,
                        price=price_dec
                    )
                    if result and not result.get('error'):
                        order_id = result.get('orderId', f'sell_{i}')
                        self.open_orders[order_id] = {
                            'side': 'SELL',
                            'price': price_dec,
                            'size': size_dec,
                            'level': i
                        }
                        orders_placed += 1
                except Exception as e:
                    logger.warning(f"SELL error L{i}: {e}"[:80])

        self.grid_center = mid_price
        if orders_placed > 0:
            logger.info(f"  Grid: {orders_placed} orders placed around ${mid_price:,.2f}")

    async def _check_fills(self) -> int:
        """Check for filled orders"""
        fills = 0
        try:
            orders = await self.client.get_orders(self.symbol)
            exchange_order_ids = set()

            if orders:
                for order in orders:
                    order_id = order.get('orderId')
                    status = order.get('status', '').upper()

                    if status in ['OPEN', 'NEW', 'PARTIAL']:
                        exchange_order_ids.add(order_id)

                    if order_id in self.open_orders and status in ['FILLED', 'CLOSED']:
                        info = self.open_orders[order_id]
                        filled_size = float(order.get('filledQuantity', info['size']))
                        fill_price = float(order.get('avgPrice', info['price']))

                        notional = filled_size * fill_price
                        self.total_volume += notional
                        self.fills_count += 1
                        fills += 1

                        logger.info(f"  FILL: {info['side']} {filled_size:.6f} @ ${fill_price:,.2f} (${notional:,.2f})")
                        del self.open_orders[order_id]

            # Sync: remove stale orders
            stale = [oid for oid in self.open_orders if oid not in exchange_order_ids]
            for oid in stale:
                del self.open_orders[oid]

        except Exception as e:
            logger.error(f"Check fills error: {e}")

        return fills

    async def _sync_position(self):
        """Sync position from exchange"""
        try:
            positions = await self.client.get_positions()
            if positions:
                for pos in positions:
                    if pos.get('symbol') == self.symbol:
                        self.position_size = float(pos.get('size', 0))
                        entry_price = float(pos.get('entryPrice', 0))
                        self.position_notional = abs(self.position_size * entry_price)
                        return
            self.position_size = 0.0
            self.position_notional = 0.0
        except Exception as e:
            logger.debug(f"Sync position error: {e}")

    async def run(self):
        """Main trading loop"""
        try:
            if not await self.initialize():
                return

            cycle = 0
            grid_reset_pct = 0.25

            logger.info(f"\nStarting live trading...")
            logger.info("-" * 70)

            # Place initial grid
            await self._place_grid_orders(self.grid_center)

            while True:
                cycle += 1

                # Get current orderbook
                try:
                    orderbook = await self.client.get_orderbook(self.symbol)
                    if not orderbook:
                        await asyncio.sleep(2)
                        continue

                    bids = orderbook.get('bids', [])
                    asks = orderbook.get('asks', [])
                    if not bids or not asks:
                        await asyncio.sleep(2)
                        continue

                    bid = float(bids[0][0])
                    ask = float(asks[0][0])
                    mid = (bid + ask) / 2
                    spread_bps = (ask - bid) / mid * 10000

                except Exception as e:
                    logger.warning(f"Orderbook error: {e}")
                    await asyncio.sleep(2)
                    continue

                self.price_history.append(mid)

                # Calculate ROC and update pause state
                roc = self._calculate_roc()
                self._update_pause_state(roc)

                # Check for fills
                fills = await self._check_fills()

                # Refresh grid on price move or fills
                price_move_pct = abs(mid - self.grid_center) / self.grid_center * 100 if self.grid_center else 0

                no_tracked_orders = len(self.open_orders) == 0
                not_fully_paused = not (self.orders_paused and self.pause_side == 'ALL')

                should_refresh = (
                    fills > 0 or
                    price_move_pct >= grid_reset_pct or
                    (no_tracked_orders and not_fully_paused)
                )

                if should_refresh:
                    if price_move_pct >= grid_reset_pct:
                        logger.info(f"  Grid reset: price moved {price_move_pct:.3f}%")
                    elif no_tracked_orders and not_fully_paused:
                        logger.info(f"  Grid reset: no active orders")
                    await self._sync_position()
                    await self._place_grid_orders(mid)

                # Status log every 30 seconds
                if cycle % 30 == 0:
                    try:
                        account = await self.client.get_account_info()
                        if account:
                            self.current_balance = float(account.get('equity', self.current_balance))
                    except:
                        pass

                    pnl = self.current_balance - self.initial_balance
                    elapsed = (datetime.now() - self.start_time).total_seconds() / 60
                    pause_status = f"PAUSE-{self.pause_side}" if self.orders_paused else "LIVE"

                    logger.info(f"\n[{elapsed:.1f}m] ${mid:,.2f} | Spread: {spread_bps:.1f}bps | ROC: {roc:+.1f}bps | {pause_status}")
                    logger.info(f"  Volume: ${self.total_volume:,.2f} | Fills: {self.fills_count}")
                    logger.info(f"  P&L: ${pnl:+.2f} (${self.current_balance:.2f})")

                await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("\nStopping by user request...")
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            logger.info("\nCleaning up - canceling open orders...")
            await self._cancel_all_orders()
            self._print_report()

    def _print_report(self):
        """Print final report"""
        elapsed = (datetime.now() - self.start_time).total_seconds() / 60 if self.start_time else 0
        pnl = self.current_balance - self.initial_balance

        logger.info("\n" + "=" * 70)
        logger.info("HIBACHI GRID MM - FINAL REPORT")
        logger.info("=" * 70)
        logger.info(f"Duration: {elapsed:.1f} minutes")
        logger.info(f"Total Volume: ${self.total_volume:,.2f}")
        logger.info(f"Total Fills: {self.fills_count}")
        logger.info(f"P&L: ${pnl:+.2f}")
        logger.info("=" * 70)


def main():
    """
    Hibachi Grid MM - same strategy as Paradex
    """
    mm = HibachiGridMM(
        symbol="ETH/USDT-P",           # ETH on Hibachi
        base_spread_bps=2.0,           # 2 bps spread
        order_size_usd=100.0,          # $100 per order
        num_levels=2,                  # 2 levels per side = $200 per side
        max_inventory_pct=300.0,       # Allow $210 max inventory
        capital=70.0,                  # ~$70 account
        roc_threshold_bps=5.0,         # More conservative ROC threshold
        min_pause_duration=30,         # 30s pause
    )
    asyncio.run(mm.run())


if __name__ == "__main__":
    main()
