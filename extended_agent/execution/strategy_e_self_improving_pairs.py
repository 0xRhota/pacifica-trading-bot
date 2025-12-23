"""
Strategy E - Self-Improving Pairs Trade (for Extended)

PHILOSOPHY:
This is the evolution of Strategy D. Same core concept (pairs trade for volume
generation while staying flat), but with SELF-IMPROVING capabilities.

The strategy:
1. Tracks actual outcomes (not just $0.00 PnL)
2. Analyzes direction accuracy over time
3. Gradually adjusts bias toward the better-performing direction
4. Includes past performance context in LLM prompts

CRITICAL IMPROVEMENT over Strategy D:
- Strategy D always picked ETH to long with weak reasoning
- Strategy E tracks if that was RIGHT or WRONG
- After 5 trades, it reviews: "Am I picking the right asset to long?"
- If accuracy < 45%, it adjusts bias toward the other direction

Uses the exchange-agnostic core strategy from core/strategies/self_improving_pairs/
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

# Import the core strategy
from core.strategies.self_improving_pairs import SelfImprovingPairsStrategy

logger = logging.getLogger(__name__)


class StrategyESelfImprovingPairs:
    """
    Wrapper for the self-improving pairs strategy.

    This provides the same interface as StrategyDPairsTrade but uses the
    new self-improving core strategy that learns from its mistakes.
    """

    STRATEGY_NAME = "STRATEGY_E_SELF_IMPROVING_PAIRS"

    # Default pair
    LONG_ASSET = "ETH-USD"
    SHORT_ASSET = "BTC-USD"

    def __init__(
        self,
        position_size_usd: float = 100.0,
        hold_time_seconds: int = 3600,
        long_asset: str = "ETH-USD",
        short_asset: str = "BTC-USD",
        llm_agent=None
    ):
        """
        Initialize Self-Improving Pairs Trade Strategy.

        Args:
            position_size_usd: Dollar amount per leg
            hold_time_seconds: How long to hold before closing
            long_asset: First asset (default long candidate)
            short_asset: Second asset (default short candidate)
            llm_agent: LLM agent for direction selection
        """
        self.position_size_usd = position_size_usd
        self.hold_time_seconds = hold_time_seconds
        self.LONG_ASSET = long_asset
        self.SHORT_ASSET = short_asset
        self.ASSET_A = long_asset
        self.ASSET_B = short_asset

        # Extract LLM client from agent
        llm_client = None
        if llm_agent and hasattr(llm_agent, 'model_client'):
            llm_client = llm_agent.model_client

        # Initialize the core strategy
        self.core_strategy = SelfImprovingPairsStrategy(
            asset_a=long_asset,
            asset_b=short_asset,
            llm_client=llm_client,
            hold_time_seconds=hold_time_seconds,
            review_interval=5  # Review every 5 trades
        )

        # For compatibility with bot_extended.py (legacy interface)
        self.active_trade = None

        logger.info("")
        logger.info("=" * 70)
        logger.info("STRATEGY E: SELF-IMPROVING PAIRS TRADE")
        logger.info("=" * 70)
        logger.info(f"  Assets: {long_asset} vs {short_asset}")
        logger.info(f"  Size: ${position_size_usd} per leg")
        logger.info(f"  Hold: {hold_time_seconds}s ({hold_time_seconds/60:.0f} min)")
        logger.info(f"  Review: Every 5 trades")
        logger.info("")
        logger.info("  KEY IMPROVEMENTS OVER STRATEGY D:")
        logger.info("    - Tracks actual outcomes (correct/wrong direction)")
        logger.info("    - Analyzes accuracy over rolling 10 trades")
        logger.info("    - GRADUALLY adjusts bias (max 15% per review)")
        logger.info("    - Includes past performance in LLM prompts")
        logger.info("")
        logger.info("  SELF-IMPROVEMENT CYCLE:")
        logger.info("    1. Track: Did long asset outperform short?")
        logger.info("    2. Analyze: What's our accuracy? Which direction works?")
        logger.info("    3. Adjust: Shift bias toward better direction")
        logger.info("    4. Apply: Include bias hint in next LLM prompt")
        logger.info("=" * 70)
        logger.info("")

    def sync_with_positions(self, our_positions: List[Dict]) -> Optional[str]:
        """
        Sync strategy state with actual positions.

        Args:
            our_positions: Current open positions

        Returns:
            Symbol of orphaned position if found, None otherwise
        """
        orphan = self.core_strategy.sync_with_positions(our_positions)

        # Sync active_trade for compatibility
        if self.core_strategy.has_active_trade():
            if self.active_trade is None:
                # Get open trade data from outcome tracker to populate asset info
                open_trade = self.core_strategy.outcome_tracker.get_open_trade()
                if open_trade:
                    self.active_trade = {
                        "open_time": self.core_strategy._active_trade_open_time,
                        "status": "active",
                        "long_asset": open_trade.get("long_symbol", self.ASSET_A),
                        "short_asset": open_trade.get("short_symbol", self.ASSET_B),
                        "trade_id": open_trade.get("id")
                    }
                    logger.info(f"[PAIRS-E] Synced active_trade from outcome tracker: long={self.active_trade['long_asset']}, short={self.active_trade['short_asset']}, id={self.active_trade['trade_id']}")
                else:
                    self.active_trade = {
                        "open_time": self.core_strategy._active_trade_open_time,
                        "status": "active",
                        "long_asset": self.ASSET_A,
                        "short_asset": self.ASSET_B
                    }
                    logger.warning(f"[PAIRS-E] No open trade in tracker - using defaults")
        else:
            self.active_trade = None

        return orphan

    async def should_open_pair(self, our_positions: List[Dict]) -> bool:
        """Check if we should open a new pairs trade."""
        # Sync first
        orphan = self.sync_with_positions(our_positions)
        if orphan:
            logger.info(f"[PAIRS-E] Cannot open - orphaned {orphan} needs cleanup")
            return False

        # Don't open if already have active trade
        if self.core_strategy.has_active_trade():
            return False

        # Don't open if we have positions in our target assets
        for pos in our_positions:
            symbol = pos.get('symbol', '')
            if symbol in [self.ASSET_A, self.ASSET_B]:
                logger.info(f"[PAIRS-E] Already have position in {symbol}")
                return False

        return True

    async def should_close_pair(self) -> bool:
        """Check if we should close the current pairs trade."""
        return self.core_strategy.should_close_pair()

    def get_time_remaining(self) -> Optional[int]:
        """Get seconds remaining until close."""
        return self.core_strategy.get_time_remaining()

    async def get_open_decisions(
        self,
        account_balance: float,
        market_data_dict: Dict = None
    ) -> List[Dict]:
        """
        Get decisions to open a new pairs trade.

        Args:
            account_balance: Current account balance
            market_data_dict: Market data for both assets

        Returns:
            List of LONG and SHORT decisions
        """
        # Calculate position size
        size_per_leg = min(self.position_size_usd, account_balance * 0.4)

        # Get decisions from core strategy (with self-improvement context)
        decisions = await self.core_strategy.get_decisions(
            market_data=market_data_dict or {},
            position_size_usd=size_per_leg
        )

        # Update active_trade for compatibility
        if decisions:
            long_decision = next((d for d in decisions if d['action'] == 'LONG'), None)
            short_decision = next((d for d in decisions if d['action'] == 'SHORT'), None)

            self.active_trade = {
                "open_time": datetime.now(),
                "long_asset": long_decision['symbol'] if long_decision else self.ASSET_A,
                "short_asset": short_decision['symbol'] if short_decision else self.ASSET_B,
                "size_per_leg": size_per_leg,
                "status": "opening"
            }

        return decisions

    async def get_close_decisions(self) -> List[Dict]:
        """Get decisions to close the current pairs trade."""
        return self.core_strategy.get_close_decisions()

    def record_entry(self, symbol: str, price: float, size: float):
        """Record entry price after execution."""
        if self.active_trade is None:
            return

        # Update active_trade for compatibility
        if symbol == self.active_trade.get("long_asset"):
            self.active_trade["long_entry_price"] = price
            self.active_trade["long_size"] = size
        elif symbol == self.active_trade.get("short_asset"):
            self.active_trade["short_entry_price"] = price
            self.active_trade["short_size"] = size

        # Check if both legs filled
        if (self.active_trade.get("long_entry_price") and
            self.active_trade.get("short_entry_price")):

            self.active_trade["status"] = "open"

            # Record in core strategy
            entry_prices = {
                self.active_trade["long_asset"]: self.active_trade["long_entry_price"],
                self.active_trade["short_asset"]: self.active_trade["short_entry_price"]
            }

            trade_id = self.core_strategy.record_entry(
                entry_prices=entry_prices,
                llm_reasoning=self.active_trade.get("llm_reasoning", ""),
                long_symbol=self.active_trade["long_asset"],
                short_symbol=self.active_trade["short_asset"]
            )

            self.active_trade["trade_id"] = trade_id
            logger.info(f"[PAIRS-E] Both legs filled - trade {trade_id} is OPEN")

    def record_exit(self, symbol: str, price: float, pnl: float):
        """Record exit price after closing."""
        logger.info(f"[PAIRS-E] record_exit called: symbol={symbol}, price={price}, pnl={pnl}")

        if self.active_trade is None:
            logger.warning(f"[PAIRS-E] record_exit: active_trade is None! Cannot record.")
            return

        logger.info(f"[PAIRS-E] active_trade: long_asset={self.active_trade.get('long_asset')}, short_asset={self.active_trade.get('short_asset')}")

        # Update active_trade for compatibility
        if symbol == self.active_trade.get("long_asset"):
            self.active_trade["long_exit_price"] = price
            self.active_trade["long_pnl"] = pnl
        elif symbol == self.active_trade.get("short_asset"):
            self.active_trade["short_exit_price"] = price
            self.active_trade["short_pnl"] = pnl

        # Check if both legs closed
        if (self.active_trade.get("long_exit_price") and
            self.active_trade.get("short_exit_price")):

            # Record in core strategy (triggers learning)
            trade_id = self.active_trade.get("trade_id")
            if trade_id:
                exit_prices = {
                    self.active_trade["long_asset"]: self.active_trade["long_exit_price"],
                    self.active_trade["short_asset"]: self.active_trade["short_exit_price"]
                }

                outcome = self.core_strategy.record_exit(trade_id, exit_prices)

                if outcome:
                    direction_emoji = "" if outcome['correct_direction'] else ""
                    logger.info("")
                    logger.info("=" * 60)
                    logger.info("PAIRS TRADE CLOSED - OUTCOME")
                    logger.info("=" * 60)
                    logger.info(f"  Direction: {direction_emoji} {'CORRECT' if outcome['correct_direction'] else 'WRONG'}")
                    logger.info(f"  Long return: {outcome['long_return']:+.2f}%")
                    logger.info(f"  Short return: {outcome['short_return']:+.2f}%")
                    logger.info(f"  Spread return: {outcome['spread_return']:+.2f}%")
                    logger.info("=" * 60)
                    logger.info("")

            # Clear active trade
            self.active_trade = None

    def get_status(self) -> Dict:
        """Get comprehensive strategy status."""
        core_status = self.core_strategy.get_status()

        return {
            "strategy": self.STRATEGY_NAME,
            "long_asset": self.LONG_ASSET,
            "short_asset": self.SHORT_ASSET,
            "position_size": self.position_size_usd,
            "hold_time": self.hold_time_seconds,
            "stats": {
                "total_trades": core_status["performance"]["total_trades"],
                "accuracy": core_status["performance"]["accuracy"],
                "avg_spread_return": core_status["performance"]["avg_spread_return"],
                "total_pnl": 0,  # Calculated from outcomes
                "total_volume": 0
            },
            "bias": core_status["bias"],
            "active_trade": {
                "status": "active" if self.active_trade else None,
                "time_remaining_seconds": self.get_time_remaining(),
                "time_remaining_min": (self.get_time_remaining() or 0) / 60
            } if self.active_trade else None
        }
