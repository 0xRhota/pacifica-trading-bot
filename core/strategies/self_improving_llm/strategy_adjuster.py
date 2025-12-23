"""
Strategy Adjuster - Applies dynamic filters and generates prompt hints

Based on PerformanceAnalyzer findings, this component:
1. Maintains a list of active trading filters
2. Applies filters to incoming LLM decisions
3. Generates performance context for LLM prompts
4. Tracks filter effectiveness over time

Exchange-agnostic: Works with any LLM trading system.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
import threading

logger = logging.getLogger(__name__)


@dataclass
class TradeFilter:
    """A single trading filter"""
    id: str                      # Unique identifier
    created_time: str            # When filter was created
    filter_type: str             # "block", "reduce", "confidence_threshold"
    dimension: str               # "symbol", "direction", "combo"
    key: str                     # The value to match (e.g., "SOL", "SHORT", "SOL_SHORT")
    action_value: float          # For reduce: 0.5 = 50% size. For threshold: min confidence
    reason: str                  # Why this filter was created
    source_stats: Dict           # Stats that triggered this filter
    active: bool = True          # Whether filter is currently active
    expires_after_trades: int = 20  # Auto-expire after N successful trades
    trades_since_created: int = 0


class StrategyAdjuster:
    """
    Manages dynamic trading filters and LLM prompt enhancement.

    The adjuster sits between the LLM decision and execution, applying
    learned filters to prevent repeating past mistakes.

    Filter Types:
    - BLOCK: Completely reject the trade
    - REDUCE: Reduce position size by action_value (0.5 = 50%)
    - CONFIDENCE_THRESHOLD: Require confidence >= action_value

    Usage:
        adjuster = StrategyAdjuster()

        # Load filters from analysis
        adjuster.apply_analysis_results(analyzer_report)

        # Check if a decision should be modified
        decision = {"symbol": "SOL/USDT-P", "action": "LONG", "confidence": 0.7}
        modified, reason = adjuster.apply_filters(decision)

        # Get prompt context for LLM
        context = adjuster.get_prompt_context()
    """

    DEFAULT_STATE_FILE = "logs/strategies/self_improving_llm_state.json"

    def __init__(self, state_file: str = None):
        """
        Initialize the strategy adjuster.

        Args:
            state_file: Path to persist filter state
        """
        self.state_file = state_file or self.DEFAULT_STATE_FILE
        self._lock = threading.Lock()
        self._state = self._load_or_create()

        # Ensure directory exists
        Path(self.state_file).parent.mkdir(parents=True, exist_ok=True)

        logger.info("StrategyAdjuster initialized")
        active_filters = [f for f in self._state["filters"] if f.get("active", True)]
        logger.info(f"  Active filters: {len(active_filters)}")

    def _load_or_create(self) -> Dict:
        """Load existing state or create new"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    if 'filters' in data:
                        return data
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Corrupted state file, creating new: {e}")

        return {
            "metadata": {
                "created": datetime.now().isoformat(),
                "version": "1.0"
            },
            "filters": [],
            "adjustment_history": [],
            "last_review": None
        }

    def _save(self):
        """Save state to disk"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self._state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save adjuster state: {e}")

    def add_filter(
        self,
        filter_type: str,
        dimension: str,
        key: str,
        action_value: float,
        reason: str,
        source_stats: Dict = None
    ) -> str:
        """
        Add a new trading filter.

        Args:
            filter_type: "block", "reduce", or "confidence_threshold"
            dimension: "symbol", "direction", or "combo"
            key: Value to match (e.g., "SOL", "SHORT", "SOL_SHORT")
            action_value: For reduce: multiplier. For threshold: min confidence
            reason: Human-readable reason
            source_stats: Stats that triggered this filter

        Returns:
            filter_id: Unique ID for this filter
        """
        with self._lock:
            # Check for existing filter on same key
            for f in self._state["filters"]:
                if f["dimension"] == dimension and f["key"] == key and f.get("active", True):
                    # Update existing filter if more restrictive
                    if filter_type == "block" and f["filter_type"] != "block":
                        f["filter_type"] = "block"
                        f["reason"] = reason
                        f["source_stats"] = source_stats or {}
                        self._save()
                        logger.info(f"[ADJUSTER] Upgraded filter {f['id']} to BLOCK")
                        return f["id"]
                    logger.info(f"[ADJUSTER] Filter already exists for {dimension}:{key}")
                    return f["id"]

            filter_id = f"{dimension}_{key}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            new_filter = {
                "id": filter_id,
                "created_time": datetime.now().isoformat(),
                "filter_type": filter_type,
                "dimension": dimension,
                "key": key,
                "action_value": action_value,
                "reason": reason,
                "source_stats": source_stats or {},
                "active": True,
                "expires_after_trades": 20,
                "trades_since_created": 0
            }

            self._state["filters"].append(new_filter)
            self._state["adjustment_history"].append({
                "time": datetime.now().isoformat(),
                "action": "add_filter",
                "filter_id": filter_id,
                "details": f"{filter_type} on {dimension}:{key}"
            })
            self._save()

            logger.info(f"[ADJUSTER] Added filter: {filter_type} {dimension}:{key}")
            return filter_id

    def apply_filters(
        self,
        decision: Dict
    ) -> Tuple[Dict, Optional[str]]:
        """
        Apply all active filters to a trading decision.

        Args:
            decision: Trading decision dict with keys:
                - symbol: Trading symbol
                - action: "LONG" or "SHORT"
                - confidence: 0.0-1.0
                - position_size_usd: (optional) size in USD

        Returns:
            (modified_decision, rejection_reason)
            If rejection_reason is not None, trade should be skipped
        """
        with self._lock:
            symbol = decision.get("symbol", "")
            action = decision.get("action", "").upper()
            confidence = decision.get("confidence", 0.5)
            size = decision.get("position_size_usd", 0)

            # Normalize symbol
            if "/" in symbol:
                base_symbol = symbol.split("/")[0]
            else:
                base_symbol = symbol

            # Create combo key
            combo_key = f"{base_symbol}_{action}"

            # Track modifications
            modified = decision.copy()
            rejection_reason = None
            applied_filters = []

            for f in self._state["filters"]:
                if not f.get("active", True):
                    continue

                # Check if filter matches
                matches = False
                if f["dimension"] == "symbol" and f["key"] == base_symbol:
                    matches = True
                elif f["dimension"] == "direction" and f["key"] == action:
                    matches = True
                elif f["dimension"] == "combo" and f["key"] == combo_key:
                    matches = True

                if not matches:
                    continue

                # Apply filter
                filter_type = f["filter_type"]

                if filter_type == "block":
                    rejection_reason = f"BLOCKED by filter: {f['reason']}"
                    applied_filters.append(f["id"])
                    break

                elif filter_type == "reduce":
                    multiplier = f.get("action_value", 0.5)
                    if size > 0:
                        original = size
                        modified["position_size_usd"] = size * multiplier
                        logger.info(
                            f"[ADJUSTER] Reduced position: ${original:.2f} -> "
                            f"${modified['position_size_usd']:.2f}"
                        )
                    applied_filters.append(f["id"])

                elif filter_type == "confidence_threshold":
                    min_conf = f.get("action_value", 0.8)
                    if confidence < min_conf:
                        rejection_reason = (
                            f"BLOCKED: Confidence {confidence:.2f} below "
                            f"threshold {min_conf:.2f} ({f['reason']})"
                        )
                        applied_filters.append(f["id"])
                        break

            # Log what happened
            if rejection_reason:
                logger.warning(f"[ADJUSTER] Trade rejected: {rejection_reason}")
            elif applied_filters:
                logger.info(f"[ADJUSTER] Applied {len(applied_filters)} filter(s)")

            return modified, rejection_reason

    def apply_analysis_results(self, filters: List[Dict]) -> int:
        """
        Apply filters from PerformanceAnalyzer.

        Args:
            filters: List of filter dicts from analyzer.get_filters_from_report()

        Returns:
            Number of filters added/updated
        """
        count = 0
        for f in filters:
            action = f.get("action", "")
            if action == "block":
                filter_type = "block"
                action_value = 1.0
            elif action == "reduce":
                filter_type = "reduce"
                action_value = 0.5
            elif action == "increase_threshold":
                filter_type = "confidence_threshold"
                action_value = 0.85
            else:
                continue

            self.add_filter(
                filter_type=filter_type,
                dimension=f.get("dimension", "combo"),
                key=f.get("key", ""),
                action_value=action_value,
                reason=f.get("reason", "Performance-based filter"),
                source_stats=f.get("stats", {})
            )
            count += 1

        logger.info(f"[ADJUSTER] Applied {count} filters from analysis")
        return count

    def get_prompt_context(self) -> str:
        """
        Generate performance context for LLM prompts.

        Returns:
            String to append to LLM prompt with performance hints
        """
        with self._lock:
            active_filters = [f for f in self._state["filters"] if f.get("active", True)]

            if not active_filters:
                return ""

            lines = [
                "",
                "=== PERFORMANCE ALERTS ===",
                "Based on recent trade analysis, note the following:"
            ]

            # Group by action type
            blocks = []
            reduces = []
            thresholds = []

            for f in active_filters:
                key = f["key"]
                reason = f.get("reason", "")
                stats = f.get("source_stats", {})

                if f["filter_type"] == "block":
                    win_rate = stats.get("win_rate", 0)
                    pnl = stats.get("total_pnl", 0)
                    blocks.append(f"- {key}: {win_rate:.0%} win rate, ${pnl:+.2f} total")
                elif f["filter_type"] == "reduce":
                    win_rate = stats.get("win_rate", 0)
                    reduces.append(f"- {key}: {win_rate:.0%} win rate (size reduced 50%)")
                elif f["filter_type"] == "confidence_threshold":
                    min_conf = f.get("action_value", 0.8)
                    thresholds.append(f"- {key}: requires {min_conf:.0%}+ confidence")

            if blocks:
                lines.append("")
                lines.append("BLOCKED (do NOT trade these):")
                lines.extend(blocks)

            if reduces:
                lines.append("")
                lines.append("HIGH RISK (approach with caution):")
                lines.extend(reduces)

            if thresholds:
                lines.append("")
                lines.append("CONFIDENCE REQUIREMENTS:")
                lines.extend(thresholds)

            lines.append("")
            lines.append("Focus on opportunities NOT listed above.")
            lines.append("=== END ALERTS ===")

            return "\n".join(lines)

    def get_active_filters(self) -> List[Dict]:
        """Get list of all active filters"""
        with self._lock:
            return [f for f in self._state["filters"] if f.get("active", True)]

    def deactivate_filter(self, filter_id: str) -> bool:
        """Deactivate a filter by ID"""
        with self._lock:
            for f in self._state["filters"]:
                if f["id"] == filter_id:
                    f["active"] = False
                    self._state["adjustment_history"].append({
                        "time": datetime.now().isoformat(),
                        "action": "deactivate_filter",
                        "filter_id": filter_id
                    })
                    self._save()
                    logger.info(f"[ADJUSTER] Deactivated filter: {filter_id}")
                    return True
            return False

    def clear_all_filters(self):
        """Clear all filters (use with caution)"""
        with self._lock:
            count = len([f for f in self._state["filters"] if f.get("active", True)])
            for f in self._state["filters"]:
                f["active"] = False
            self._state["adjustment_history"].append({
                "time": datetime.now().isoformat(),
                "action": "clear_all",
                "details": f"Cleared {count} filters"
            })
            self._save()
            logger.info(f"[ADJUSTER] Cleared {count} filters")

    def increment_trade_count(self, filter_ids: List[str] = None):
        """
        Increment trade count for filters (for expiration tracking).

        Args:
            filter_ids: Specific filters to increment, or None for all active
        """
        with self._lock:
            for f in self._state["filters"]:
                if not f.get("active", True):
                    continue

                if filter_ids is None or f["id"] in filter_ids:
                    f["trades_since_created"] = f.get("trades_since_created", 0) + 1

                    # Check for expiration
                    expires = f.get("expires_after_trades", 20)
                    if f["trades_since_created"] >= expires:
                        f["active"] = False
                        logger.info(
                            f"[ADJUSTER] Filter {f['id']} expired after "
                            f"{f['trades_since_created']} trades"
                        )

            self._save()

    def get_stats(self) -> Dict:
        """Get adjuster statistics"""
        with self._lock:
            active = [f for f in self._state["filters"] if f.get("active", True)]
            return {
                "total_filters": len(self._state["filters"]),
                "active_filters": len(active),
                "block_filters": len([f for f in active if f["filter_type"] == "block"]),
                "reduce_filters": len([f for f in active if f["filter_type"] == "reduce"]),
                "threshold_filters": len([f for f in active if f["filter_type"] == "confidence_threshold"]),
                "adjustment_history_count": len(self._state.get("adjustment_history", []))
            }
