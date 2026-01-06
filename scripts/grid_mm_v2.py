#!/usr/bin/env python3
"""
Grid Market Maker v8 - Volume Recovery (Full History Context)
SCALED FOR $23 ACCOUNT

Qwen v8 recommendations WITH FULL v1-v7 HISTORY:
- v1-v4 PROVED wider spreads don't help (2.5 bps was WORSE than 1 bps)
- v6-v7 PROVED preemptive pausing is the key breakthrough

v8 changes (informed by complete history):
1. KEEP spread tight: 1.5 bps (v2-v4 proved widening doesn't help)
2. LOWER ROC threshold: 1.0 bps (catch trends earlier)
3. REDUCE pause duration: 15 seconds (from 20) - balance volume/safety
4. LOWER inventory limit: 25% (from 30%) - less exposure is better
5. Order size: $5 (scaled from $250 for $23 account)
6. 6 levels for depth

v8 @ $1000: +$1.19 P&L, +$1.81 per $10k (PROFITABLE!)
v8 @ $23: Testing if same efficiency holds at small scale

Goal: High volume + positive/break-even P&L

Reference: research/strategies/GRID_MM_EVOLUTION.md
Reference: research/LEARNINGS.md
"""

import os
import sys
import asyncio
import logging
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

from paradex_py import Paradex


