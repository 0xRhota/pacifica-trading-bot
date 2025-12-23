"""
Strategy F: Self-Improving LLM Trading

Wraps the core self-improving strategy for Hibachi DEX.

This strategy replaces the hardcoded filters with a learning system that:
1. Tracks every trade outcome (symbol, direction, confidence, result)
2. Analyzes performance across multiple dimensions
3. Automatically generates filters for poor performers
4. Enhances LLM prompts with performance context

Key improvements over hardcoded filters:
- Adapts to changing market conditions
- Learns from its own mistakes
- Provides LLM with its past performance
- Can be reset/adjusted as needed
"""

import logging
from typing import Dict, List, Optional, Tuple

# Import core self-improving strategy
from core.strategies.self_improving_llm import (
    SelfImprovingLLMStrategy,
    StrategyConfig,
    OutcomeTracker,
    PerformanceAnalyzer,
    StrategyAdjuster
)

logger = logging.getLogger(__name__)


class StrategyFSelfImproving:
    """
    Strategy F adapter for Hibachi - Self-Improving LLM Trading.

    This wraps the core self-improving strategy and provides:
    1. Pre-trade filtering (block/reduce poor performers)
    2. Prompt enhancement (add performance context for LLM)
    3. Outcome tracking (record every trade result)
    4. Periodic review (analyze and adjust filters)

    Usage:
        strategy = StrategyFSelfImproving(position_size=10.0)

        # Get enhanced prompt context
        context = strategy.get_prompt_enhancement()
        prompt = base_prompt + context

        # Filter LLM decision before execution
        decision = {"symbol": "SOL/USDT-P", "action": "LONG", "confidence": 0.7}
        modified, rejection = strategy.filter_decision(decision)

        if rejection:
            # Skip this trade
            logger.info(f"Trade rejected: {rejection}")
            continue

        # Execute trade...

        # Record entry after execution
        trade_id = strategy.record_entry(decision, entry_price)

        # Later, record exit
        strategy.record_exit(trade_id, exit_price, pnl_usd)
    """

    STRATEGY_NAME = "STRATEGY_F_SELF_IMPROVING_HIBACHI"

    def __init__(
        self,
        position_size: float = 10.0,
        review_interval: int = 10,
        rolling_window: int = 50,
        auto_apply_filters: bool = True,
        log_dir: str = "logs/strategies"
    ):
        """
        Initialize Strategy F.

        Args:
            position_size: Default position size in USD
            review_interval: Trades between review cycles
            rolling_window: Number of trades to analyze
            auto_apply_filters: Automatically apply analysis findings
            log_dir: Directory for state files
        """
        self.position_size = position_size

        # Configure core strategy
        config = StrategyConfig(
            review_interval=review_interval,
            min_trades_for_analysis=10,
            rolling_window=rolling_window,
            auto_apply_filters=auto_apply_filters,
            log_dir=log_dir
        )

        # Initialize core strategy
        self.strategy = SelfImprovingLLMStrategy(config=config)

        # Track active trade IDs by symbol
        self._active_trades: Dict[str, int] = {}

        self._log_startup()

    def _log_startup(self):
        """Log strategy initialization"""
        logger.info("")
        logger.info("=" * 70)
        logger.info(f"STRATEGY F: {self.STRATEGY_NAME}")
        logger.info("=" * 70)
        logger.info("  MODE: Self-Improving LLM (Dynamic Filters)")
        logger.info(f"  Position Size: ${self.position_size}")
        logger.info("")
        logger.info("  KEY FEATURES:")
        logger.info("    - Tracks outcomes by symbol, direction, confidence")
        logger.info("    - Analyzes performance every 10 trades")
        logger.info("    - Auto-blocks poor performers (<30% win rate)")
        logger.info("    - Auto-reduces position on risky combos (<40% win)")
        logger.info("    - Provides LLM with its past performance")
        logger.info("")

        # Log current state
        stats = self.strategy.get_stats()
        logger.info("  CURRENT STATE:")
        logger.info(f"    Total trades: {stats['total_trades']}")
        logger.info(f"    Win rate: {stats['overall_win_rate']:.1%}")
        logger.info(f"    Total PnL: ${stats['overall_pnl_usd']:+.2f}")
        logger.info(f"    Active filters: {stats['active_filters']}")
        logger.info(f"      - Block filters: {stats['block_filters']}")
        logger.info(f"      - Reduce filters: {stats['reduce_filters']}")
        logger.info("")

        # Log active filters
        filters_summary = self.strategy.get_active_filters_summary()
        logger.info(f"  {filters_summary}")
        logger.info("=" * 70)
        logger.info("")

    def filter_decision(
        self,
        decision: Dict
    ) -> Tuple[Dict, Optional[str]]:
        """
        Filter an LLM decision through active filters.

        Args:
            decision: Dict with:
                - symbol: Trading symbol (e.g., "SOL/USDT-P")
                - action: "LONG" or "SHORT"
                - confidence: 0.0-1.0
                - position_size_usd: (optional) size in USD

        Returns:
            (modified_decision, rejection_reason)
            rejection_reason is not None if trade should be skipped
        """
        # Ensure position size is set
        if "position_size_usd" not in decision:
            decision["position_size_usd"] = self.position_size

        return self.strategy.filter_decision(decision)

    def get_prompt_enhancement(self) -> str:
        """
        Get performance context to add to LLM prompt.

        This includes:
        - Blocked combos (e.g., "SOL_SHORT: 25% win rate - DO NOT TRADE")
        - High-risk combos (e.g., "ETH_SHORT: 38% win rate - use caution")
        - Confidence requirements

        Returns:
            String to append to LLM prompt
        """
        return self.strategy.get_prompt_enhancement()

    def record_entry(
        self,
        decision: Dict,
        entry_price: float,
        llm_reasoning: str = ""
    ) -> int:
        """
        Record a trade entry.

        Args:
            decision: The (possibly modified) decision dict
            entry_price: Actual entry price
            llm_reasoning: LLM's reasoning for this trade

        Returns:
            trade_id: Use this to record exit later
        """
        symbol = decision.get("symbol", "UNKNOWN")
        action = decision.get("action", "UNKNOWN")
        confidence = decision.get("confidence", 0.5)

        trade_id = self.strategy.record_trade_entry(
            symbol=symbol,
            direction=action,
            confidence=confidence,
            entry_price=entry_price,
            llm_reasoning=llm_reasoning
        )

        # Track active trade by symbol
        self._active_trades[symbol] = trade_id

        return trade_id

    def record_exit(
        self,
        symbol: str = None,
        trade_id: int = None,
        exit_price: float = 0,
        pnl_usd: float = None
    ) -> Optional[Dict]:
        """
        Record a trade exit.

        Args:
            symbol: Symbol (used to look up trade_id if not provided)
            trade_id: ID from record_entry (optional if symbol provided)
            exit_price: Actual exit price
            pnl_usd: Actual PnL in USD

        Returns:
            Outcome dict or None
        """
        # Look up trade_id from symbol if not provided
        if trade_id is None and symbol:
            trade_id = self._active_trades.get(symbol)

        if trade_id is None:
            logger.warning(f"[STRATEGY F] No active trade found for {symbol}")
            return None

        outcome = self.strategy.record_trade_exit(
            trade_id=trade_id,
            exit_price=exit_price,
            pnl_usd=pnl_usd
        )

        # Remove from active trades
        if symbol and symbol in self._active_trades:
            del self._active_trades[symbol]

        return outcome

    def get_active_trade_id(self, symbol: str) -> Optional[int]:
        """Get the active trade ID for a symbol"""
        return self._active_trades.get(symbol)

    def force_review(self):
        """Force an immediate review cycle"""
        logger.info("[STRATEGY F] Forcing review cycle...")
        return self.strategy.force_review()

    def get_stats(self) -> Dict:
        """Get combined statistics"""
        return self.strategy.get_stats()

    def get_dimension_breakdown(self) -> Dict:
        """Get performance breakdown by all dimensions"""
        return self.strategy.get_dimension_breakdown()

    def clear_filters(self):
        """Clear all active filters (use with caution)"""
        logger.warning("[STRATEGY F] Clearing all filters - starting fresh")
        self.strategy.clear_filters()

    def log_status(self):
        """Log current strategy status"""
        stats = self.get_stats()
        logger.info("")
        logger.info("=" * 60)
        logger.info("STRATEGY F STATUS")
        logger.info("=" * 60)
        logger.info(f"  Total trades: {stats['total_trades']}")
        logger.info(f"  Win rate: {stats['overall_win_rate']:.1%}")
        logger.info(f"  Total PnL: ${stats['overall_pnl_usd']:+.2f}")
        logger.info(f"  Trades since review: {stats['trades_since_review']}")
        logger.info(f"  Active filters: {stats['active_filters']}")
        logger.info("=" * 60)
