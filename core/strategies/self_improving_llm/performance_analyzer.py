"""
Performance Analyzer - Multi-dimensional analysis for single-asset LLM trading

Analyzes performance across multiple dimensions:
1. By Symbol (BTC, ETH, SOL)
2. By Direction (LONG, SHORT)
3. By Confidence bracket
4. By Symbol+Direction combo

Identifies problematic patterns and generates actionable recommendations.
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of recommended actions"""
    BLOCK = "block"           # Block this combo entirely
    REDUCE = "reduce"         # Reduce position size
    INCREASE_THRESHOLD = "increase_threshold"  # Require higher confidence
    MONITOR = "monitor"       # No action, but flag for monitoring
    NONE = "none"             # No action needed


@dataclass
class DimensionAnalysis:
    """Analysis result for a single dimension value"""
    key: str                    # e.g., "SOL", "SHORT", "SOL_SHORT"
    dimension: str              # "symbol", "direction", "combo"
    count: int
    win_rate: float
    avg_pnl_percent: float
    total_pnl_usd: float
    action: ActionType
    action_reason: str
    severity: float             # 0.0 (minor) to 1.0 (critical)


@dataclass
class AnalysisReport:
    """Complete analysis report"""
    overall_win_rate: float
    overall_pnl_usd: float
    sample_size: int
    sufficient_data: bool
    dimension_analyses: List[DimensionAnalysis]
    top_issues: List[DimensionAnalysis]  # Sorted by severity
    summary: str


