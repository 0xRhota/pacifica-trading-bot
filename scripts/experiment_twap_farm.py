#!/usr/bin/env python3
"""
Experiment 2: TWAP Volume Farming (Paper Trade)
Simulates TWAP-style execution to generate volume while staying market neutral

Strategy:
- Execute small market orders at regular intervals
- Alternate BUY/SELL to stay delta neutral
- Track slippage and P&L from the spread capture
- Duration: 1 hour
"""

import os
import sys
import time
import asyncio
import logging
import random
from datetime import datetime, timedelta
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

from paradex_py import Paradex


class TWAPVolumeFarmer:
    """
    Simulated TWAP Volume Farming
    Generates volume through regular small trades while staying market neutral
    """

    def __init__(
        self,
        symbol: str = "BTC-USD-PERP",
        order_size_usd: float = 50.0,       # $50 per sub-order
        interval_seconds: int = 30,          # Trade every 30s (like Paradex TWAP)
        stop_loss_pct: float = 10.0,         # Stop at 10% drawdown
        duration_minutes: int = 60,
        strategy: str = "alternating"        # alternating, random, or momentum
    ):
        self.symbol = symbol
        self.order_size_usd = order_size_usd
        self.interval_seconds = interval_seconds
        self.stop_loss_pct = stop_loss_pct
        self.duration_minutes = duration_minutes
        self.strategy = strategy

        # State
        self.client = None
        self.start_time = None
        self.initial_balance = 1000.0

        # Position tracking
        self.position_size = 0.0
        self.position_avg_price = 0.0

        # Stats
        self.total_volume = 0.0
        self.realized_pnl = 0.0
        self.trades: List[Dict] = []
        self.last_side = None

        # Price tracking for momentum
        self.price_history: List[float] = []

    async def initialize(self):
        """Initialize Paradex client"""
        logger.info("=" * 60)
        logger.info("TWAP VOLUME FARMER - PAPER TRADE")
        logger.info("=" * 60)
        logger.info(f"Symbol: {self.symbol}")
        logger.info(f"Order Size: ${self.order_size_usd}")
        logger.info(f"Interval: {self.interval_seconds}s")
        logger.info(f"Strategy: {self.strategy}")
        logger.info(f"Stop Loss: {self.stop_loss_pct}%")
        logger.info(f"Duration: {self.duration_minutes} minutes")
        logger.info("=" * 60)

        self.client = Paradex(env="prod")

        # Get initial price
        bbo = self.client.api_client.fetch_bbo(market=self.symbol)
        if not bbo:
            raise Exception(f"Cannot fetch BBO for {self.symbol}")

        mid = (float(bbo['bid']) + float(bbo['ask'])) / 2
        logger.info(f"Initial price: ${mid:,.2f}")

        self.start_time = datetime.now()

    def _get_next_side(self, mid_price: float) -> str:
        """Determine next trade side based on strategy"""
        if self.strategy == "alternating":
            # Simple alternation to stay neutral
            if self.last_side is None or self.last_side == "SELL":
                return "BUY"
            return "SELL"

        elif self.strategy == "random":
            # Random but track position to prevent too much drift
            if abs(self.position_size * mid_price) > self.order_size_usd * 3:
                # Too exposed, rebalance
                return "SELL" if self.position_size > 0 else "BUY"
            return random.choice(["BUY", "SELL"])

        elif self.strategy == "momentum":
            # Trade with short-term momentum
            self.price_history.append(mid_price)
            if len(self.price_history) < 5:
                return "BUY" if self.last_side != "BUY" else "SELL"

            # Keep last 20 prices
            self.price_history = self.price_history[-20:]
            recent = self.price_history[-5:]
            older = self.price_history[-10:-5] if len(self.price_history) >= 10 else self.price_history[:5]

            recent_avg = sum(recent) / len(recent)
            older_avg = sum(older) / len(older)

            # But also check position to stay neutral-ish
            if abs(self.position_size * mid_price) > self.order_size_usd * 5:
                return "SELL" if self.position_size > 0 else "BUY"

            return "BUY" if recent_avg > older_avg else "SELL"

        return "BUY"

    def _simulate_fill(self, side: str, bid: float, ask: float) -> Dict:
        """Simulate a market order fill with realistic slippage"""
        # Market orders: BUY hits ask, SELL hits bid
        if side == "BUY":
            # Simulate small slippage (0.01-0.05%)
            slippage = random.uniform(0.0001, 0.0005)
            fill_price = ask * (1 + slippage)
        else:
            slippage = random.uniform(0.0001, 0.0005)
            fill_price = bid * (1 - slippage)

        fill_size = self.order_size_usd / fill_price
        notional = fill_price * fill_size

        # Update position
        if side == "BUY":
            if self.position_size >= 0:
                # Adding to long
                total_cost = (self.position_avg_price * self.position_size) + (fill_price * fill_size)
                self.position_size += fill_size
                self.position_avg_price = total_cost / self.position_size if self.position_size > 0 else 0
            else:
                # Closing short
                close_size = min(fill_size, abs(self.position_size))
                pnl = (self.position_avg_price - fill_price) * close_size
                self.realized_pnl += pnl
                self.position_size += fill_size
                if self.position_size > 0:
                    self.position_avg_price = fill_price
        else:  # SELL
            if self.position_size <= 0:
                # Adding to short
                total_cost = (self.position_avg_price * abs(self.position_size)) + (fill_price * fill_size)
                self.position_size -= fill_size
                self.position_avg_price = total_cost / abs(self.position_size) if self.position_size != 0 else fill_price
            else:
                # Closing long
                close_size = min(fill_size, self.position_size)
                pnl = (fill_price - self.position_avg_price) * close_size
                self.realized_pnl += pnl
                self.position_size -= fill_size
                if self.position_size < 0:
                    self.position_avg_price = fill_price

        self.total_volume += notional
        self.last_side = side

        return {
            'time': datetime.now(),
            'side': side,
            'price': fill_price,
            'size': fill_size,
            'notional': notional,
            'slippage_bps': slippage * 10000
        }

    def _calculate_unrealized_pnl(self, mid_price: float) -> float:
        """Calculate unrealized P&L"""
        if self.position_size == 0:
            return 0.0
        elif self.position_size > 0:
            return (mid_price - self.position_avg_price) * self.position_size
        else:
            return (self.position_avg_price - mid_price) * abs(self.position_size)

    async def run(self):
        """Main trading loop"""
        await self.initialize()

        end_time = self.start_time + timedelta(minutes=self.duration_minutes)
        trade_count = 0

        logger.info(f"\nStarting TWAP farming until {end_time.strftime('%H:%M:%S')}...")
        logger.info(f"Expected trades: ~{self.duration_minutes * 60 // self.interval_seconds}")
        logger.info("-" * 60)

        try:
            while datetime.now() < end_time:
                # Fetch current BBO
                bbo = self.client.api_client.fetch_bbo(market=self.symbol)
                if not bbo:
                    await asyncio.sleep(1)
                    continue

                bid = float(bbo['bid'])
                ask = float(bbo['ask'])
                mid = (bid + ask) / 2
                spread_bps = (ask - bid) / mid * 10000

                # Determine side and execute
                side = self._get_next_side(mid)
                fill = self._simulate_fill(side, bid, ask)
                trade_count += 1
                self.trades.append(fill)

                # Calculate P&L
                unrealized_pnl = self._calculate_unrealized_pnl(mid)
                total_pnl = self.realized_pnl + unrealized_pnl
                total_pnl_pct = total_pnl / self.initial_balance * 100

                # Log trade
                elapsed = (datetime.now() - self.start_time).total_seconds() / 60
                logger.info(
                    f"[{elapsed:.1f}m] #{trade_count} {side} ${fill['notional']:.2f} @ ${fill['price']:,.2f} | "
                    f"Pos: {self.position_size:.6f} | P&L: ${total_pnl:.2f}"
                )

                # Check stop loss
                if total_pnl_pct <= -self.stop_loss_pct:
                    logger.warning(f"STOP LOSS HIT: {total_pnl_pct:.2f}%")
                    break

                # Wait for next interval
                await asyncio.sleep(self.interval_seconds)

        except KeyboardInterrupt:
            logger.info("\nStopped by user")

        # Close any remaining position at end
        if abs(self.position_size) > 0.000001:
            logger.info(f"\nClosing remaining position: {self.position_size:.6f}")
            bbo = self.client.api_client.fetch_bbo(market=self.symbol)
            if bbo:
                bid = float(bbo['bid'])
                ask = float(bbo['ask'])
                mid = (bid + ask) / 2
                close_side = "SELL" if self.position_size > 0 else "BUY"

                # Simulate close
                if close_side == "SELL":
                    close_price = bid * 0.9999  # Small slippage
                    pnl = (close_price - self.position_avg_price) * self.position_size
                else:
                    close_price = ask * 1.0001
                    pnl = (self.position_avg_price - close_price) * abs(self.position_size)

                self.realized_pnl += pnl
                self.total_volume += abs(self.position_size) * close_price
                self.position_size = 0

        self._print_report()

    def _print_report(self):
        """Print final report"""
        elapsed = (datetime.now() - self.start_time).total_seconds() / 60

        logger.info("\n" + "=" * 60)
        logger.info("TWAP VOLUME FARMER - FINAL REPORT")
        logger.info("=" * 60)
        logger.info(f"Duration: {elapsed:.1f} minutes")
        logger.info(f"Strategy: {self.strategy}")
        logger.info(f"Total Trades: {len(self.trades)}")
        logger.info(f"Total Volume: ${self.total_volume:,.2f}")
        logger.info(f"Avg Trade Size: ${self.total_volume/len(self.trades) if self.trades else 0:,.2f}")
        logger.info(f"Final Position: {self.position_size:.6f} BTC")
        logger.info(f"Realized P&L: ${self.realized_pnl:.2f}")
        logger.info(f"Total P&L: ${self.realized_pnl:.2f} ({self.realized_pnl/self.initial_balance*100:.3f}%)")

        if self.total_volume > 0:
            profit_per_volume = self.realized_pnl / self.total_volume * 10000
            logger.info(f"Profit per $10k volume: ${profit_per_volume:.2f}")

        # Calculate avg slippage
        if self.trades:
            avg_slippage = sum(t['slippage_bps'] for t in self.trades) / len(self.trades)
            logger.info(f"Avg Slippage: {avg_slippage:.2f} bps")

        logger.info("=" * 60)

        # Extrapolate to $1M volume
        if self.total_volume > 0:
            profit_at_1m = (self.realized_pnl / self.total_volume) * 1_000_000
            logger.info(f"\n📊 EXTRAPOLATED TO $1M VOLUME: ${profit_at_1m:.2f}")
        logger.info("=" * 60)

        # Save results
        with open('logs/twap_farm_results.txt', 'w') as f:
            f.write(f"TWAP Volume Farmer Results - {datetime.now()}\n")
            f.write(f"Duration: {elapsed:.1f} minutes\n")
            f.write(f"Strategy: {self.strategy}\n")
            f.write(f"Trades: {len(self.trades)}\n")
            f.write(f"Volume: ${self.total_volume:,.2f}\n")
            f.write(f"P&L: ${self.realized_pnl:.2f}\n")


async def main():
    farmer = TWAPVolumeFarmer(
        symbol="BTC-USD-PERP",
        order_size_usd=50.0,        # $50 per trade
        interval_seconds=30,         # Every 30s like Paradex TWAP
        stop_loss_pct=10.0,          # 10% stop loss
        duration_minutes=60,         # 1 hour
        strategy="alternating"       # Stay market neutral
    )
    await farmer.run()


if __name__ == "__main__":
    asyncio.run(main())