class GridMarketMakerV2:
    """
    Improved Grid Market Maker with:
    - Inventory management
    - Volatility-adjusted spreads
    - Position skewing
    """

    def __init__(
        self,
        symbol: str = "BTC-USD-PERP",
        base_spread_bps: float = 2.5,          # Base spread: 2.5 bps (widened per Qwen v4)
        grid_reset_pct: float = 0.15,          # Reset at 0.15% (was 0.25%)
        stop_loss_pct: float = 10.0,
        order_size_usd: float = 200.0,         # $200 per order (was $100)
        num_levels: int = 5,                   # 5 levels per side (was 3)
        duration_minutes: int = 60,
        max_inventory_pct: float = 50.0,       # Max 50% of capital in inventory
        capital: float = 1000.0,
        volatility_window: int = 30,           # 30 samples for volatility calc
        volatility_multiplier: float = 1.5,   # Spread multiplier based on vol
    ):
        self.symbol = symbol
        self.base_spread_bps = base_spread_bps
        self.grid_reset_pct = grid_reset_pct
        self.stop_loss_pct = stop_loss_pct
        self.order_size_usd = order_size_usd
        self.num_levels = num_levels
        self.duration_minutes = duration_minutes
        self.max_inventory_pct = max_inventory_pct
        self.capital = capital
        self.volatility_window = volatility_window
        self.volatility_multiplier = volatility_multiplier

        # State
        self.client = None
        self.grid_center = None
        self.buy_orders: List[Dict] = []
        self.sell_orders: List[Dict] = []

        # Price history for volatility and trend detection
        self.price_history: deque = deque(maxlen=volatility_window)
        self.market_spread_history: deque = deque(maxlen=volatility_window)  # Track market spread
        self.current_spread_bps = base_spread_bps
        self.current_market_spread_bps = 0.5  # Will be updated from live data
        self.trend_strength = 0.0  # Positive = uptrend, negative = downtrend

        # v7: Trend detection and order pause state
        self.roc_bps = 0.0  # Rate of change in bps (10-second lookback)
        self.orders_paused = False  # True when orders should be paused
        self.pause_side = None  # 'BUY' or 'SELL' - which side is paused
        self.trend_order_size_mult = 1.0  # Reduce order size in trends
        self.pause_start_time = None  # v7: Track when pause started
        self.min_pause_duration = 15  # v8: 15s (was 20) - balance volume/safety

        # Stats
        self.total_volume = 0.0
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.fills = []
        self.start_time = None
        self.initial_balance = capital

        # Position tracking
        self.position_size = 0.0
        self.position_avg_price = 0.0
        self.position_notional = 0.0

        # Metrics
        self.grid_resets = 0
        self.spread_adjustments = 0

    async def initialize(self):
        """Initialize Paradex client"""
        logger.info("=" * 70)
        logger.info("GRID MARKET MAKER v8 - VOLUME RECOVERY")
        logger.info("=" * 70)
        logger.info(f"Symbol: {self.symbol}")
        logger.info(f"Base Spread: {self.base_spread_bps} bps (volatility-adjusted)")
        logger.info(f"Grid Reset: {self.grid_reset_pct}%")
        logger.info(f"Order Size: ${self.order_size_usd}")
        logger.info(f"Levels: {self.num_levels} per side")
        logger.info(f"Max Inventory: {self.max_inventory_pct}% of ${self.capital}")
        logger.info(f"Duration: {self.duration_minutes} minutes")
        logger.info("=" * 70)

        self.client = Paradex(env="prod")

        bbo = self.client.api_client.fetch_bbo(market=self.symbol)
        if not bbo:
            raise Exception(f"Cannot fetch BBO for {self.symbol}")

        mid = (float(bbo['bid']) + float(bbo['ask'])) / 2
        logger.info(f"Initial mid price: ${mid:,.2f}")

        self.grid_center = mid
        self.start_time = datetime.now()
        self.price_history.append(mid)

        self._place_grid(mid)

    def _calculate_volatility(self) -> float:
        """Calculate recent price volatility in bps"""
        if len(self.price_history) < 5:
            return 0.0

        prices = list(self.price_history)
        returns = []
        for i in range(1, len(prices)):
            ret = abs(prices[i] - prices[i-1]) / prices[i-1] * 10000  # bps
            returns.append(ret)

        if not returns:
            return 0.0

        # Use average absolute return as volatility proxy
        return sum(returns) / len(returns)

    def _calculate_trend(self) -> float:
        """
        Calculate trend strength using simple momentum.
        Returns: positive for uptrend, negative for downtrend, 0 for no trend.
        Qwen v4: Skip orders that go against strong trends to avoid adverse selection.
        """
        if len(self.price_history) < 10:
            return 0.0

        prices = list(self.price_history)
        # Compare recent prices (last 5) to earlier prices (5 before that)
        recent_avg = sum(prices[-5:]) / 5
        earlier_avg = sum(prices[-10:-5]) / 5

        if earlier_avg == 0:
            return 0.0

        # Trend strength in bps
        trend_bps = (recent_avg - earlier_avg) / earlier_avg * 10000
        self.trend_strength = trend_bps
        return trend_bps

    def _calculate_roc(self) -> float:
        """
        Calculate Rate of Change over short period (10 samples ~ 10 seconds).
        Qwen v6: This is FASTER than trend detection for preemptive order pausing.
        Returns: positive for rising price, negative for falling price, in bps.
        """
        if len(self.price_history) < 10:
            return 0.0

        prices = list(self.price_history)
        current_price = prices[-1]
        price_10s_ago = prices[-10]

        if price_10s_ago == 0:
            return 0.0

        roc_bps = (current_price - price_10s_ago) / price_10s_ago * 10000
        self.roc_bps = roc_bps
        return roc_bps

    def _update_pause_state(self):
        """
        Qwen v8 (with full v1-v7 history context):
        - Lower ROC threshold (1.0 bps) to catch trends earlier
        - 15s pause duration balances volume recovery vs safety
        - v2-v4 proved wider spreads don't help - keep pausing as primary defense
        """
        roc = self._calculate_roc()
        roc_threshold = 1.0  # v8: Even lower threshold (was 1.5) - catch trends earlier

        old_pause = self.orders_paused
        old_side = self.pause_side

        # Check if we should START a new pause
        if roc > roc_threshold:
            # Strong uptrend - PAUSE all sell orders
            if not self.orders_paused or self.pause_side != 'SELL':
                self.pause_start_time = datetime.now()
            self.orders_paused = True
            self.pause_side = 'SELL'
            self.trend_order_size_mult = 0.5
        elif roc < -roc_threshold:
            # Strong downtrend - PAUSE all buy orders
            if not self.orders_paused or self.pause_side != 'BUY':
                self.pause_start_time = datetime.now()
            self.orders_paused = True
            self.pause_side = 'BUY'
            self.trend_order_size_mult = 0.5
        else:
            # v7: Only resume if paused for minimum duration
            if self.orders_paused and self.pause_start_time:
                pause_elapsed = (datetime.now() - self.pause_start_time).total_seconds()
                if pause_elapsed >= self.min_pause_duration:
                    # Minimum duration met, can resume
                    self.orders_paused = False
                    self.pause_side = None
                    self.trend_order_size_mult = 1.0
                    self.pause_start_time = None
                # else: keep paused until minimum duration
            else:
                self.orders_paused = False
                self.pause_side = None
                self.trend_order_size_mult = 1.0

        # Log state changes
        if self.orders_paused and not old_pause:
            logger.info(f"  ⏸️ PAUSED {self.pause_side} orders (ROC: {roc:+.2f} bps, min {self.min_pause_duration}s)")
        elif not self.orders_paused and old_pause:
            logger.info(f"  ▶️ RESUMED orders (ROC: {roc:+.2f} bps)")

    def _get_adjusted_spread(self) -> float:
        """
        Get dynamic spread based on market spread + buffer.
        Qwen recommendation: Match market spread to capture fills, add small buffer for profit.
        """
        vol = self._calculate_volatility()

        # Get average market spread from recent history
        if len(self.market_spread_history) > 0:
            avg_market_spread = sum(self.market_spread_history) / len(self.market_spread_history)
        else:
            avg_market_spread = 0.5  # Default assumption

        # Dynamic spread = market spread + buffer (0.3-0.5 bps)
        # This ensures we're competitive but still capture some spread
        buffer_bps = 0.3 if vol < 2 else 0.5  # Larger buffer in higher vol

        # Base our spread on market spread, with minimum of base_spread_bps
        market_based_spread = avg_market_spread + buffer_bps
        adjusted = max(market_based_spread, self.base_spread_bps)

        # Still widen in high volatility
        if vol > 5:
            adjusted = adjusted * self.volatility_multiplier
        elif vol > 2:
            adjusted = adjusted * 1.2

        if abs(adjusted - self.current_spread_bps) > 0.1:  # Only log significant changes
            self.spread_adjustments += 1
            logger.info(f"  📊 Spread: {adjusted:.2f} bps (mkt: {avg_market_spread:.2f}, vol: {vol:.2f})")
            self.current_spread_bps = adjusted

        return adjusted

    def _get_inventory_skew(self) -> tuple:
        """
        Calculate order size skew based on inventory.
        Returns (buy_multiplier, sell_multiplier)

        Qwen v3: More GRADUAL skew to reduce profit erosion from forced rebalancing.
        Instead of aggressive 2x/0x, use smoother 1.3x/0.7x transitions.
        """
        max_inventory = self.capital * (self.max_inventory_pct / 100)

        if abs(self.position_notional) < max_inventory * 0.15:
            # Minimal inventory (<15%), no skew
            return (1.0, 1.0)

        inventory_ratio = self.position_notional / max_inventory

        if inventory_ratio > 0:  # Long inventory - reduce buys, increase sells
            if inventory_ratio > 0.8:
                return (0.2, 1.5)  # Heavy long - minimal buys (not zero), boost sells
            elif inventory_ratio > 0.5:
                return (0.5, 1.3)  # Moderate-heavy long
            elif inventory_ratio > 0.3:
                return (0.7, 1.2)  # Moderate long
            else:
                return (0.85, 1.1)  # Light long
        else:  # Short inventory - reduce sells, increase buys
            inventory_ratio = abs(inventory_ratio)
            if inventory_ratio > 0.8:
                return (1.5, 0.2)  # Heavy short - boost buys, minimal sells (not zero)
            elif inventory_ratio > 0.5:
                return (1.3, 0.5)  # Moderate-heavy short
            elif inventory_ratio > 0.3:
                return (1.2, 0.7)  # Moderate short
            else:
                return (1.1, 0.85)  # Light short

    def _place_grid(self, mid_price: float):
        """Place virtual grid orders with inventory-adjusted sizing"""
        self.buy_orders = []
        self.sell_orders = []
        self.grid_center = mid_price

        spread_bps = self._get_adjusted_spread()
        spread_pct = spread_bps / 10000
        buy_mult, sell_mult = self._get_inventory_skew()

        for i in range(1, self.num_levels + 1):
            # Buy orders below mid (with skew) - skip if multiplier is 0
            if buy_mult > 0:
                buy_price = mid_price * (1 - spread_pct * i)
                buy_size_usd = self.order_size_usd * buy_mult
                buy_size = buy_size_usd / buy_price
                self.buy_orders.append({
                    'price': buy_price,
                    'size': buy_size,
                    'size_usd': buy_size_usd,
                    'filled': False,
                    'level': i
                })

            # Sell orders above mid (with skew) - skip if multiplier is 0
            if sell_mult > 0:
                sell_price = mid_price * (1 + spread_pct * i)
                sell_size_usd = self.order_size_usd * sell_mult
                sell_size = sell_size_usd / sell_price
                self.sell_orders.append({
                    'price': sell_price,
                    'size': sell_size,
                    'size_usd': sell_size_usd,
                    'filled': False,
                    'level': i
                })

        if buy_mult != 1.0 or sell_mult != 1.0:
            buy_status = "DISABLED" if buy_mult == 0 else f"×{buy_mult:.2f}"
            sell_status = "DISABLED" if sell_mult == 0 else f"×{sell_mult:.2f}"
            logger.info(f"  🔄 Grid placed with skew: buys {buy_status}, sells {sell_status}")

    def _check_fills(self, bid: float, ask: float) -> List:
        """Check if any orders would have filled - v6 with order pause"""
        fills_this_cycle = []
        max_inventory = self.capital * (self.max_inventory_pct / 100)

        # v6: Update pause state based on ROC
        self._update_pause_state()

        # Check buy orders - SKIP ALL if buy orders are paused (downtrend)
        if not (self.orders_paused and self.pause_side == 'BUY'):
            for order in self.buy_orders:
                if not order['filled'] and bid <= order['price']:
                    # CRITICAL: Skip if this buy would push inventory over max
                    potential_notional = self.position_notional + (order['price'] * order['size'])
                    if self.position_size > 0 and potential_notional > max_inventory:
                        continue  # Skip - would exceed max long inventory

                    order['filled'] = True
                    fill_price = order['price']
                    fill_size = order['size']
                    notional = fill_price * fill_size

                    # Update position
                    if self.position_size >= 0:
                        total_cost = (self.position_avg_price * self.position_size) + (fill_price * fill_size)
                        self.position_size += fill_size
                        self.position_avg_price = total_cost / self.position_size if self.position_size > 0 else 0
                    else:
                        pnl = (self.position_avg_price - fill_price) * min(fill_size, abs(self.position_size))
                        self.realized_pnl += pnl
                        self.position_size += fill_size

                    self.position_notional = self.position_size * fill_price
                    self.total_volume += notional
                    fills_this_cycle.append(('BUY', fill_price, fill_size, notional))
                    self.fills.append({
                        'time': datetime.now(),
                        'side': 'BUY',
                        'price': fill_price,
                        'size': fill_size,
                        'notional': notional
                    })

        # Check sell orders - SKIP ALL if sell orders are paused (uptrend)
        if not (self.orders_paused and self.pause_side == 'SELL'):
            for order in self.sell_orders:
                if not order['filled'] and ask >= order['price']:
                    # CRITICAL: Skip if this sell would push inventory over max
                    potential_notional = self.position_notional - (order['price'] * order['size'])
                    if self.position_size < 0 and abs(potential_notional) > max_inventory:
                        continue  # Skip - would exceed max short inventory

                    order['filled'] = True
                    fill_price = order['price']
                    fill_size = order['size']
                    notional = fill_price * fill_size

                    if self.position_size <= 0:
                        total_cost = (self.position_avg_price * abs(self.position_size)) + (fill_price * fill_size)
                        self.position_size -= fill_size
                        self.position_avg_price = total_cost / abs(self.position_size) if self.position_size != 0 else 0
                    else:
                        pnl = (fill_price - self.position_avg_price) * min(fill_size, self.position_size)
                        self.realized_pnl += pnl
                        self.position_size -= fill_size

                    self.position_notional = self.position_size * fill_price
                    self.total_volume += notional
                    fills_this_cycle.append(('SELL', fill_price, fill_size, notional))
                    self.fills.append({
                        'time': datetime.now(),
                        'side': 'SELL',
                        'price': fill_price,
                        'size': fill_size,
                        'notional': notional
                    })

        return fills_this_cycle

    def _calculate_unrealized_pnl(self, mid_price: float) -> float:
        """Calculate unrealized P&L"""
        if self.position_size == 0:
            return 0.0
        elif self.position_size > 0:
            return (mid_price - self.position_avg_price) * self.position_size
        else:
            return (self.position_avg_price - mid_price) * abs(self.position_size)

    async def run(self):
        """Main loop"""
        await self.initialize()

        end_time = self.start_time + timedelta(minutes=self.duration_minutes)
        cycle = 0

        logger.info(f"\nStarting market making until {end_time.strftime('%H:%M:%S')}...")
        logger.info("-" * 70)

        consecutive_errors = 0
        max_consecutive_errors = 5

        try:
            while datetime.now() < end_time:
                cycle += 1

                # API call with retry logic
                try:
                    bbo = self.client.api_client.fetch_bbo(market=self.symbol)
                    consecutive_errors = 0  # Reset on success
                except Exception as e:
                    consecutive_errors += 1
                    logger.warning(f"  ⚠️ API error ({consecutive_errors}/{max_consecutive_errors}): {str(e)[:50]}")
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error("  ❌ Too many consecutive errors, stopping")
                        break
                    await asyncio.sleep(2 ** consecutive_errors)  # Exponential backoff
                    continue

                if not bbo:
                    await asyncio.sleep(1)
                    continue

                bid = float(bbo['bid'])
                ask = float(bbo['ask'])
                mid = (bid + ask) / 2
                spread_bps = (ask - bid) / mid * 10000

                # Update price and market spread history
                self.price_history.append(mid)
                self.market_spread_history.append(spread_bps)
                self.current_market_spread_bps = spread_bps

                # Check for fills
                fills = self._check_fills(bid, ask)
                for side, price, size, notional in fills:
                    logger.info(f"  ✅ FILL: {side} {size:.6f} @ ${price:,.2f} (${notional:,.2f})")

                # QWEN v7: Tighter force close thresholds
                # Use 6 bps threshold during pause, 3 bps normal (was 8/5)
                trend = self._calculate_trend()
                force_close_threshold = 6.0 if self.orders_paused else 3.0
                if abs(self.position_size) > 0:
                    # Short position in strong uptrend = BAD, force close
                    if self.position_size < 0 and trend > force_close_threshold:
                        close_price = ask  # Buy to close short at ask
                        close_size = abs(self.position_size)
                        close_notional = close_price * close_size
                        # Calculate P&L on forced close
                        pnl = (self.position_avg_price - close_price) * close_size
                        self.realized_pnl += pnl
                        self.total_volume += close_notional
                        logger.warning(f"  🛑 TREND CLOSE: BUY {close_size:.6f} @ ${close_price:,.2f} (trend: +{trend:.1f}bps, P&L: ${pnl:.2f})")
                        self.position_size = 0
                        self.position_avg_price = 0
                        self.position_notional = 0
                        self._place_grid(mid)  # Reset grid after force close
                    # Long position in strong downtrend = BAD, force close
                    elif self.position_size > 0 and trend < -force_close_threshold:
                        close_price = bid  # Sell to close long at bid
                        close_size = self.position_size
                        close_notional = close_price * close_size
                        # Calculate P&L on forced close
                        pnl = (close_price - self.position_avg_price) * close_size
                        self.realized_pnl += pnl
                        self.total_volume += close_notional
                        logger.warning(f"  🛑 TREND CLOSE: SELL {close_size:.6f} @ ${close_price:,.2f} (trend: {trend:.1f}bps, P&L: ${pnl:.2f})")
                        self.position_size = 0
                        self.position_avg_price = 0
                        self.position_notional = 0
                        self._place_grid(mid)  # Reset grid after force close

                # Check grid reset - price-based or inventory-based
                price_move_pct = abs(mid - self.grid_center) / self.grid_center * 100
                max_inventory = self.capital * (self.max_inventory_pct / 100)
                inventory_ratio = abs(self.position_notional) / max_inventory if max_inventory > 0 else 0

                # Force reset if: price moved too much OR inventory exceeds 60% of max
                needs_reset = price_move_pct >= self.grid_reset_pct
                inventory_force_reset = inventory_ratio > 0.6 and fills  # Only on new fills

                if needs_reset or inventory_force_reset:
                    self.grid_resets += 1
                    reason = f"Price moved {price_move_pct:.3f}%" if needs_reset else f"Inventory at {inventory_ratio*100:.0f}%"
                    logger.info(f"  🔄 RESET #{self.grid_resets}: {reason}")
                    self._place_grid(mid)

                # P&L calculation
                self.unrealized_pnl = self._calculate_unrealized_pnl(mid)
                total_pnl = self.realized_pnl + self.unrealized_pnl
                total_pnl_pct = total_pnl / self.initial_balance * 100

                # Stop loss check
                if total_pnl_pct <= -self.stop_loss_pct:
                    logger.warning(f"⚠️ STOP LOSS HIT: {total_pnl_pct:.2f}%")
                    break

                # Status log every 30 seconds
                if cycle % 30 == 0:
                    elapsed = (datetime.now() - self.start_time).total_seconds() / 60
                    vol = self._calculate_volatility()
                    inv_pct = abs(self.position_notional) / self.capital * 100
                    pause_status = f"⏸️{self.pause_side}" if self.orders_paused else "▶️"

                    logger.info(f"\n[{elapsed:.1f}m] BTC: ${mid:,.2f} | Spread: {spread_bps:.2f}bps | ROC: {self.roc_bps:+.2f}bps | {pause_status}")
                    logger.info(f"  Position: {self.position_size:.6f} BTC (${self.position_notional:,.0f} = {inv_pct:.1f}% inv)")
                    logger.info(f"  Volume: ${self.total_volume:,.2f} | Fills: {len(self.fills)} | Resets: {self.grid_resets}")
                    logger.info(f"  P&L: ${total_pnl:.2f} (Real: ${self.realized_pnl:.2f}, Unreal: ${self.unrealized_pnl:.2f})")

                    if self.total_volume > 0:
                        profit_per_10k = total_pnl / self.total_volume * 10000
                        logger.info(f"  📈 Profit per $10k vol: ${profit_per_10k:.2f}")

                await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("\nStopped by user")

        self._print_report()

    def _print_report(self):
        """Print final report"""
        elapsed = (datetime.now() - self.start_time).total_seconds() / 60
        total_pnl = self.realized_pnl + self.unrealized_pnl

        logger.info("\n" + "=" * 70)
        logger.info("GRID MARKET MAKER v8 - FINAL REPORT")
        logger.info("=" * 70)
        logger.info(f"Duration: {elapsed:.1f} minutes")
        logger.info(f"Total Volume: ${self.total_volume:,.2f}")
        logger.info(f"Total Fills: {len(self.fills)}")
        logger.info(f"Grid Resets: {self.grid_resets}")
        logger.info(f"Spread Adjustments: {self.spread_adjustments}")
        logger.info(f"Final Position: {self.position_size:.6f} BTC (${self.position_notional:,.2f})")
        logger.info(f"Realized P&L: ${self.realized_pnl:.2f}")
        logger.info(f"Unrealized P&L: ${self.unrealized_pnl:.2f}")
        logger.info(f"Total P&L: ${total_pnl:.2f} ({total_pnl/self.initial_balance*100:.3f}%)")

        if self.total_volume > 0:
            profit_per_10k = total_pnl / self.total_volume * 10000
            logger.info(f"Profit per $10k volume: ${profit_per_10k:.2f}")
            logger.info(f"📊 Extrapolated to $1M volume: ${total_pnl/self.total_volume*1_000_000:.2f}")

        logger.info("=" * 70)

        # Compare with v1
        v1_profit_per_10k = 0.48
        if self.total_volume > 0:
            improvement = (profit_per_10k / v1_profit_per_10k - 1) * 100 if v1_profit_per_10k > 0 else 0
            logger.info(f"\n📈 vs v1: ${profit_per_10k:.2f} vs ${v1_profit_per_10k:.2f} per $10k ({improvement:+.1f}% improvement)")

        # Save results
        os.makedirs('logs', exist_ok=True)
        with open('logs/grid_mm_v8_results.txt', 'w') as f:
            f.write(f"Grid Market Maker v8 Results - {datetime.now()}\n")
            f.write(f"Duration: {elapsed:.1f} minutes\n")
            f.write(f"Volume: ${self.total_volume:,.2f}\n")
            f.write(f"Fills: {len(self.fills)}\n")
            f.write(f"P&L: ${total_pnl:.2f}\n")
            f.write(f"Profit per $10k: ${profit_per_10k:.2f}\n" if self.total_volume > 0 else "")


async def main():
    # SCALED FOR $23 ACCOUNT (from $1000 v8 test)
    # v8 winning params: 1.5 bps spread, 1.0 bps ROC, 15s pause, 25% inventory
    # Scaling: $23/$1000 = 2.3% of original
    # Order size: $5 (was $250) - still reasonable for volume
    # Capital: $23 (actual account)
    mm = GridMarketMakerV2(
        symbol="BTC-USD-PERP",
        base_spread_bps=1.5,        # v8: KEEP 1.5 bps (v2-v4 proved widening doesn't help)
        grid_reset_pct=0.15,        # 0.15%
        stop_loss_pct=10.0,
        order_size_usd=5.0,         # Scaled for $23 account (was $250 for $1000)
        num_levels=6,               # v8: 6 levels - more depth
        duration_minutes=60,
        max_inventory_pct=25.0,     # v8: Max 25% inventory = $5.75 max position
        capital=23.0,               # $23 actual account
        volatility_window=30,
        volatility_multiplier=1.5,
    )
    await mm.run()


if __name__ == "__main__":
    asyncio.run(main())