class PerformanceAnalyzer:
    """
    Multi-dimensional performance analyzer for LLM trading.

    Thresholds:
    - BLOCK_WIN_RATE: Below this + MIN_TRADES = block entirely
    - REDUCE_WIN_RATE: Below this = reduce position size
    - MIN_TRADES: Minimum trades for valid analysis
    - SEVERE_LOSS_THRESHOLD: Total loss in USD triggering severe action

    Usage:
        analyzer = PerformanceAnalyzer()
        report = analyzer.analyze(tracker)

        for issue in report.top_issues:
            print(f"{issue.key}: {issue.action.value} - {issue.action_reason}")
    """

    # Win rate thresholds
    BLOCK_WIN_RATE = 0.30       # Below 30% = consider blocking
    REDUCE_WIN_RATE = 0.40      # Below 40% = reduce position
    MONITOR_WIN_RATE = 0.45     # Below 45% = monitor closely

    # Minimum trades for action
    MIN_TRADES_BLOCK = 10       # Need 10+ trades to block
    MIN_TRADES_REDUCE = 5       # Need 5+ trades to reduce
    MIN_TRADES_MONITOR = 3      # Need 3+ trades to flag

    # Loss thresholds (USD)
    SEVERE_LOSS_USD = -20.0     # Total loss triggering severe action
    MODERATE_LOSS_USD = -10.0   # Total loss triggering moderate action

    def __init__(
        self,
        block_win_rate: float = None,
        reduce_win_rate: float = None,
        min_trades_block: int = None
    ):
        """
        Initialize analyzer with optional custom thresholds.

        Args:
            block_win_rate: Custom block threshold
            reduce_win_rate: Custom reduce threshold
            min_trades_block: Custom min trades for blocking
        """
        if block_win_rate:
            self.BLOCK_WIN_RATE = block_win_rate
        if reduce_win_rate:
            self.REDUCE_WIN_RATE = reduce_win_rate
        if min_trades_block:
            self.MIN_TRADES_BLOCK = min_trades_block

        logger.info("PerformanceAnalyzer initialized")
        logger.info(f"  Block threshold: {self.BLOCK_WIN_RATE:.0%} (min {self.MIN_TRADES_BLOCK} trades)")
        logger.info(f"  Reduce threshold: {self.REDUCE_WIN_RATE:.0%} (min {self.MIN_TRADES_REDUCE} trades)")

    def analyze(self, tracker, n: int = 50) -> AnalysisReport:
        """
        Perform full multi-dimensional analysis.

        Args:
            tracker: OutcomeTracker instance
            n: Number of recent trades to analyze

        Returns:
            AnalysisReport with all findings
        """
        # Get overall stats
        overall = tracker.get_overall_stats(n)

        if not overall.get("sufficient_data", False):
            return AnalysisReport(
                overall_win_rate=overall.get("win_rate", 0),
                overall_pnl_usd=overall.get("total_pnl_usd", 0),
                sample_size=overall.get("total", 0),
                sufficient_data=False,
                dimension_analyses=[],
                top_issues=[],
                summary=f"Insufficient data: {overall.get('total', 0)} trades (need 10+)"
            )

        dimension_analyses = []

        # Analyze by symbol
        symbol_stats = tracker.get_stats_by_dimension("symbol", n)
        for key, stats in symbol_stats.items():
            analysis = self._analyze_dimension(key, "symbol", stats)
            if analysis:
                dimension_analyses.append(analysis)

        # Analyze by direction
        direction_stats = tracker.get_stats_by_dimension("direction", n)
        for key, stats in direction_stats.items():
            analysis = self._analyze_dimension(key, "direction", stats)
            if analysis:
                dimension_analyses.append(analysis)

        # Analyze by combo (most granular)
        combo_stats = tracker.get_combo_stats(n)
        for key, stats in combo_stats.items():
            analysis = self._analyze_dimension(key, "combo", stats)
            if analysis:
                dimension_analyses.append(analysis)

        # Sort by severity for top issues
        issues = [a for a in dimension_analyses if a.action != ActionType.NONE]
        top_issues = sorted(issues, key=lambda x: x.severity, reverse=True)[:5]

        # Generate summary
        summary = self._generate_summary(overall, top_issues)

        report = AnalysisReport(
            overall_win_rate=overall["win_rate"],
            overall_pnl_usd=overall["total_pnl_usd"],
            sample_size=overall["total"],
            sufficient_data=True,
            dimension_analyses=dimension_analyses,
            top_issues=top_issues,
            summary=summary
        )

        self._log_report(report)
        return report

    def _analyze_dimension(
        self,
        key: str,
        dimension: str,
        stats: Dict
    ) -> Optional[DimensionAnalysis]:
        """
        Analyze a single dimension value.

        Args:
            key: The dimension value (e.g., "SOL", "SHORT", "SOL_SHORT")
            dimension: Type of dimension
            stats: Statistics dict for this value

        Returns:
            DimensionAnalysis or None if insufficient data
        """
        count = stats.get("count", 0)
        win_rate = stats.get("win_rate", 0)
        avg_pnl_pct = stats.get("avg_pnl_percent", 0)
        total_pnl = stats.get("total_pnl_usd", 0)

        # Skip if no data
        if count == 0:
            return None

        # Determine action
        action = ActionType.NONE
        reason = ""
        severity = 0.0

        # Check for blocking conditions
        if count >= self.MIN_TRADES_BLOCK and win_rate < self.BLOCK_WIN_RATE:
            action = ActionType.BLOCK
            reason = f"{win_rate:.0%} win rate over {count} trades - BLOCK"
            severity = 1.0 - win_rate  # Lower win rate = higher severity

        elif total_pnl < self.SEVERE_LOSS_USD and count >= self.MIN_TRADES_REDUCE:
            action = ActionType.BLOCK
            reason = f"${total_pnl:.2f} total loss - BLOCK"
            severity = min(1.0, abs(total_pnl) / 50.0)  # Scale by loss

        # Check for reduction conditions
        elif count >= self.MIN_TRADES_REDUCE and win_rate < self.REDUCE_WIN_RATE:
            action = ActionType.REDUCE
            reason = f"{win_rate:.0%} win rate - reduce position 50%"
            severity = 0.6 - win_rate

        elif total_pnl < self.MODERATE_LOSS_USD and count >= self.MIN_TRADES_REDUCE:
            action = ActionType.REDUCE
            reason = f"${total_pnl:.2f} total loss - reduce position 50%"
            severity = min(0.7, abs(total_pnl) / 30.0)

        # Check for monitoring conditions
        elif count >= self.MIN_TRADES_MONITOR and win_rate < self.MONITOR_WIN_RATE:
            action = ActionType.MONITOR
            reason = f"{win_rate:.0%} win rate - monitoring"
            severity = 0.3

        # Ensure severity is clamped
        severity = max(0.0, min(1.0, severity))

        return DimensionAnalysis(
            key=key,
            dimension=dimension,
            count=count,
            win_rate=win_rate,
            avg_pnl_percent=avg_pnl_pct,
            total_pnl_usd=total_pnl,
            action=action,
            action_reason=reason,
            severity=severity
        )

    def _generate_summary(
        self,
        overall: Dict,
        top_issues: List[DimensionAnalysis]
    ) -> str:
        """Generate a human-readable summary"""
        parts = []

        win_rate = overall["win_rate"]
        total_pnl = overall["total_pnl_usd"]
        count = overall["total"]

        # Overall assessment
        if win_rate >= 0.50:
            parts.append(f"HEALTHY: {win_rate:.0%} win rate, ${total_pnl:+.2f} over {count} trades.")
        elif win_rate >= 0.40:
            parts.append(f"NEEDS WORK: {win_rate:.0%} win rate, ${total_pnl:+.2f} over {count} trades.")
        else:
            parts.append(f"CRITICAL: {win_rate:.0%} win rate, ${total_pnl:+.2f} over {count} trades.")

        # Top issues
        if top_issues:
            parts.append(f" Top issues:")
            for issue in top_issues[:3]:
                parts.append(f" - {issue.key}: {issue.action.value} ({issue.action_reason})")

        return "".join(parts)

    def _log_report(self, report: AnalysisReport):
        """Log the analysis report"""
        logger.info("=" * 70)
        logger.info("PERFORMANCE ANALYSIS REPORT")
        logger.info("=" * 70)
        logger.info(f"  Sample size: {report.sample_size} trades")
        logger.info(f"  Overall win rate: {report.overall_win_rate:.1%}")
        logger.info(f"  Total PnL: ${report.overall_pnl_usd:+.2f}")
        logger.info("")

        if report.top_issues:
            logger.info("TOP ISSUES:")
            for issue in report.top_issues:
                logger.info(
                    f"  {issue.key} ({issue.dimension}): {issue.action.value} "
                    f"[{issue.win_rate:.0%} win, ${issue.total_pnl_usd:+.2f}]"
                )
                logger.info(f"    -> {issue.action_reason}")
        else:
            logger.info("  No critical issues found")

        logger.info("=" * 70)

    def get_filters_from_report(self, report: AnalysisReport) -> List[Dict]:
        """
        Extract actionable filters from analysis report.

        Args:
            report: AnalysisReport from analyze()

        Returns:
            List of filter dicts ready for StrategyAdjuster
        """
        filters = []

        for issue in report.top_issues:
            if issue.action == ActionType.NONE:
                continue

            filter_dict = {
                "key": issue.key,
                "dimension": issue.dimension,
                "action": issue.action.value,
                "reason": issue.action_reason,
                "severity": issue.severity,
                "stats": {
                    "count": issue.count,
                    "win_rate": issue.win_rate,
                    "total_pnl": issue.total_pnl_usd
                }
            }
            filters.append(filter_dict)

        return filters
