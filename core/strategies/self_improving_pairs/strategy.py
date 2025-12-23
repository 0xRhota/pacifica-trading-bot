"""
Self-Improving Pairs Trade Strategy

This is the main strategy class that orchestrates pairs trading with
self-improvement capabilities. It combines:
1. OutcomeTracker - Records trade results
2. PerformanceAnalyzer - Analyzes accuracy
3. StrategyAdjuster - Adjusts bias based on performance

The strategy is EXCHANGE-AGNOSTIC. It works with any exchange by:
- Taking standardized market data as input
- Returning standardized decisions as output
- Letting the exchange adapter handle execution

Key features:
- LLM-based direction selection (which asset to long/short)
- Past performance context in prompts
- Gradual bias adjustment based on results
- Automatic review cycles

Usage:
    from core.strategies import SelfImprovingPairsStrategy

    strategy = SelfImprovingPairsStrategy(
        asset_a="ETH-USD",
        asset_b="BTC-USD",
        llm_client=model_client,
        hold_time_seconds=3600
    )

    # Get decisions (returns list of LONG/SHORT decisions)
    decisions = await strategy.get_decisions(market_data)

    # After execution, record the entry
    trade_id = strategy.record_entry(entry_prices, llm_reasoning)

    # When closing, record the exit (triggers learning)
    strategy.record_exit(trade_id, exit_prices)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .outcome_tracker import OutcomeTracker
from .performance_analyzer import PerformanceAnalyzer, Recommendation
from .strategy_adjuster import StrategyAdjuster

logger = logging.getLogger(__name__)


class SelfImprovingPairsStrategy:
    """
    Self-improving pairs trade strategy with LLM direction selection.

    This strategy opens opposing positions on two correlated assets
    (e.g., Long ETH, Short BTC) and closes them after a hold period.
    It learns from past trades and adjusts its direction bias over time.

    Attributes:
        asset_a: First asset (default long candidate), e.g., "ETH-USD"
        asset_b: Second asset (default short candidate), e.g., "BTC-USD"
        hold_time_seconds: How long to hold positions before closing
        review_interval_trades: Run performance review every N trades
    """

    STRATEGY_NAME = "SELF_IMPROVING_PAIRS_V1"
    DEFAULT_HOLD_TIME = 3600  # 1 hour
    REVIEW_INTERVAL_TRADES = 5  # Review every 5 trades

    def __init__(
        self,
        asset_a: str = "ETH-USD",
        asset_b: str = "BTC-USD",
        llm_client=None,
        hold_time_seconds: int = None,
        review_interval: int = None
    ):
        """
        Initialize the self-improving pairs strategy.

        Args:
            asset_a: First asset symbol (will be longed if bias <= 0.5)
            asset_b: Second asset symbol (will be shorted if bias <= 0.5)
            llm_client: LLM model client for direction decisions
            hold_time_seconds: How long to hold before closing (default: 1 hour)
            review_interval: Trades between performance reviews (default: 5)
        """
        self.asset_a = asset_a
        self.asset_b = asset_b
        self.llm_client = llm_client
        self.hold_time_seconds = hold_time_seconds or self.DEFAULT_HOLD_TIME
        self.review_interval = review_interval or self.REVIEW_INTERVAL_TRADES

        # Initialize components
        self.outcome_tracker = OutcomeTracker()
        self.analyzer = PerformanceAnalyzer()
        self.adjuster = StrategyAdjuster()

        # Track active trade
        self._active_trade_id: Optional[int] = None
        self._active_trade_open_time: Optional[datetime] = None

        # Log initialization
        logger.info("=" * 60)
        logger.info(f"STRATEGY: {self.STRATEGY_NAME}")
        logger.info("=" * 60)
        logger.info(f"  Assets: {self.asset_a} vs {self.asset_b}")
        logger.info(f"  Hold time: {self.hold_time_seconds}s ({self.hold_time_seconds/60:.0f} min)")
        logger.info(f"  Review interval: Every {self.review_interval} trades")
        logger.info(f"  Current bias: {self.adjuster.get_current_bias():.2f}")
        logger.info(f"  LLM: {'Configured' if llm_client else 'NOT CONFIGURED'}")
        logger.info("=" * 60)

    async def get_decisions(
        self,
        market_data: Dict[str, Dict],
        position_size_usd: float = 10.0
    ) -> List[Dict]:
        """
        Get trading decisions for opening a new pairs trade.

        This method:
        1. Gets past performance stats
        2. Constructs an enhanced prompt with performance context
        3. Asks the LLM which asset to long
        4. Returns standardized decisions

        Args:
            market_data: Dict of {symbol: {price, rsi, macd, ...}}
            position_size_usd: Dollar amount per leg

        Returns:
            List of decisions:
            [
                {"action": "LONG", "symbol": "ETH-USD", "reasoning": "...", ...},
                {"action": "SHORT", "symbol": "BTC-USD", "reasoning": "...", ...}
            ]
        """
        # Get current stats and bias
        stats = self.outcome_tracker.get_rolling_stats(n=10)
        bias = self.adjuster.get_current_bias()
        bias_instruction = self.adjuster.get_bias_instruction()

        # Ask LLM for direction
        long_symbol, short_symbol, reasoning = await self._ask_llm_direction(
            market_data, stats, bias_instruction
        )

        logger.info("")
        logger.info("=" * 60)
        logger.info("PAIRS TRADE: OPENING DECISION")
        logger.info("=" * 60)
        logger.info(f"  Long: {long_symbol}")
        logger.info(f"  Short: {short_symbol}")
        logger.info(f"  Size: ${position_size_usd:.2f} per leg")
        logger.info(f"  Bias: {bias:.2f} ({self.adjuster._get_bias_category()})")
        logger.info(f"  Reasoning: {reasoning[:100]}...")
        logger.info("=" * 60)

        return [
            {
                "action": "LONG",
                "symbol": long_symbol,
                "reasoning": f"PAIRS TRADE: {reasoning}",
                "confidence": 0.6,
                "position_size_usd": position_size_usd,
                "strategy": self.STRATEGY_NAME
            },
            {
                "action": "SHORT",
                "symbol": short_symbol,
                "reasoning": f"PAIRS TRADE: Opposite leg to {long_symbol}",
                "confidence": 0.6,
                "position_size_usd": position_size_usd,
                "strategy": self.STRATEGY_NAME
            }
        ]

    async def _ask_llm_direction(
        self,
        market_data: Dict[str, Dict],
        stats: Dict,
        bias_instruction: str
    ) -> Tuple[str, str, str]:
        """
        Ask the LLM which asset to long/short.

        Args:
            market_data: Market data for both assets
            stats: Rolling performance statistics
            bias_instruction: Current bias instruction for prompt

        Returns:
            (long_symbol, short_symbol, reasoning)
        """
        if not self.llm_client:
            # No LLM - use bias to determine direction
            suggested = self.adjuster.get_suggested_direction()
            if suggested == "BTC":
                return (self.asset_b, self.asset_a, "No LLM - using BTC bias")
            else:
                return (self.asset_a, self.asset_b, "No LLM - using ETH bias (default)")

        # Build the prompt with past performance context
        prompt = self._build_direction_prompt(market_data, stats, bias_instruction)

        try:
            # Call LLM
            result = self.llm_client.query(prompt)
            if not result or not result.get('content'):
                logger.warning("[STRATEGY] Empty LLM response, using default direction")
                return self._get_default_direction()

            text = result['content'].strip()
            return self._parse_llm_response(text)

        except Exception as e:
            logger.error(f"[STRATEGY] LLM error: {e}")
            return self._get_default_direction()

    def _build_direction_prompt(
        self,
        market_data: Dict[str, Dict],
        stats: Dict,
        bias_instruction: str
    ) -> str:
        """Build the enhanced direction prompt with past performance context"""

        # Extract market data
        data_a = market_data.get(self.asset_a, {})
        data_b = market_data.get(self.asset_b, {})

        # Format past performance section
        if stats.get("sufficient_data", False):
            performance_section = f"""
