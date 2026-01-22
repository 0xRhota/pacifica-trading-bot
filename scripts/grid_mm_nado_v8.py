#!/usr/bin/env python3
"""
Grid Market Maker v15 - Nado DEX
Dynamic spread based on ROC volatility + time-based refresh

Strategy: Place limit orders on both sides of mid price
- Grid resets on 0.5% price move
- Inventory skew at 70% threshold
- ROC-based trend pause with longer pauses
- DYNAMIC SPREAD: Automatically adjusts based on volatility
- TIME-BASED REFRESH: Refresh orders every 5 minutes (US-001)

v15 Changes (Time-based refresh - US-001):
- Added last_refresh_time tracking
- Refresh orders if >5 minutes since last placement
- Move _calculate_dynamic_spread() OUTSIDE of _place_grid_orders()
  so spread updates every status cycle (not just on order placement)
- Log shows 'Time-based refresh' when triggered

v12 Parameters (Dynamic Spread):
- Spread: DYNAMIC based on ROC
  - ROC 0-5 bps → 15 bps spread (calm market)
  - ROC 5-10 bps → 20 bps spread (low volatility)
  - ROC 10-20 bps → 25 bps spread (moderate volatility)
  - ROC >20 bps → PAUSE orders (trend detected)
- ROC threshold: 50 bps for pause
- Pause duration: 5 minutes
- Grid reset: 0.5% price move OR 5 min time-based refresh
"""

import os
import sys
import time
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, List
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

from dexes.nado.nado_sdk import NadoSDK


