"""
Position Manager
================
Manages delta-neutral positions across two exchanges.
Ensures positions stay balanced and handles rebalancing.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Tuple
from datetime import datetime, timezone

from funding_arb_agent.exchanges.base import (
    ExchangeAdapter, Position, Side, FundingInfo
)
from .config import ArbConfig

logger = logging.getLogger(__name__)


@dataclass
class ArbPosition:
    """
    Represents a delta-neutral arbitrage position across two exchanges.

    For funding arbitrage:
    - One exchange has SHORT (receives funding when rate > 0)
    - Other exchange has LONG (pays funding when rate > 0)
    - Net delta = 0 (market neutral)
    """
    symbol: str
    short_exchange: str  # Exchange name where we're SHORT
    long_exchange: str   # Exchange name where we're LONG
    short_position: Optional[Position]
    long_position: Optional[Position]
    opened_at: datetime
    last_rotated: datetime

    @property
    def short_size_usd(self) -> float:
        return self.short_position.notional_value if self.short_position else 0

    @property
    def long_size_usd(self) -> float:
        return self.long_position.notional_value if self.long_position else 0

    @property
    def delta_imbalance(self) -> float:
        """Net delta exposure in USD (should be near 0)"""
        return self.long_size_usd - self.short_size_usd

    @property
    def total_notional(self) -> float:
        """Total notional value (both legs)"""
        return self.short_size_usd + self.long_size_usd

    @property
    def is_balanced(self) -> bool:
        """Check if position is reasonably balanced"""
        if self.total_notional == 0:
            return True
        imbalance_pct = abs(self.delta_imbalance) / self.total_notional
        return imbalance_pct < 0.1  # Within 10%


@dataclass
class FundingSpread:
    """Funding rate spread between two exchanges"""
    symbol: str
    exchange_a: str
    exchange_b: str
    rate_a: float  # Funding rate on exchange A
    rate_b: float  # Funding rate on exchange B
    spread: float  # rate_a - rate_b
    annualized_spread: float  # Spread annualized (%)

    @property
    def short_exchange(self) -> str:
        """Exchange to SHORT (higher rate = receive more funding)"""
        return self.exchange_a if self.rate_a > self.rate_b else self.exchange_b

    @property
    def long_exchange(self) -> str:
        """Exchange to LONG (lower rate = pay less funding)"""
        return self.exchange_b if self.rate_a > self.rate_b else self.exchange_a


class PositionManager:
    """
    Manages delta-neutral arbitrage positions.

    Responsibilities:
    1. Track positions on both exchanges
    2. Calculate funding spreads
    3. Open/close/rotate positions
    4. Maintain delta neutrality
    """

    def __init__(
        self,
        exchange_a: ExchangeAdapter,
        exchange_b: ExchangeAdapter,
        config: ArbConfig
    ):
        self.exchange_a = exchange_a
        self.exchange_b = exchange_b
        self.config = config

        # Track active arbitrage positions
        self.arb_positions: Dict[str, ArbPosition] = {}

        # Track last trade times per symbol
        self.last_trade_times: Dict[str, datetime] = {}

        # Volume tracking
        self.total_volume_usd: float = 0
        self.session_start: datetime = datetime.now(timezone.utc)

    async def get_funding_spread(self, symbol: str) -> Optional[FundingSpread]:
        """
        Calculate funding rate spread for a symbol between both exchanges.
        """
        try:
            # Get funding info from both exchanges
            info_a = await self.exchange_a.get_funding_info(symbol)
            info_b = await self.exchange_b.get_funding_info(symbol)

            if not info_a or not info_b:
                return None

            spread = info_a.funding_rate - info_b.funding_rate
            annualized = abs(spread) * 1095 * 100  # Annualized %

            return FundingSpread(
                symbol=symbol,
                exchange_a=self.exchange_a.name,
                exchange_b=self.exchange_b.name,
                rate_a=info_a.funding_rate,
                rate_b=info_b.funding_rate,
                spread=spread,
                annualized_spread=annualized
            )

        except Exception as e:
            logger.error(f"Error calculating funding spread for {symbol}: {e}")
            return None

    async def get_all_spreads(self) -> Dict[str, FundingSpread]:
        """Get funding spreads for all configured symbols"""
        spreads = {}
        for symbol in self.config.symbols:
            spread = await self.get_funding_spread(symbol)
            if spread:
                spreads[symbol] = spread
        return spreads

    async def sync_positions(self) -> None:
        """
        Sync internal position tracking with actual exchange positions.
        """
        for symbol in self.config.symbols:
            pos_a = await self.exchange_a.get_position(symbol)
            pos_b = await self.exchange_b.get_position(symbol)

            # Determine which is SHORT and which is LONG
            if pos_a and pos_b:
                if pos_a.side == Side.SHORT:
                    short_ex, long_ex = self.exchange_a.name, self.exchange_b.name
                    short_pos, long_pos = pos_a, pos_b
                else:
                    short_ex, long_ex = self.exchange_b.name, self.exchange_a.name
                    short_pos, long_pos = pos_b, pos_a

                if symbol not in self.arb_positions:
                    self.arb_positions[symbol] = ArbPosition(
                        symbol=symbol,
                        short_exchange=short_ex,
                        long_exchange=long_ex,
                        short_position=short_pos,
                        long_position=long_pos,
                        opened_at=datetime.now(timezone.utc),
                        last_rotated=datetime.now(timezone.utc)
                    )
                else:
                    # Update existing
                    arb = self.arb_positions[symbol]
                    arb.short_position = short_pos if arb.short_exchange == self.exchange_a.name else long_pos
                    arb.long_position = long_pos if arb.long_exchange == self.exchange_a.name else short_pos

            elif symbol in self.arb_positions:
                # Positions closed
                del self.arb_positions[symbol]

    async def open_arb_position(
        self,
        symbol: str,
        spread: FundingSpread,
        size_usd: float
    ) -> Tuple[bool, str]:
        """
        Open a delta-neutral arbitrage position.

        Opens SHORT on high-rate exchange, LONG on low-rate exchange.
        """
        try:
            # Check cooldown
            if symbol in self.last_trade_times:
                elapsed = (datetime.now(timezone.utc) - self.last_trade_times[symbol]).total_seconds()
                if elapsed < self.config.min_trade_interval:
                    return False, f"Cooldown: {self.config.min_trade_interval - elapsed:.0f}s remaining"

            # Determine exchanges
            short_adapter = self.exchange_a if spread.short_exchange == self.exchange_a.name else self.exchange_b
            long_adapter = self.exchange_b if spread.short_exchange == self.exchange_a.name else self.exchange_a

            logger.info(f"Opening arb position for {symbol}:")
            logger.info(f"  SHORT ${size_usd:.2f} on {short_adapter.name} (rate: {spread.rate_a if spread.short_exchange == self.exchange_a.name else spread.rate_b:.6f})")
            logger.info(f"  LONG  ${size_usd:.2f} on {long_adapter.name} (rate: {spread.rate_b if spread.short_exchange == self.exchange_a.name else spread.rate_a:.6f})")
            logger.info(f"  Spread: {spread.annualized_spread:.2f}% annualized")

            if self.config.dry_run:
                logger.info("  [DRY RUN] No orders placed")
                self.total_volume_usd += size_usd * 2
                self.last_trade_times[symbol] = datetime.now(timezone.utc)
                return True, "Dry run - positions simulated"

            # Open both positions (attempt simultaneously)
            # SHORT on high-rate exchange
            short_result = await short_adapter.open_position(symbol, Side.SHORT, size_usd)
            if not short_result.success:
                return False, f"Failed to open SHORT on {short_adapter.name}: {short_result.error}"

            # LONG on low-rate exchange
            long_result = await long_adapter.open_position(symbol, Side.LONG, size_usd)
            if not long_result.success:
                # Attempt to close the SHORT we just opened
                logger.error(f"Failed to open LONG on {long_adapter.name}, closing SHORT...")
                await short_adapter.close_position(symbol)
                return False, f"Failed to open LONG on {long_adapter.name}: {long_result.error}"

            # Track volume
            self.total_volume_usd += (short_result.filled_size * short_result.filled_price +
                                      long_result.filled_size * long_result.filled_price)

            # Update tracking
            self.last_trade_times[symbol] = datetime.now(timezone.utc)

            # Create arb position record
            self.arb_positions[symbol] = ArbPosition(
                symbol=symbol,
                short_exchange=short_adapter.name,
                long_exchange=long_adapter.name,
                short_position=await short_adapter.get_position(symbol),
                long_position=await long_adapter.get_position(symbol),
                opened_at=datetime.now(timezone.utc),
                last_rotated=datetime.now(timezone.utc)
            )

            return True, f"Opened {symbol} arb: SHORT on {short_adapter.name}, LONG on {long_adapter.name}"

        except Exception as e:
            logger.error(f"Error opening arb position: {e}")
            return False, str(e)

    async def close_arb_position(self, symbol: str) -> Tuple[bool, str]:
        """
        Close both legs of an arbitrage position.
        """
        try:
            if symbol not in self.arb_positions:
                return True, "No position to close"

            arb = self.arb_positions[symbol]

            # Get adapters
            short_adapter = self.exchange_a if arb.short_exchange == self.exchange_a.name else self.exchange_b
            long_adapter = self.exchange_b if arb.short_exchange == self.exchange_a.name else self.exchange_a

            logger.info(f"Closing arb position for {symbol}")

            if self.config.dry_run:
                logger.info("  [DRY RUN] No orders placed")
                self.total_volume_usd += arb.total_notional
                del self.arb_positions[symbol]
                return True, "Dry run - positions closed"

            # Close both positions
            short_result = await short_adapter.close_position(symbol)
            long_result = await long_adapter.close_position(symbol)

            if short_result.success and long_result.success:
                self.total_volume_usd += arb.total_notional
                del self.arb_positions[symbol]
                return True, f"Closed {symbol} arb position"
            else:
                errors = []
                if not short_result.success:
                    errors.append(f"SHORT: {short_result.error}")
                if not long_result.success:
                    errors.append(f"LONG: {long_result.error}")
                return False, "; ".join(errors)

        except Exception as e:
            logger.error(f"Error closing arb position: {e}")
            return False, str(e)

    async def rotate_position(self, symbol: str) -> Tuple[bool, str]:
        """
        Rotate a position - close and reopen to generate volume.

        This is key for volume generation: by closing and reopening,
        we execute 4 trades (2 close + 2 open) which generates volume
        on both exchanges while maintaining the same market exposure.
        """
        try:
            if symbol not in self.arb_positions:
                return False, "No position to rotate"

            arb = self.arb_positions[symbol]
            original_size = arb.short_size_usd  # Use short side as reference

            # Get current spread
            spread = await self.get_funding_spread(symbol)
            if not spread:
                return False, "Could not get funding spread"

            logger.info(f"Rotating {symbol} position for volume generation")
            logger.info(f"  Current size: ${original_size:.2f} per leg")
            logger.info(f"  Current spread: {spread.annualized_spread:.2f}% annualized")

            # Close existing position
            close_success, close_msg = await self.close_arb_position(symbol)
            if not close_success:
                return False, f"Failed to close for rotation: {close_msg}"

            # Reopen with same size (may flip direction if spread changed)
            open_success, open_msg = await self.open_arb_position(
                symbol, spread, original_size
            )

            if open_success:
                if symbol in self.arb_positions:
                    self.arb_positions[symbol].last_rotated = datetime.now(timezone.utc)
                return True, f"Rotated {symbol}: {close_msg} -> {open_msg}"
            else:
                return False, f"Rotation incomplete: {open_msg}"

        except Exception as e:
            logger.error(f"Error rotating position: {e}")
            return False, str(e)

    async def rebalance_if_needed(self, symbol: str) -> Tuple[bool, str]:
        """
        Check and rebalance position if delta is imbalanced.
        """
        if symbol not in self.arb_positions:
            return True, "No position to rebalance"

        arb = self.arb_positions[symbol]
        imbalance = abs(arb.delta_imbalance)

        if imbalance <= self.config.max_delta_imbalance_usd:
            return True, f"Position balanced (imbalance: ${imbalance:.2f})"

        logger.warning(f"{symbol} delta imbalance: ${imbalance:.2f} - rebalancing")

        # Determine which side needs adjustment
        if arb.long_size_usd > arb.short_size_usd:
            # Need to increase SHORT or decrease LONG
            adjust_amount = imbalance / 2  # Split adjustment
            # For simplicity, rotate the position
            return await self.rotate_position(symbol)
        else:
            # Need to increase LONG or decrease SHORT
            return await self.rotate_position(symbol)

    def get_session_stats(self) -> Dict:
        """Get statistics for the current session"""
        elapsed = (datetime.now(timezone.utc) - self.session_start).total_seconds() / 3600
        return {
            "session_duration_hours": elapsed,
            "total_volume_usd": self.total_volume_usd,
            "volume_per_hour": self.total_volume_usd / elapsed if elapsed > 0 else 0,
            "active_positions": len(self.arb_positions),
            "symbols_traded": list(self.arb_positions.keys()),
        }