=== YOUR PAST PERFORMANCE (READ THIS CAREFULLY) ===
Last {stats['total']} trades: {stats['correct']} correct, {stats['total'] - stats['correct']} wrong ({stats['accuracy']:.0%} accuracy)

Direction breakdown:
- Long {self.asset_a.split('-')[0]} calls: {stats['eth_bias']['count']} trades, {stats['eth_bias']['correct']} correct ({stats['eth_bias']['accuracy']:.0%})
- Long {self.asset_b.split('-')[0]} calls: {stats['btc_bias']['count']} trades, {stats['btc_bias']['correct']} correct ({stats['btc_bias']['accuracy']:.0%})

Average spread return: {stats['avg_spread_return']:+.2f}%
"""
        else:
            performance_section = """
=== PAST PERFORMANCE ===
Insufficient data (fewer than 5 trades). Make your best judgment based on current data.
"""

        prompt = f"""=== PAIRS TRADE DIRECTION ANALYSIS ===

MARKET DATA:
{self.asset_a}:
  Price: ${data_a.get('price', 0):.2f}
  RSI(14): {data_a.get('rsi', 50):.1f}
  MACD: {data_a.get('macd', 0):.4f}
  24h Change: {data_a.get('price_change_24h', 0):.2f}%

{self.asset_b}:
  Price: ${data_b.get('price', 0):.2f}
  RSI(14): {data_b.get('rsi', 50):.1f}
  MACD: {data_b.get('macd', 0):.4f}
  24h Change: {data_b.get('price_change_24h', 0):.2f}%

