"""
Funding Arbitrage Engine
========================
Main engine that orchestrates the delta-neutral funding rate arbitrage strategy.

Timing Strategy (from user requirements):
- Scan interval: 15-30 minutes (funding settles every 8h, no need for frequent checks)
- Position rotation: Every 1-2 hours to generate volume
- Goal: Maximize volume while capturing funding rate differential
"""

import asyncio
import logging
import random
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict

from funding_arb_agent.exchanges.base import ExchangeAdapter
from .config import ArbConfig
from .position_manager import PositionManager, FundingSpread

logger = logging.getLogger(__name__)


class FundingArbitrageEngine:
    """
    Main engine for delta-neutral funding rate arbitrage.

    Strategy:
    1. Monitor funding rates on both exchanges
    2. When spread > threshold: SHORT high-rate, LONG low-rate
    3. Collect funding differential every 8 hours
    4. Rotate positions periodically to generate volume
    5. Maintain strict delta neutrality

    Volume Generation:
    - Each rotation = 4 trades (2 close + 2 open)
    - Rotation every 1 hour with $100 positions = ~$9,600 daily volume per symbol
    """

    def __init__(
        self,
        exchange_a: ExchangeAdapter,
        exchange_b: ExchangeAdapter,
        config: Optional[ArbConfig] = None
    ):
        self.exchange_a = exchange_a
        self.exchange_b = exchange_b
        self.config = config or ArbConfig()

        self.position_manager = PositionManager(exchange_a, exchange_b, self.config)

        # Timing
        self.last_scan_time: Optional[datetime] = None
        self.last_rotation_time: Dict[str, datetime] = {}

        # State
        self.running = False
        self.initialized = False

        # Stats
        self.cycles_completed = 0
        self.errors_count = 0

    async def initialize(self) -> bool:
        """Initialize both exchange connections"""
        try:
            logger.info("=" * 60)
            logger.info("FUNDING ARBITRAGE ENGINE INITIALIZING")
            logger.info("=" * 60)

            # Initialize exchanges
            logger.info(f"Initializing {self.exchange_a.name}...")
            if not await self.exchange_a.initialize():
                logger.error(f"Failed to initialize {self.exchange_a.name}")
                return False

            logger.info(f"Initializing {self.exchange_b.name}...")
            if not await self.exchange_b.initialize():
                logger.error(f"Failed to initialize {self.exchange_b.name}")
                return False

            # Log configuration
            logger.info("")
            logger.info("Configuration:")
            logger.info(f"  Scan interval: {self.config.scan_interval}s ({self.config.scan_interval/60:.1f} min)")
            logger.info(f"  Rotation interval: {self.config.rotation_interval}s ({self.config.rotation_interval/60:.1f} min)")
            logger.info(f"  Position size: ${self.config.position_size_usd:.2f} per leg")
            logger.info(f"  Min spread: {self.config.min_spread_threshold:.2f}% annualized")
            logger.info(f"  Symbols: {', '.join(self.config.symbols)}")
            logger.info(f"  Mode: {'DRY RUN' if self.config.dry_run else 'LIVE'}")
            logger.info("")

            # Get initial balances
            bal_a = await self.exchange_a.get_balance()
            bal_b = await self.exchange_b.get_balance()

            logger.info("Account Balances:")
            if bal_a:
                logger.info(f"  {self.exchange_a.name}: ${bal_a.equity:.2f}")
            if bal_b:
                logger.info(f"  {self.exchange_b.name}: ${bal_b.equity:.2f}")

            self.initialized = True
            logger.info("")
            logger.info("Engine initialized successfully!")
            return True

        except Exception as e:
            logger.error(f"Initialization error: {e}")
            return False

    async def shutdown(self) -> None:
        """Clean shutdown"""
        logger.info("Shutting down arbitrage engine...")
        self.running = False

        # Close positions if needed (optional - could keep them)
        # for symbol in list(self.position_manager.arb_positions.keys()):
        #     await self.position_manager.close_arb_position(symbol)

        await self.exchange_a.close()
        await self.exchange_b.close()

        # Log final stats
        stats = self.position_manager.get_session_stats()
        logger.info("")
        logger.info("=" * 60)
        logger.info("SESSION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"  Duration: {stats['session_duration_hours']:.2f} hours")
        logger.info(f"  Total Volume: ${stats['total_volume_usd']:,.2f}")
        logger.info(f"  Volume/Hour: ${stats['volume_per_hour']:,.2f}")
        logger.info(f"  Cycles: {self.cycles_completed}")
        logger.info(f"  Errors: {self.errors_count}")
        logger.info("=" * 60)

    async def scan_opportunities(self) -> Dict[str, FundingSpread]:
        """
        Scan for arbitrage opportunities across all symbols.
        Returns spreads that meet the threshold.
        """
        viable_spreads = {}
        all_spreads = await self.position_manager.get_all_spreads()

        logger.info("")
        logger.info("-" * 60)
        logger.info("FUNDING RATE SCAN")
        logger.info("-" * 60)
        logger.info(f"{'Symbol':<8} {self.exchange_a.name:<12} {self.exchange_b.name:<12} {'Spread':<12} {'Status':<10}")
        logger.info("-" * 60)

        for symbol, spread in all_spreads.items():
            status = "VIABLE" if spread.annualized_spread >= self.config.min_spread_threshold else "LOW"

            logger.info(
                f"{symbol:<8} "
                f"{spread.rate_a:>10.6f}  "
                f"{spread.rate_b:>10.6f}  "
                f"{spread.annualized_spread:>10.2f}%  "
                f"{status:<10}"
            )

            if spread.annualized_spread >= self.config.min_spread_threshold:
                viable_spreads[symbol] = spread

        logger.info("-" * 60)
        logger.info(f"Viable opportunities: {len(viable_spreads)}/{len(all_spreads)}")

        return viable_spreads

    async def manage_positions(self, spreads: Dict[str, FundingSpread]) -> None:
        """
        Manage positions based on current spreads.

        1. Open new positions for viable spreads
        2. Close positions if spread drops below threshold
        3. Rebalance if delta drifts
        """
        now = datetime.now(timezone.utc)

        # Check existing positions
        for symbol in list(self.position_manager.arb_positions.keys()):
            spread = spreads.get(symbol)

            if not spread or spread.annualized_spread < self.config.close_spread_threshold:
                # Spread too low - close position
                logger.info(f"{symbol}: Spread dropped below threshold, closing position")
                success, msg = await self.position_manager.close_arb_position(symbol)
                logger.info(f"  Result: {msg}")
            else:
                # Check delta balance
                await self.position_manager.rebalance_if_needed(symbol)

        # Open new positions for viable spreads
        for symbol, spread in spreads.items():
            if symbol not in self.position_manager.arb_positions:
                # Calculate available size
                total_position_value = sum(
                    p.total_notional for p in self.position_manager.arb_positions.values()
                )
                remaining_capacity = self.config.max_total_position_usd - total_position_value

                if remaining_capacity >= self.config.position_size_usd:
                    size = min(self.config.position_size_usd, remaining_capacity)
                    success, msg = await self.position_manager.open_arb_position(
                        symbol, spread, size
                    )
                    logger.info(f"  {msg}")

    async def rotate_for_volume(self) -> None:
        """
        Rotate positions to generate trading volume.

        This is key for the volume generation strategy:
        - Close and reopen positions periodically
        - Each rotation = 4 trades across both exchanges
        - Maintains same exposure while generating volume
        """
        if not self.config.enable_rotation:
            return

        now = datetime.now(timezone.utc)

        for symbol, arb in list(self.position_manager.arb_positions.items()):
            # Check if it's time to rotate
            last_rotation = self.last_rotation_time.get(symbol) or arb.last_rotated

            # Add jitter to avoid predictable patterns
            jitter = random.randint(-self.config.rotation_jitter, self.config.rotation_jitter)
            rotation_due = last_rotation + timedelta(seconds=self.config.rotation_interval + jitter)

            if now >= rotation_due:
                logger.info(f"Rotating {symbol} for volume generation...")
                success, msg = await self.position_manager.rotate_position(symbol)
                logger.info(f"  {msg}")

                if success:
                    self.last_rotation_time[symbol] = now

    async def run_cycle(self) -> None:
        """
        Run a single arbitrage cycle.
        """
        try:
            self.cycles_completed += 1
            now = datetime.now(timezone.utc)

            logger.info("")
            logger.info("=" * 60)
            logger.info(f"CYCLE #{self.cycles_completed} - {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            logger.info("=" * 60)

            # 1. Sync positions from exchanges
            await self.position_manager.sync_positions()

            # 2. Scan for opportunities
            spreads = await self.scan_opportunities()

            # 3. Manage positions (open/close based on spreads)
            await self.manage_positions(spreads)

            # 4. Rotate positions for volume
            await self.rotate_for_volume()

            # 5. Log status
            self._log_status()

            self.last_scan_time = now

        except Exception as e:
            logger.error(f"Cycle error: {e}")
            self.errors_count += 1

    def _log_status(self) -> None:
        """Log current status summary"""
        stats = self.position_manager.get_session_stats()

        logger.info("")
        logger.info("-" * 60)
        logger.info("STATUS")
        logger.info("-" * 60)
        logger.info(f"  Active positions: {stats['active_positions']}")
        logger.info(f"  Session volume: ${stats['total_volume_usd']:,.2f}")
        logger.info(f"  Volume/hour: ${stats['volume_per_hour']:,.2f}")

        for symbol, arb in self.position_manager.arb_positions.items():
            logger.info(f"  {symbol}: SHORT ${arb.short_size_usd:.2f} on {arb.short_exchange}, "
                       f"LONG ${arb.long_size_usd:.2f} on {arb.long_exchange}")

        logger.info("-" * 60)

    async def run(self) -> None:
        """
        Main run loop.
        """
        if not self.initialized:
            if not await self.initialize():
                return

        self.running = True
        logger.info(f"Starting arbitrage engine (interval: {self.config.scan_interval}s)")

        try:
            while self.running:
                await self.run_cycle()

                # Wait for next cycle
                logger.info(f"Next scan in {self.config.scan_interval}s...")
                await asyncio.sleep(self.config.scan_interval)

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            await self.shutdown()

    async def run_once(self) -> None:
        """Run a single cycle (for testing)"""
        if not self.initialized:
            if not await self.initialize():
                return

        await self.run_cycle()
        await self.shutdown()
