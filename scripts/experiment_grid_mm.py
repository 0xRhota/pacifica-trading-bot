#!/usr/bin/env python3
"""
Experiment 1: Grid Market Maker (Paper Trade)
Places simulated limit orders on both sides of mid price
Tracks fills based on real BBO data

Settings (matching the claimed strategy):
- Spread: +1 bps from mid
- Grid Reset: 0.25% price movement
- Stop Loss: 10% drawdown
- Duration: 1 hour
"""

import os
import sys
import time
import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, '.env'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Paradex client setup
from paradex_py import Paradex
from paradex_py.common.order import OrderSide


class GridMarketMaker:
    """
    Simulated Grid Market Maker
    Places virtual limit orders and tracks fills based on real price movement
    """

    def __init__(
        self,
        symbol: str = "BTC-USD-PERP",
        grid_spread_bps: float = 1.0,      # 1 bps = 0.01%
        grid_reset_pct: float = 0.25,      # Reset grid if price moves 0.25%
        stop_loss_pct: float = 10.0,       # Stop at 10% drawdown
        order_size_usd: float = 100.0,     # $100 per order
        num_levels: int = 3,               # Orders on each side
        duration_minutes: int = 60
    ):
        self.symbol = symbol
        self.grid_spread_bps = grid_spread_bps
        self.grid_reset_pct = grid_reset_pct
        self.stop_loss_pct = stop_loss_pct
        self.order_size_usd = order_size_usd
        self.num_levels = num_levels
        self.duration_minutes = duration_minutes

        # State
        self.client = None
        self.grid_center = None
        self.buy_orders: List[Dict] = []   # {price, size, filled}
        self.sell_orders: List[Dict] = []

        # Stats
        self.total_volume = 0.0
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.fills = []
        self.start_time = None
        self.initial_balance = 1000.0  # Simulated starting balance

        # Position tracking
        self.position_size = 0.0
        self.position_avg_price = 0.0

    async def initialize(self):
        """Initialize Paradex client"""
        logger.info("=" * 60)
        logger.info("GRID MARKET MAKER - PAPER TRADE")
        logger.info("=" * 60)
        logger.info(f"Symbol: {self.symbol}")
        logger.info(f"Spread: {self.grid_spread_bps} bps")
        logger.info(f"Grid Reset: {self.grid_reset_pct}%")
        logger.info(f"Stop Loss: {self.stop_loss_pct}%")
        logger.info(f"Order Size: ${self.order_size_usd}")
        logger.info(f"Levels: {self.num_levels} per side")
        logger.info(f"Duration: {self.duration_minutes} minutes")
        logger.info("=" * 60)

        # Initialize Paradex (read-only, just for BBO data)
        self.client = Paradex(env="prod")

        # Get initial price
        bbo = self.client.api_client.fetch_bbo(market=self.symbol)
        if not bbo:
            raise Exception(f"Cannot fetch BBO for {self.symbol}")

        mid = (float(bbo['bid']) + float(bbo['ask'])) / 2
        logger.info(f"Initial mid price: ${mid:,.2f}")

        self.grid_center = mid
        self.start_time = datetime.now()

        # Place initial grid
        self._place_grid(mid)

    def _place_grid(self, mid_price: float):
        """Place virtual grid orders around mid price"""
        self.buy_orders = []
        self.sell_orders = []
        self.grid_center = mid_price

        spread_pct = self.grid_spread_bps / 10000  # Convert bps to decimal

        for i in range(1, self.num_levels + 1):
            # Buy orders below mid
            buy_price = mid_price * (1 - spread_pct * i)
            buy_size = self.order_size_usd / buy_price
            self.buy_orders.append({
                'price': buy_price,
                'size': buy_size,
                'filled': False,
                'level': i
            })

            # Sell orders above mid
            sell_price = mid_price * (1 + spread_pct * i)
            sell_size = self.order_size_usd / sell_price
            self.sell_orders.append({
                'price': sell_price,
                'size': sell_size,
                'filled': False,
                'level': i
            })

        logger.info(f"Grid placed: {len(self.buy_orders)} buys, {len(self.sell_orders)} sells around ${mid_price:,.2f}")

    def _check_fills(self, bid: float, ask: float):
        """Check if any orders would have filled"""
        fills_this_cycle = []

        # Check buy orders (fill if bid drops to our buy price)
        for order in self.buy_orders:
            if not order['filled'] and bid <= order['price']:
                order['filled'] = True
                fill_price = order['price']
                fill_size = order['size']
                notional = fill_price * fill_size

                # Update position
                if self.position_size >= 0:
                    # Adding to long or opening long
                    total_cost = (self.position_avg_price * self.position_size) + (fill_price * fill_size)
                    self.position_size += fill_size
                    self.position_avg_price = total_cost / self.position_size if self.position_size > 0 else 0
                else:
                    # Closing short
                    pnl = (self.position_avg_price - fill_price) * min(fill_size, abs(self.position_size))
                    self.realized_pnl += pnl
                    self.position_size += fill_size

                self.total_volume += notional
                fills_this_cycle.append(('BUY', fill_price, fill_size, notional))
                self.fills.append({
                    'time': datetime.now(),
                    'side': 'BUY',
                    'price': fill_price,
                    'size': fill_size,
                    'notional': notional
                })

        # Check sell orders (fill if ask rises to our sell price)
        for order in self.sell_orders:
            if not order['filled'] and ask >= order['price']:
                order['filled'] = True
                fill_price = order['price']
                fill_size = order['size']
                notional = fill_price * fill_size

                # Update position
                if self.position_size <= 0:
                    # Adding to short or opening short
                    total_cost = (self.position_avg_price * abs(self.position_size)) + (fill_price * fill_size)
                    self.position_size -= fill_size
                    self.position_avg_price = total_cost / abs(self.position_size) if self.position_size != 0 else 0
                else:
                    # Closing long
                    pnl = (fill_price - self.position_avg_price) * min(fill_size, self.position_size)
                    self.realized_pnl += pnl
                    self.position_size -= fill_size

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

    def _calculate_unrealized_pnl(self, mid_price: float):
        """Calculate unrealized P&L on current position"""
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
        logger.info("-" * 60)

        try:
            while datetime.now() < end_time:
                cycle += 1

                # Fetch current BBO
                bbo = self.client.api_client.fetch_bbo(market=self.symbol)
                if not bbo:
                    await asyncio.sleep(1)
                    continue

                bid = float(bbo['bid'])
                ask = float(bbo['ask'])
                mid = (bid + ask) / 2
                spread_bps = (ask - bid) / mid * 10000

                # Check for fills
                fills = self._check_fills(bid, ask)
                for side, price, size, notional in fills:
                    logger.info(f"  FILL: {side} {size:.6f} @ ${price:,.2f} (${notional:,.2f})")

                # Check if grid needs reset (price moved too far)
                price_move_pct = abs(mid - self.grid_center) / self.grid_center * 100
                if price_move_pct >= self.grid_reset_pct:
                    logger.info(f"  RESET: Price moved {price_move_pct:.3f}% from grid center")
                    self._place_grid(mid)

                # Calculate P&L
                self.unrealized_pnl = self._calculate_unrealized_pnl(mid)
                total_pnl = self.realized_pnl + self.unrealized_pnl
                total_pnl_pct = total_pnl / self.initial_balance * 100

                # Check stop loss
                if total_pnl_pct <= -self.stop_loss_pct:
                    logger.warning(f"STOP LOSS HIT: {total_pnl_pct:.2f}%")
                    break

                # Log status every 30 seconds
                if cycle % 30 == 0:
                    elapsed = (datetime.now() - self.start_time).total_seconds() / 60
                    logger.info(f"\n[{elapsed:.1f}m] BTC: ${mid:,.2f} | Spread: {spread_bps:.2f}bps")
                    logger.info(f"  Position: {self.position_size:.6f} BTC @ ${self.position_avg_price:,.2f}")
                    logger.info(f"  Volume: ${self.total_volume:,.2f} | Fills: {len(self.fills)}")
                    logger.info(f"  P&L: ${total_pnl:.2f} (Real: ${self.realized_pnl:.2f}, Unreal: ${self.unrealized_pnl:.2f})")

                await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("\nStopped by user")

        # Final report
        self._print_report()

    def _print_report(self):
        """Print final report"""
        elapsed = (datetime.now() - self.start_time).total_seconds() / 60
        total_pnl = self.realized_pnl + self.unrealized_pnl

        logger.info("\n" + "=" * 60)
        logger.info("GRID MARKET MAKER - FINAL REPORT")
        logger.info("=" * 60)
        logger.info(f"Duration: {elapsed:.1f} minutes")
        logger.info(f"Total Volume: ${self.total_volume:,.2f}")
        logger.info(f"Total Fills: {len(self.fills)}")
        logger.info(f"Final Position: {self.position_size:.6f} BTC")
        logger.info(f"Realized P&L: ${self.realized_pnl:.2f}")
        logger.info(f"Unrealized P&L: ${self.unrealized_pnl:.2f}")
        logger.info(f"Total P&L: ${total_pnl:.2f} ({total_pnl/self.initial_balance*100:.3f}%)")

        if self.total_volume > 0:
            profit_per_volume = total_pnl / self.total_volume * 10000
            logger.info(f"Profit per $10k volume: ${profit_per_volume:.2f}")

        logger.info("=" * 60)

        # Save results
        with open('logs/grid_mm_results.txt', 'w') as f:
            f.write(f"Grid Market Maker Results - {datetime.now()}\n")
            f.write(f"Duration: {elapsed:.1f} minutes\n")
            f.write(f"Volume: ${self.total_volume:,.2f}\n")
            f.write(f"Fills: {len(self.fills)}\n")
            f.write(f"P&L: ${total_pnl:.2f}\n")


async def main():
    mm = GridMarketMaker(
        symbol="BTC-USD-PERP",
        grid_spread_bps=1.0,       # +1 bps spread
        grid_reset_pct=0.25,       # Reset at 0.25% move
        stop_loss_pct=10.0,        # 10% stop loss
        order_size_usd=100.0,      # $100 per order
        num_levels=3,              # 3 orders each side
        duration_minutes=60        # 1 hour
    )
    await mm.run()


if __name__ == "__main__":
    asyncio.run(main())