{performance_section}

=== STRATEGY GUIDANCE ===
{bias_instruction}

=== YOUR TASK ===
You are executing a PAIRS TRADE: long one asset, short the other.
Based on the data above, which asset is MORE LIKELY to outperform in the next 1 hour?

Consider:
1. Your past accuracy with each direction
2. Current technical indicators
3. The system's bias instruction above

RESPOND ONLY WITH:
LONG: {self.asset_a} or {self.asset_b}
SHORT: {self.asset_a} or {self.asset_b}
CONFIDENCE: 0.0-1.0
REASON: <one sentence explaining your choice, acknowledging past performance if relevant>
"""
        return prompt

    def _parse_llm_response(self, text: str) -> Tuple[str, str, str]:
        """Parse the LLM's direction response"""
        long_symbol = None
        short_symbol = None
        reason = "LLM analysis"

        for line in text.split('\n'):
            line = line.strip()
            if line.upper().startswith('LONG:'):
                long_symbol = line.split(':', 1)[1].strip()
            elif line.upper().startswith('SHORT:'):
                short_symbol = line.split(':', 1)[1].strip()
            elif line.upper().startswith('REASON:'):
                reason = line.split(':', 1)[1].strip()

        # Validate response
        valid_symbols = [self.asset_a, self.asset_b]
        if long_symbol in valid_symbols and short_symbol in valid_symbols:
            if long_symbol != short_symbol:
                logger.info(f"[STRATEGY-LLM] {long_symbol} > {short_symbol}: {reason}")
                return (long_symbol, short_symbol, reason)

        # Invalid response - use default
        logger.warning(f"[STRATEGY-LLM] Invalid response, using default direction")
        return self._get_default_direction()

    def _get_default_direction(self) -> Tuple[str, str, str]:
        """Get default direction based on current bias"""
        suggested = self.adjuster.get_suggested_direction()
        if suggested == "BTC":
            return (self.asset_b, self.asset_a, "Default: BTC bias active")
        else:
            return (self.asset_a, self.asset_b, "Default: ETH bias or neutral")

    def record_entry(
        self,
        entry_prices: Dict[str, float],
        llm_reasoning: str,
        long_symbol: str,
        short_symbol: str
    ) -> int:
        """
        Record a trade entry.

        Args:
            entry_prices: Dict of {symbol: price} for both assets
            llm_reasoning: The reasoning from get_decisions
            long_symbol: Which symbol was longed
            short_symbol: Which symbol was shorted

        Returns:
            trade_id: Use this to record the exit
        """
        trade_id = self.outcome_tracker.record_entry(
            long_symbol=long_symbol,
            short_symbol=short_symbol,
            entry_prices=entry_prices,
            llm_reasoning=llm_reasoning
        )

        self._active_trade_id = trade_id
        self._active_trade_open_time = datetime.now()

        return trade_id

    def record_exit(self, trade_id: int, exit_prices: Dict[str, float]) -> Optional[Dict]:
        """
        Record a trade exit and trigger learning if needed.

        Args:
            trade_id: ID from record_entry
            exit_prices: Dict of {symbol: price} for both assets

        Returns:
            Outcome dict with returns and correctness
        """
        outcome = self.outcome_tracker.record_exit(trade_id, exit_prices)

        self._active_trade_id = None
        self._active_trade_open_time = None

        # Check if we should run a review
        trades_since_review = self.outcome_tracker.get_trades_since_last_review()
        if trades_since_review >= self.review_interval:
            self._run_review_cycle()

        return outcome

    def _run_review_cycle(self):
        """Run a performance review and potentially adjust strategy"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("RUNNING PERFORMANCE REVIEW")
        logger.info("=" * 60)

        # Get stats
        stats = self.outcome_tracker.get_rolling_stats(n=10)

        if not stats.get("sufficient_data", False):
            logger.info("Insufficient data for review")
            return

        # Analyze
        analysis = self.analyzer.analyze(stats)

        # Determine if adjustment needed
        if self.analyzer.should_trigger_adjustment(analysis):
            trade_count = self.outcome_tracker.get_trade_count()
            self.adjuster.adjust(analysis, trade_count)

        # Mark review complete
        self.outcome_tracker.mark_review_complete()

    def should_close_pair(self) -> bool:
        """Check if the current pair should be closed (hold time elapsed)"""
        if not self._active_trade_open_time:
            return False

        elapsed = (datetime.now() - self._active_trade_open_time).total_seconds()
        return elapsed >= self.hold_time_seconds

    def get_time_remaining(self) -> Optional[int]:
        """Get seconds remaining until close, or None if no active trade"""
        if not self._active_trade_open_time:
            return None

        elapsed = (datetime.now() - self._active_trade_open_time).total_seconds()
        remaining = self.hold_time_seconds - elapsed
        return max(0, int(remaining))

    def has_active_trade(self) -> bool:
        """Check if there's an active (open) trade"""
        return self._active_trade_id is not None

    def get_active_trade_id(self) -> Optional[int]:
        """Get the current active trade ID"""
        return self._active_trade_id

    def sync_with_positions(self, open_positions: List[Dict]) -> Optional[str]:
        """
        Sync strategy state with actual exchange positions.
        Detects orphaned positions (one leg missing).

        Args:
            open_positions: List of current open positions from exchange

        Returns:
            Symbol of orphaned position if found, None otherwise
        """
        has_a = any(p.get('symbol') == self.asset_a for p in open_positions)
        has_b = any(p.get('symbol') == self.asset_b for p in open_positions)

        # Both legs present
        if has_a and has_b:
            if not self._active_trade_id:
                # We have positions but no tracking - sync
                logger.warning(f"[STRATEGY] Found both legs but no active trade - syncing")
                self._active_trade_id = -1  # Placeholder
                self._active_trade_open_time = datetime.now()
            return None

        # Neither leg present
        if not has_a and not has_b:
            if self._active_trade_id:
                logger.warning(f"[STRATEGY] No positions but have active trade - clearing")
                self._active_trade_id = None
                self._active_trade_open_time = None
            return None

        # One leg orphaned
        if has_a:
            logger.warning(f"[STRATEGY] ORPHANED: {self.asset_a} (other leg missing)")
            self._active_trade_id = None
            self._active_trade_open_time = None
            return self.asset_a

        if has_b:
            logger.warning(f"[STRATEGY] ORPHANED: {self.asset_b} (other leg missing)")
            self._active_trade_id = None
            self._active_trade_open_time = None
            return self.asset_b

        return None

    def get_status(self) -> Dict:
        """Get comprehensive status of the strategy"""
        stats = self.outcome_tracker.get_rolling_stats(n=10)
        adjuster_state = self.adjuster.get_state_summary()

        return {
            "strategy": self.STRATEGY_NAME,
            "assets": [self.asset_a, self.asset_b],
            "hold_time_seconds": self.hold_time_seconds,
            "has_active_trade": self.has_active_trade(),
            "time_remaining": self.get_time_remaining(),
            "performance": {
                "total_trades": stats["total"],
                "accuracy": stats["accuracy"],
                "avg_spread_return": stats["avg_spread_return"]
            },
            "bias": {
                "current": adjuster_state["current_bias"],
                "category": adjuster_state["bias_category"],
                "suggested_direction": adjuster_state["suggested_direction"]
            },
            "review": {
                "interval": self.review_interval,
                "trades_since_last": self.outcome_tracker.get_trades_since_last_review()
            }
        }

    def get_close_decisions(self) -> List[Dict]:
        """
        Get decisions to close the current pairs trade.

        Returns:
            List of CLOSE decisions for both legs
        """
        open_trade = self.outcome_tracker.get_open_trade()

        if not open_trade:
            return []

        elapsed_min = 0
        if self._active_trade_open_time:
            elapsed_min = (datetime.now() - self._active_trade_open_time).total_seconds() / 60

        long_symbol = open_trade.get("long_symbol", self.asset_a)
        short_symbol = open_trade.get("short_symbol", self.asset_b)

        logger.info("")
        logger.info("=" * 60)
        logger.info("PAIRS TRADE: CLOSING")
        logger.info("=" * 60)
        logger.info(f"  Held for: {elapsed_min:.1f} minutes")
        logger.info(f"  Closing: {long_symbol} (long)")
        logger.info(f"  Closing: {short_symbol} (short)")
        logger.info("=" * 60)

        return [
            {
                "action": "CLOSE",
                "symbol": long_symbol,
                "reasoning": f"PAIRS TRADE: Closing long leg after {elapsed_min:.0f}min hold",
                "strategy": self.STRATEGY_NAME
            },
            {
                "action": "CLOSE",
                "symbol": short_symbol,
                "reasoning": f"PAIRS TRADE: Closing short leg after {elapsed_min:.0f}min hold",
                "strategy": self.STRATEGY_NAME
            }
        ]