class GridMarketMakerNado:
    """
    Grid Market Maker v12 for Nado - Dynamic spread based on ROC volatility
    """

    def __init__(
        self,
        symbol: str = "ETH-PERP",
        base_spread_bps: float = 8.0,      # v11: 8 bps (15 was too wide) per Qwen
        order_size_usd: float = 100.0,     # $100 per order
        num_levels: int = 2,               # 2 levels per side
        max_inventory_pct: float = 100.0,  # v9: Lower leverage limit
        capital: float = 90.0,             # Account capital
        hedge_symbol: str = "BTC-PERP",    # Cross-asset LONG hedge
        hedge_size_pct: float = 80.0,      # Use 80% of capital for hedge (increased for tariff play)
        roc_threshold_bps: float = 50.0,   # v10: 50 bps ROC threshold (was 3) per Qwen
        min_pause_duration: int = 300,     # v10: 5 min pause (was 15s) per Qwen
    ):
        self.symbol = symbol
        self.base_spread_bps = base_spread_bps
        self.order_size_usd = order_size_usd
        self.num_levels = num_levels
        self.max_inventory_pct = max_inventory_pct
        self.capital = capital
        self.hedge_symbol = hedge_symbol
        self.hedge_size_pct = hedge_size_pct
        self.roc_threshold_bps = roc_threshold_bps
        self.min_pause_duration = min_pause_duration

        # Hedge position tracking
        self.hedge_position_opened = False

        # State
        self.sdk: Optional[NadoSDK] = None
        self.grid_center = None
        self.open_orders: Dict[str, Dict] = {}  # digest -> order info
        self.price_history: deque = deque(maxlen=360)  # 6 minutes at 1/sec

        # Trend detection
        self.orders_paused = False
        self.pause_side = None
        self.pause_start_time = None

        # Dynamic spread tracking
        self.current_spread_bps = base_spread_bps
        self.last_spread_bps = base_spread_bps

        # Stats
        self.total_volume = 0.0
        self.fills_count = 0
        self.start_time = None
        self.initial_balance = 0.0

        # v14: Cooldown after placing orders (skip fill check for N cycles)
        self.skip_fill_check_cycles = 0

        # v15: Time-based refresh (US-001)
        self.last_refresh_time = None
        self.time_refresh_interval = 300  # 5 minutes

        # Position tracking
        self.position_size = 0.0
        self.position_notional = 0.0

        # Market info
        self.product_id = None
        self.tick_size = 0.1
        self.step_size = 0.001
        self.min_notional = 100.0  # Nado min is $100

        # Grid reset threshold (v10: 0.5% price move, was 0.25%) per Qwen
        self.grid_reset_pct = 0.50

    async def initialize(self):
        """Initialize Nado SDK"""
        logger.info("=" * 70)
        logger.info("NADO GRID MM v13 - ANTI-ADVERSE-SELECTION")
        logger.info("=" * 70)
        logger.info(f"Symbol: {self.symbol}")
        logger.info(f"Spread: DYNAMIC (15-30 bps - wider to beat adverse selection)")
        logger.info(f"  ROC 0-5 bps → 15 bps spread")
        logger.info(f"  ROC 5-10 bps → 20 bps spread")
        logger.info(f"  ROC 10-20 bps → 25 bps spread")
        logger.info(f"  ROC >20 bps → PAUSE orders (trend detected)")
        logger.info(f"ROC Window: 1 minute (fast reaction)")
        logger.info(f"Order Size: ${self.order_size_usd}")
        logger.info(f"Levels: {self.num_levels} per side")
        logger.info(f"Grid Reset: {self.grid_reset_pct}% price move")
        logger.info(f"ROC Threshold: {self.roc_threshold_bps} bps")
        logger.info(f"Min Pause: {self.min_pause_duration}s")
        logger.info(f"Time-based Refresh: {self.time_refresh_interval}s")
        logger.info("=" * 70)

        # Initialize SDK
        wallet_address = os.getenv('NADO_WALLET_ADDRESS')
        signer_key = os.getenv('NADO_LINKED_SIGNER_PRIVATE_KEY')
        subaccount_name = os.getenv('NADO_SUBACCOUNT_NAME', 'default')

        if not wallet_address or not signer_key:
            raise ValueError("NADO_WALLET_ADDRESS and NADO_LINKED_SIGNER_PRIVATE_KEY required in .env")

        self.sdk = NadoSDK(wallet_address, signer_key, subaccount_name=subaccount_name)

        # Verify linked signer
        if not await self.sdk.verify_linked_signer():
            raise ValueError("Linked signer not verified")
        logger.info("Linked signer verified!")

        # Get balance
        balance = await self.sdk.get_balance()
        self.initial_balance = balance or 0
        # Use actual balance as capital (dynamic, not hardcoded)
        self.capital = self.initial_balance
        logger.info(f"Account balance: ${self.initial_balance:.2f}")

        # Get product info
        product = await self.sdk.get_product_by_symbol(self.symbol)
        if not product:
            raise ValueError(f"Product {self.symbol} not found")

        self.product_id = product.get('product_id')
        self.tick_size = float(product.get('quote_currency_price_increment', 0.1))
        self.step_size = float(product.get('base_currency_increment', 0.001))
        self.min_notional = 100.0  # Nado min
        logger.info(f"Product ID: {self.product_id}, tick={self.tick_size}, step={self.step_size}, min=${self.min_notional}")

        # Get initial price
        mid = await self._get_mid_price()
        if not mid:
            raise Exception("Cannot get initial price")

        logger.info(f"Initial price: ${mid:,.2f}")
        self.grid_center = mid
        self.price_history.append(mid)
        self.start_time = datetime.now()

        # Sync position
        await self._sync_position()

        # DISABLED: Hedge feature removed per user request (2026-01-15)
        # await self._open_hedge_long()

        return True

    async def _get_mid_price(self) -> Optional[float]:
        """Get current mid price from Nado market_price query"""
        try:
            response = await self.sdk._query("market_price", {"product_id": str(self.product_id)})
            if response.get("status") == "success":
                data = response.get("data", {})
                bid = self.sdk._from_x18(int(data.get('bid_x18', '0')))
                ask = self.sdk._from_x18(int(data.get('ask_x18', '0')))
                if bid > 0 and ask > 0:
                    return (bid + ask) / 2
        except Exception as e:
            logger.error(f"Mid price error: {e}")
        return None

    async def _sync_position(self):
        """Sync position from exchange"""
        try:
            self.position_size = await self.sdk.get_position_size(self.symbol)
            mid = await self._get_mid_price()
            if mid:
                self.position_notional = self.position_size * mid
                if self.position_size != 0:
                    side = 'LONG' if self.position_size > 0 else 'SHORT'
                    logger.info(f"Position: {side} {abs(self.position_size):.6f} (${abs(self.position_notional):,.2f})")
        except Exception as e:
            logger.error(f"Position sync error: {e}")

    async def _open_hedge_long(self):
        """Open a LONG position on the hedge asset (BTC when grid is ETH)"""
        if self.hedge_position_opened:
            return

        try:
            # Check current hedge position
            hedge_size = await self.sdk.get_position_size(self.hedge_symbol)

            # Get hedge asset price first (needed for both check and order)
            hedge_product = await self.sdk.get_product_by_symbol(self.hedge_symbol)
            if not hedge_product:
                logger.error(f"Hedge product {self.hedge_symbol} not found")
                return

            hedge_product_id = hedge_product.get('product_id')
            response = await self.sdk._query("market_price", {"product_id": str(hedge_product_id)})
            if response.get("status") != "success":
                logger.error("Cannot get hedge price")
                return

            data = response.get("data", {})
            bid = self.sdk._from_x18(int(data.get('bid_x18', '0')))
            ask = self.sdk._from_x18(int(data.get('ask_x18', '0')))
            hedge_price = (bid + ask) / 2

            # Calculate target hedge size
            target_notional = self.capital * (self.hedge_size_pct / 100)
            current_notional = hedge_size * hedge_price if hedge_size > 0 else 0

            if hedge_size > 0:
                logger.info(f"Current hedge: {self.hedge_symbol} = {hedge_size:.6f} (${current_notional:.2f})")
                # Check if we need to top up
                if current_notional >= target_notional * 0.9:  # Within 10% of target
                    logger.info(f"✅ Hedge at target: ${current_notional:.2f} / ${target_notional:.2f}")
                    self.hedge_position_opened = True
                    return
                else:
                    # Need to add more
                    additional_notional = target_notional - current_notional
                    logger.info(f"🔄 Topping up hedge: need ${additional_notional:.2f} more")

            # If SHORT, close it first
            if hedge_size < 0:
                logger.info(f"🔄 Closing SHORT hedge on {self.hedge_symbol}...")
                result = await self.sdk.create_market_order(
                    symbol=self.hedge_symbol,
                    is_buy=True,
                    amount=abs(hedge_size)
                )
                if result and result.get('status') == 'success':
                    logger.info(f"  ✅ Closed SHORT {self.hedge_symbol}")
                await asyncio.sleep(1)
                current_notional = 0  # Reset after closing short

            # Calculate amount to add (full target if new, difference if topping up)
            hedge_notional = target_notional - current_notional

            if hedge_notional < 5:  # Min $5 order
                logger.info(f"Hedge amount too small: ${hedge_notional:.2f}")
                self.hedge_position_opened = True
                return

            # Calculate size
            import math
            step_size_raw = hedge_product.get('size_increment') or hedge_product.get('base_increment')
            step_size = self.sdk._from_x18(int(step_size_raw)) if step_size_raw else 0.0001
            hedge_amount = hedge_notional / hedge_price
            hedge_amount = math.ceil(hedge_amount / step_size) * step_size

            action = "Topping up" if current_notional > 0 else "Opening"
            logger.info(f"🚀 {action} LONG hedge: {self.hedge_symbol} ${hedge_notional:.2f} @ ${hedge_price:,.2f}")

            result = await self.sdk.create_market_order(
                symbol=self.hedge_symbol,
                is_buy=True,
                amount=hedge_amount
            )

            if result and result.get('status') == 'success':
                final_notional = current_notional + hedge_notional
                logger.info(f"  ✅ HEDGE LONG: {self.hedge_symbol} +{hedge_amount:.6f} (total ${final_notional:.2f})")
                self.hedge_position_opened = True
            else:
                logger.error(f"  ❌ Hedge order failed: {result}")

        except Exception as e:
            logger.error(f"Hedge open error: {e}")

    def _round_price(self, price: float) -> float:
        """Round price to tick size (avoid floating point errors)"""
        ticks = round(price / self.tick_size)
        return round(ticks * self.tick_size, 2)  # Round to 2 decimals to avoid FP errors

    def _round_size(self, size: float) -> float:
        """Round size to step size - round UP to ensure min notional is met"""
        import math
        steps = math.ceil(size / self.step_size)  # Round UP not down
        result = max(steps * self.step_size, self.step_size)
        return round(result, 3)  # Round to 3 decimals to avoid FP errors like 0.043000000000003

    def _calculate_roc(self) -> float:
        """Calculate Rate of Change in bps over 3-minute window (v14: proper window per LEARNINGS.md)"""
        if len(self.price_history) < 180:
            return 0.0  # Need 3 min of data before calculating ROC
        prices = list(self.price_history)
        current = prices[-1]
        past = prices[-180]  # 3 minutes ago (180 samples at 1/sec) - per LEARNINGS.md ROC window fix
        if past == 0:
            return 0.0
        return (current - past) / past * 10000

    def _calculate_dynamic_spread(self, roc: float) -> float:
        """
        Calculate dynamic spread based on ROC (volatility).

        v13: WIDER SPREADS to combat adverse selection (-8.5 bps avg loss)
        Analysis showed we were buying $2.51 higher than selling on average.
        Minimum spread must exceed adverse selection to be profitable.

        Spread bands (v13 - wider to beat adverse selection):
        | ROC (abs) | Spread | Rationale |
        |-----------|--------|-----------|
        | 0-5 bps   | 15 bps | Calm market - still need edge over adverse selection |
        | 5-10 bps  | 20 bps | Low volatility, balanced |
        | 10-20 bps | 25 bps | Moderate volatility, protect |
        | > 20 bps  | PAUSE  | Stop trading, trend detected |
        """
        abs_roc = abs(roc)

        if abs_roc < 5:
            spread = 15.0  # Was 1.5 - way too tight
        elif abs_roc < 10:
            spread = 20.0  # Was 3.0
        elif abs_roc < 20:
            spread = 25.0  # Was 6.0
        else:
            # Above 20 bps = trend, pause orders
            spread = 30.0

        return spread

    def _update_pause_state(self, roc: float):
        """Update order pause state based on trend - EXACT v8 logic"""
        old_paused = self.orders_paused
        old_side = self.pause_side

        strong_trend_threshold = self.roc_threshold_bps * 2.0

        if abs(roc) > strong_trend_threshold:
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
            result = await self.sdk.cancel_all_orders(self.symbol)
            if result:
                logger.info(f"  Orders cancelled")
            self.open_orders.clear()
        except Exception as e:
            logger.error(f"Cancel error: {e}")
            self.open_orders.clear()

    async def _place_grid_orders(self, mid_price: float, roc: float = 0.0):
        """Place grid orders with dynamic spread based on volatility (ROC)"""
        # First cancel existing orders
        await self._cancel_all_orders()

        # If ALL orders paused, don't place anything
        if self.orders_paused and self.pause_side == 'ALL':
            logger.info(f"  Grid SKIPPED: Strong trend, all orders paused")
            return

        # Calculate dynamic spread based on current volatility
        self.current_spread_bps = self._calculate_dynamic_spread(roc)

        # Log spread changes
        if self.current_spread_bps != self.last_spread_bps:
            direction = "WIDENED" if self.current_spread_bps > self.last_spread_bps else "TIGHTENED"
            logger.info(f"  📊 SPREAD {direction}: {self.last_spread_bps:.1f} → {self.current_spread_bps:.1f} bps (ROC: {roc:+.1f})")
            self.last_spread_bps = self.current_spread_bps

        spread_pct = self.current_spread_bps / 10000
        # DYNAMIC BALANCE: Fetch fresh balance for inventory calculations
        # (Don't use cached self.capital - balance may have changed from deposits/withdrawals)
        current_balance = await self.sdk.get_balance() or self.capital
        max_inventory = current_balance * (self.max_inventory_pct / 100)

        # Inventory ratio (signed: positive=long, negative=short)
        inv_ratio = self.position_notional / max_inventory if max_inventory > 0 else 0

        # v8 INVENTORY SKEW LOGIC
        buy_mult = 1.0
        sell_mult = 1.0
        min_mult = self.min_notional / self.order_size_usd if self.order_size_usd > 0 else 1.0

        if inv_ratio > 0.7:  # Heavy LONG - ONLY sells
            buy_mult = 0.0
            # Use min_notional to reduce - leave buffer for rounding
            # Max sell = position + max_inventory - buffer for rounding
            max_sell = abs(self.position_notional) + max_inventory - 10  # $10 buffer
            sell_target = min(max_sell, self.order_size_usd * 1.5)
            sell_target = max(sell_target, self.min_notional)  # At least min order
            sell_mult = sell_target / self.order_size_usd if self.order_size_usd > 0 else 1.0
            logger.info(f"  REDUCE LONG MODE: {inv_ratio*100:.0f}% - sells only (${sell_target:.0f})")
        elif inv_ratio > 0.3:
            buy_mult = max(min_mult, 0.3)
            sell_mult = 1.3
        elif inv_ratio < -0.7:  # Heavy SHORT - ONLY buys
            # Max buy = position + max_inventory - buffer for rounding
            max_buy = abs(self.position_notional) + max_inventory - 10  # $10 buffer
            buy_target = min(max_buy, self.order_size_usd * 1.5)
            buy_target = max(buy_target, self.min_notional)  # At least min order
            buy_mult = buy_target / self.order_size_usd if self.order_size_usd > 0 else 1.0
            sell_mult = 0.0
            logger.info(f"  REDUCE SHORT MODE: {inv_ratio*100:.0f}% - buys only (${buy_target:.0f})")
        elif inv_ratio < -0.3:
            buy_mult = 1.3
            sell_mult = max(min_mult, 0.3)

        orders_placed = 0

        # Place BUY orders
        if not (self.orders_paused and self.pause_side == 'BUY') and buy_mult > 0:
            for i in range(1, self.num_levels + 1):
                price = mid_price * (1 - spread_pct * i)
                price = self._round_price(price)

                target_notional = self.order_size_usd * buy_mult
                if target_notional < self.min_notional:
                    continue

                size = target_notional / price
                size = self._round_size(size)

                actual_notional = price * size
                if actual_notional < self.min_notional:
                    continue

                # Check inventory limit
                potential = self.position_notional + actual_notional
                if potential > max_inventory:
                    continue

                try:
                    result = await self.sdk.create_limit_order(
                        symbol=self.symbol,
                        is_buy=True,
                        amount=size,
                        price=price,
                        order_type="POST_ONLY"  # Maker-only: reject if would cross spread
                    )
                    if result and result.get('status') == 'success':
                        digest = result.get('data', {}).get('digest', str(time.time()))
                        self.open_orders[digest] = {
                            'side': 'BUY', 'price': price, 'size': size
                        }
                        orders_placed += 1
                        logger.debug(f"  BUY {size:.4f} @ ${price:,.2f}")
                except Exception as e:
                    logger.debug(f"BUY L{i} error: {e}")

        # Place SELL orders
        if not (self.orders_paused and self.pause_side == 'SELL') and sell_mult > 0:
            for i in range(1, self.num_levels + 1):
                price = mid_price * (1 + spread_pct * i)
                price = self._round_price(price)

                target_notional = self.order_size_usd * sell_mult
                if target_notional < self.min_notional:
                    continue

                size = target_notional / price
                size = self._round_size(size)

                actual_notional = price * size
                if actual_notional < self.min_notional:
                    continue

                # Check inventory limit
                potential = self.position_notional - actual_notional
                if potential < -max_inventory:
                    continue

                try:
                    result = await self.sdk.create_limit_order(
                        symbol=self.symbol,
                        is_buy=False,
                        amount=size,
                        price=price,
                        order_type="POST_ONLY"  # Maker-only: reject if would cross spread
                    )
                    if result and result.get('status') == 'success':
                        digest = result.get('data', {}).get('digest', str(time.time()))
                        self.open_orders[digest] = {
                            'side': 'SELL', 'price': price, 'size': size
                        }
                        orders_placed += 1
                        logger.debug(f"  SELL {size:.4f} @ ${price:,.2f}")
                except Exception as e:
                    logger.debug(f"SELL L{i} error: {e}")

        self.grid_center = mid_price
        if orders_placed > 0:
            logger.info(f"  Grid: {orders_placed} orders @ ${mid_price:,.2f} (spread: {self.current_spread_bps:.1f}bps)")
            # v14: Set cooldown to allow orders to propagate before checking fills
            self.skip_fill_check_cycles = 3  # Skip fill check for 3 seconds

    async def _check_fills(self) -> int:
        """Check for filled orders - EXACT v8 logic"""
        fills = 0
        try:
            orders = await self.sdk.get_orders(self.product_id)
            exchange_digests = set()

            for order in orders:
                digest = order.get('digest')
                status = order.get('status', '').upper()

                if status in ['OPEN', 'PENDING', 'NEW']:
                    exchange_digests.add(digest)

                if digest in self.open_orders and status in ['FILLED', 'CLOSED']:
                    info = self.open_orders[digest]
                    filled_size = float(order.get('filled_amount', info['size']))
                    fill_price = info['price']  # Nado may not return fill price

                    notional = filled_size * fill_price
                    self.total_volume += notional
                    self.fills_count += 1
                    fills += 1

                    logger.info(f"  FILL: {info['side']} {filled_size:.6f} @ ${fill_price:,.2f} (${notional:,.2f})")
                    del self.open_orders[digest]

            # v14: REMOVED "inferred fill" logic
            # On Nado, orders can disappear from get_orders() due to API propagation delays
            # This was causing false fill detection and constant grid resets
            # Now we only count fills when we see explicit FILLED/CLOSED status
            # If orders disappear without status, they were likely cancelled/rejected/expired, not filled
            tracked_digests = set(self.open_orders.keys())
            disappeared = tracked_digests - exchange_digests

            # Just clear disappeared orders from tracking (don't count as fills)
            for digest in disappeared:
                if digest in self.open_orders:
                    # Don't log or count - silently remove stale tracking
                    del self.open_orders[digest]

        except Exception as e:
            logger.error(f"Check fills error: {e}")

        return fills

    async def run(self):
        """Main trading loop - v15 with time-based refresh (US-001)"""
        try:
            if not await self.initialize():
                return

            logger.info(f"\nStarting grid MM (reset on {self.grid_reset_pct}% move)...")
            logger.info("-" * 70)

            # Place initial grid
            await self._place_grid_orders(self.grid_center)
            self.last_refresh_time = datetime.now()  # v15: Track refresh time

            cycle = 0
            while True:
                cycle += 1

                # Get current price
                mid = await self._get_mid_price()
                if not mid:
                    await asyncio.sleep(1)
                    continue

                self.price_history.append(mid)

                # Calculate ROC and update pause state
                roc = self._calculate_roc()
                self._update_pause_state(roc)

                # v15: Update dynamic spread EVERY cycle (not just when placing orders)
                # This fixes bug where spread gets stuck when no fills/price moves
                new_spread = self._calculate_dynamic_spread(roc)
                if new_spread != self.current_spread_bps:
                    direction = "WIDENED" if new_spread > self.current_spread_bps else "TIGHTENED"
                    logger.info(f"  📊 SPREAD {direction}: {self.current_spread_bps:.1f} → {new_spread:.1f} bps (ROC: {roc:+.1f})")
                    self.current_spread_bps = new_spread

                # v14: Decrement cooldown and skip fill check if needed
                if self.skip_fill_check_cycles > 0:
                    self.skip_fill_check_cycles -= 1
                    fills = 0  # Don't check fills during cooldown
                else:
                    # Check for fills
                    fills = await self._check_fills()

                # v8: Price-based grid reset (0.25% move)
                price_move_pct = abs(mid - self.grid_center) / self.grid_center * 100 if self.grid_center else 0

                # Inventory ratio for force reset (use fresh balance)
                loop_balance = await self.sdk.get_balance() or self.capital
                max_inventory = loop_balance * (self.max_inventory_pct / 100)
                inventory_ratio = abs(self.position_notional) / max_inventory if max_inventory > 0 else 0

                # Safety: refresh if no tracked orders
                no_tracked = len(self.open_orders) == 0
                not_paused = not (self.orders_paused and self.pause_side == 'ALL')

                # NOTE: Removed inventory_ratio > 0.8 reset trigger (v14)
                # REDUCE LONG/SHORT MODE already handles high inventory by placing one-sided orders
                # Resetting every cycle was cancelling orders before they could fill
                #
                # v14: Also removed "no active orders" reset trigger
                # Nado API has propagation delays - orders aren't immediately visible in get_orders()
                # This was causing false "no active orders" detection and constant reset loops
                #
                # v15: Added time-based refresh (US-001) to prevent stale orders
                # Hibachi uses 30s refresh and works correctly - apply similar pattern
                time_since_refresh = (datetime.now() - self.last_refresh_time).total_seconds() if self.last_refresh_time else 0
                time_based_refresh = time_since_refresh >= self.time_refresh_interval

                should_refresh = (
                    fills > 0 or
                    price_move_pct >= self.grid_reset_pct or
                    time_based_refresh
                )

                if should_refresh:
                    if time_based_refresh:
                        logger.info(f"  Time-based refresh: {time_since_refresh:.0f}s since last placement")
                    elif price_move_pct >= self.grid_reset_pct:
                        logger.info(f"  Grid reset: price moved {price_move_pct:.3f}%")
                    await self._sync_position()
                    await self._place_grid_orders(mid, roc)
                    self.last_refresh_time = datetime.now()  # v15: Update refresh time

                # Status log every 30 cycles
                if cycle % 30 == 0:
                    balance = await self.sdk.get_balance() or 0
                    pnl = balance - self.initial_balance
                    elapsed = (datetime.now() - self.start_time).total_seconds() / 60
                    inv_pct = abs(self.position_notional) / self.capital * 100 if self.capital > 0 else 0
                    pause_status = f"PAUSE-{self.pause_side}" if self.orders_paused else "LIVE"

                    logger.info(f"\n[{elapsed:.1f}m] ${mid:,.2f} | ROC: {roc:+.1f}bps | Spread: {self.current_spread_bps:.1f}bps | {pause_status}")
                    logger.info(f"  Position: {self.position_size:.6f} ({inv_pct:.0f}% inv)")
                    logger.info(f"  Volume: ${self.total_volume:,.2f} | Fills: {self.fills_count}")
                    logger.info(f"  P&L: ${pnl:+.2f} (${balance:.2f})")

                await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("\nStopping...")
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            logger.info("\nCancelling orders...")
            await self._cancel_all_orders()
            self._print_report()

    def _print_report(self):
        """Print final report"""
        elapsed = (datetime.now() - self.start_time).total_seconds() / 60 if self.start_time else 0
        logger.info("\n" + "=" * 70)
        logger.info("NADO GRID MM v12 - FINAL REPORT")
        logger.info("=" * 70)
        logger.info(f"Duration: {elapsed:.1f} minutes")
        logger.info(f"Total Volume: ${self.total_volume:,.2f}")
        logger.info(f"Total Fills: {self.fills_count}")
        logger.info("=" * 70)


async def main():
    mm = GridMarketMakerNado(
        symbol="ETH-PERP",
        base_spread_bps=15.0,        # v13: wider spread to beat -8.5 bps adverse selection
        order_size_usd=100.0,        # $100 = Nado minimum
        num_levels=1,                # 1 level per side (small account)
        max_inventory_pct=175.0,     # 1.75x - min needed for $100 orders on $72 balance
        capital=50.0,                # Ignored - uses dynamic balance
        roc_threshold_bps=50.0,      # v14: back to 50 (20 was too aggressive - caused constant pauses)
        min_pause_duration=120,      # v13: shorter pause (was 300) - resume faster in ranges
    )
    await mm.run()


if __name__ == "__main__":
    asyncio.run(main())
