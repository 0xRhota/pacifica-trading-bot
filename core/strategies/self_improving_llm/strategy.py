"""
Self-Improving LLM Strategy - Main orchestrator

Coordinates all components to create a self-learning trading system:
1. Tracks every trade outcome
2. Periodically analyzes performance
3. Generates and applies dynamic filters
4. Enhances LLM prompts with performance context

Exchange-agnostic: Can be adapted to any LLM-based trading system.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .outcome_tracker import OutcomeTracker
from .performance_analyzer import PerformanceAnalyzer, AnalysisReport
from .strategy_adjuster import StrategyAdjuster

logger = logging.getLogger(__name__)


@dataclass
class StrategyConfig:
    """Configuration for the self-improving strategy"""
    review_interval: int = 10           # Trades between reviews
    min_trades_for_analysis: int = 10   # Minimum trades before analysis
    rolling_window: int = 50            # Number of trades to analyze
    auto_apply_filters: bool = True     # Automatically apply analysis findings
    log_dir: str = "logs/strategies"    # Directory for state files


class SelfImprovingLLMStrategy:
    """
    Self-improving wrapper for LLM-based trading.

    This strategy learns from its mistakes by:
    1. Recording every trade outcome (symbol, direction, confidence, result)
    2. Analyzing performance across multiple dimensions
    3. Automatically blocking or reducing size on poor performers
    4. Adding performance context to LLM prompts

    The system does NOT replace the LLM decision-making. Instead, it:
    - Filters out historically bad decisions BEFORE execution
    - Provides the LLM with its past performance data
    - Gradually adjusts as more data accumulates

    Usage:
        strategy = SelfImprovingLLMStrategy()

        # Before getting LLM decision, get enhanced prompt
        context = strategy.get_prompt_enhancement()
        llm_prompt = base_prompt + context

        # After LLM decides, filter the decision
        decision = {"symbol": "SOL/USDT-P", "action": "LONG", "confidence": 0.7}
        modified, rejection = strategy.filter_decision(decision)

        if rejection:
            # Skip this trade
            continue

        # Execute trade with modified decision
        execute_trade(modified)

        # Record the entry
        trade_id = strategy.record_trade_entry(
            symbol="SOL/USDT-P",
            direction="LONG",
            confidence=0.7,
            entry_price=150.0,
            llm_reasoning="Strong momentum..."
        )

        # Later, record the exit
        strategy.record_trade_exit(
            trade_id=trade_id,
            exit_price=152.0,
            pnl_usd=1.50
        )

        # System will auto-review and adjust filters
    """

    STRATEGY_NAME = "SELF_IMPROVING_LLM_V1"

    def __init__(
        self,
        config: StrategyConfig = None,
        outcome_tracker: OutcomeTracker = None,
        performance_analyzer: PerformanceAnalyzer = None,
        strategy_adjuster: StrategyAdjuster = None
    ):
        """
        Initialize the self-improving strategy.

        Args:
            config: Strategy configuration
            outcome_tracker: Optional pre-configured tracker
            performance_analyzer: Optional pre-configured analyzer
            strategy_adjuster: Optional pre-configured adjuster
        """
        self.config = config or StrategyConfig()

        # Initialize components
        self.tracker = outcome_tracker or OutcomeTracker(
            log_file=f"{self.config.log_dir}/self_improving_llm_outcomes.json"
        )
        self.analyzer = performance_analyzer or PerformanceAnalyzer()
        self.adjuster = strategy_adjuster or StrategyAdjuster(
            state_file=f"{self.config.log_dir}/self_improving_llm_state.json"
        )

        # Track state
        self._last_review_count = self.tracker.get_trade_count()
        self._pending_review = False

        logger.info("=" * 60)
        logger.info(f"STRATEGY: {self.STRATEGY_NAME}")
        logger.info("=" * 60)
        logger.info(f"  Review interval: Every {self.config.review_interval} trades")
        logger.info(f"  Rolling window: {self.config.rolling_window} trades")
        logger.info(f"  Auto-apply filters: {self.config.auto_apply_filters}")

        # Log current state
        stats = self.get_stats()
        logger.info(f"  Total trades: {stats['total_trades']}")
        logger.info(f"  Active filters: {stats['active_filters']}")
        logger.info("=" * 60)

    def record_trade_entry(
        self,
        symbol: str,
        direction: str,
        confidence: float,
        entry_price: float,
        llm_reasoning: str = "",
        tags: Dict = None
    ) -> int:
        """
        Record a new trade entry.

        Args:
            symbol: Trading symbol (e.g., "SOL/USDT-P")
            direction: "LONG" or "SHORT"
            confidence: LLM confidence 0.0-1.0
            entry_price: Entry price
            llm_reasoning: LLM's reasoning
            tags: Optional metadata

        Returns:
            trade_id: Use this to record exit later
        """
        trade_id = self.tracker.record_entry(
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            entry_price=entry_price,
            llm_reasoning=llm_reasoning,
            tags=tags
        )
        return trade_id

    def record_trade_exit(
        self,
        trade_id: int,
        exit_price: float,
        pnl_usd: float = None
    ) -> Optional[Dict]:
        """
        Record a trade exit and trigger review if needed.

        Args:
            trade_id: ID from record_trade_entry
            exit_price: Exit price
            pnl_usd: Actual PnL in USD

        Returns:
            Outcome dict or None
        """
        outcome = self.tracker.record_exit(
            trade_id=trade_id,
            exit_price=exit_price,
            pnl_usd=pnl_usd
        )

        if outcome:
            # Increment filter trade counts
            self.adjuster.increment_trade_count()

            # Check if review needed
            trades_since_review = self.tracker.get_trades_since_last_review()
            if trades_since_review >= self.config.review_interval:
                self._run_review_cycle()

        return outcome

    def filter_decision(
        self,
        decision: Dict
    ) -> Tuple[Dict, Optional[str]]:
        """
        Filter an LLM decision through active filters.

        Args:
            decision: Dict with symbol, action, confidence, position_size_usd

        Returns:
            (modified_decision, rejection_reason)
            rejection_reason is not None if trade should be skipped
        """
        return self.adjuster.apply_filters(decision)

    def get_prompt_enhancement(self) -> str:
        """
        Get performance context to add to LLM prompt.

        Returns:
            String with performance alerts and guidance
        """
        return self.adjuster.get_prompt_context()

    def _run_review_cycle(self):
        """Run a full analysis and adjustment cycle"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("SELF-IMPROVEMENT REVIEW CYCLE")
        logger.info("=" * 60)

        # Check minimum trades
        total_trades = self.tracker.get_trade_count()
        if total_trades < self.config.min_trades_for_analysis:
            logger.info(
                f"  Skipping: Only {total_trades} trades "
                f"(need {self.config.min_trades_for_analysis})"
            )
            return

        # Run analysis
        report = self.analyzer.analyze(
            self.tracker,
            n=self.config.rolling_window
        )

        # Apply filters if configured
        if self.config.auto_apply_filters and report.top_issues:
            filters = self.analyzer.get_filters_from_report(report)
            applied = self.adjuster.apply_analysis_results(filters)
            logger.info(f"  Applied {applied} new filters")

        # Mark review complete
        self.tracker.mark_review_complete()

        logger.info("")
        logger.info(f"SUMMARY: {report.summary}")
        logger.info("=" * 60)

    def force_review(self) -> AnalysisReport:
        """
        Force an immediate review cycle.

        Returns:
            The analysis report
        """
        total_trades = self.tracker.get_trade_count()
        if total_trades < self.config.min_trades_for_analysis:
            logger.warning(
                f"Cannot review: Only {total_trades} trades "
                f"(need {self.config.min_trades_for_analysis})"
            )
            return None

        report = self.analyzer.analyze(
            self.tracker,
            n=self.config.rolling_window
        )

        if self.config.auto_apply_filters and report.top_issues:
            filters = self.analyzer.get_filters_from_report(report)
            self.adjuster.apply_analysis_results(filters)

        self.tracker.mark_review_complete()
        return report

    def get_stats(self) -> Dict:
        """Get combined statistics"""
        overall = self.tracker.get_overall_stats(self.config.rolling_window)
        adjuster_stats = self.adjuster.get_stats()

        return {
            "strategy_name": self.STRATEGY_NAME,
            "total_trades": self.tracker.get_trade_count(),
            "trades_since_review": self.tracker.get_trades_since_last_review(),
            "overall_win_rate": overall.get("win_rate", 0),
            "overall_pnl_usd": overall.get("total_pnl_usd", 0),
            "active_filters": adjuster_stats.get("active_filters", 0),
            "block_filters": adjuster_stats.get("block_filters", 0),
            "reduce_filters": adjuster_stats.get("reduce_filters", 0)
        }

    def get_active_filters_summary(self) -> str:
        """Get human-readable summary of active filters"""
        filters = self.adjuster.get_active_filters()

        if not filters:
            return "No active filters"

        lines = [f"Active filters ({len(filters)}):"]
        for f in filters:
            lines.append(
                f"  - {f['filter_type'].upper()} {f['key']}: {f.get('reason', 'N/A')}"
            )
        return "\n".join(lines)

    def clear_filters(self):
        """Clear all active filters (use with caution)"""
        self.adjuster.clear_all_filters()
        logger.warning("[STRATEGY] All filters cleared - starting fresh")

    def get_dimension_breakdown(self) -> Dict:
        """Get performance breakdown by all dimensions"""
        return {
            "by_symbol": self.tracker.get_stats_by_dimension("symbol", self.config.rolling_window),
            "by_direction": self.tracker.get_stats_by_dimension("direction", self.config.rolling_window),
            "by_combo": self.tracker.get_combo_stats(self.config.rolling_window),
            "by_confidence": self.tracker.get_stats_by_dimension("confidence_bracket", self.config.rolling_window)
        }
