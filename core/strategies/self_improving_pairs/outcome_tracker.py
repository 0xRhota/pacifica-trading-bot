"""
Outcome Tracker - Records and analyzes trade outcomes

This component tracks actual trade results to determine if the LLM's
direction calls were correct. It maintains a JSON log of all trades
with entry/exit prices and calculates whether each direction choice
was profitable.

Exchange-agnostic: Works with any exchange that provides prices.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import threading

logger = logging.getLogger(__name__)


@dataclass
class TradeOutcome:
    """Represents a single trade's outcome"""
    id: int
    open_time: str
    close_time: Optional[str]
    long_symbol: str
    short_symbol: str
    llm_reasoning: str
    entry_prices: Dict[str, float]  # {symbol: price}
    exit_prices: Optional[Dict[str, float]]
    returns: Optional[Dict[str, float]]  # {symbol: percent_return}
    correct_direction: Optional[bool]
    spread_return: Optional[float]  # long_return - short_return
    status: str  # "open" or "closed"


class OutcomeTracker:
    """
    Tracks trade outcomes and determines direction accuracy.

    Thread-safe JSON persistence for tracking trade results across
    bot restarts. Calculates whether the LLM picked the right asset
    to long based on actual returns.

    Usage:
        tracker = OutcomeTracker(log_file="logs/strategies/pairs_outcomes.json")

        # When opening a trade
        trade_id = tracker.record_entry(
            long_symbol="ETH-USD",
            short_symbol="BTC-USD",
            entry_prices={"ETH-USD": 3000.0, "BTC-USD": 90000.0},
            llm_reasoning="ETH showing stronger momentum..."
        )

        # When closing a trade
        tracker.record_exit(
            trade_id=trade_id,
            exit_prices={"ETH-USD": 3100.0, "BTC-USD": 91000.0}
        )

        # Get rolling statistics
        stats = tracker.get_rolling_stats(n=10)
        # Returns: {"accuracy": 0.6, "eth_bias_accuracy": 0.5, ...}
    """

    DEFAULT_LOG_FILE = "logs/strategies/self_improving_pairs_outcomes.json"

    def __init__(self, log_file: str = None):
        """
        Initialize the outcome tracker.

        Args:
            log_file: Path to JSON log file. Defaults to logs/strategies/
        """
        self.log_file = log_file or self.DEFAULT_LOG_FILE
        self._lock = threading.Lock()
        self._data = self._load_or_create()

        # Ensure directory exists
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"OutcomeTracker initialized: {self.log_file}")
        logger.info(f"  Loaded {len(self._data['trades'])} historical trades")

    def _load_or_create(self) -> Dict:
        """Load existing data or create new structure"""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    data = json.load(f)
                    # Validate structure
                    if 'trades' in data and 'metadata' in data:
                        return data
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Corrupted log file, creating new: {e}")

        # Create new structure
        return {
            "metadata": {
                "created": datetime.now().isoformat(),
                "version": "1.0",
                "description": "Self-improving pairs trade outcome log"
            },
            "trades": [],
            "next_id": 1
        }

    def _save(self):
        """Save data to disk (call within lock)"""
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save outcome log: {e}")

    def record_entry(
        self,
        long_symbol: str,
        short_symbol: str,
        entry_prices: Dict[str, float],
        llm_reasoning: str
    ) -> int:
        """
        Record a new trade entry.

        Args:
            long_symbol: Symbol being longed (e.g., "ETH-USD")
            short_symbol: Symbol being shorted (e.g., "BTC-USD")
            entry_prices: Dict of {symbol: entry_price}
            llm_reasoning: The LLM's reasoning for this direction

        Returns:
            trade_id: Unique ID for this trade (use to record exit)
        """
        with self._lock:
            trade_id = self._data["next_id"]
            self._data["next_id"] += 1

            trade = TradeOutcome(
                id=trade_id,
                open_time=datetime.now().isoformat(),
                close_time=None,
                long_symbol=long_symbol,
                short_symbol=short_symbol,
                llm_reasoning=llm_reasoning,
                entry_prices=entry_prices,
                exit_prices=None,
                returns=None,
                correct_direction=None,
                spread_return=None,
                status="open"
            )

            self._data["trades"].append(asdict(trade))
            self._save()

            logger.info(f"[OUTCOME] Trade {trade_id} opened: Long {long_symbol}, Short {short_symbol}")
            return trade_id

    def record_exit(
        self,
        trade_id: int,
        exit_prices: Dict[str, float]
    ) -> Optional[Dict]:
        """
        Record trade exit and calculate outcome.

        Args:
            trade_id: ID returned from record_entry
            exit_prices: Dict of {symbol: exit_price}

        Returns:
            Outcome dict with returns and correctness, or None if trade not found
        """
        with self._lock:
            # Find the trade
            trade = None
            for t in self._data["trades"]:
                if t["id"] == trade_id:
                    trade = t
                    break

            if not trade:
                logger.error(f"[OUTCOME] Trade {trade_id} not found")
                return None

            if trade["status"] == "closed":
                logger.warning(f"[OUTCOME] Trade {trade_id} already closed")
                return None

            # Calculate returns
            long_symbol = trade["long_symbol"]
            short_symbol = trade["short_symbol"]

            entry_long = trade["entry_prices"].get(long_symbol, 0)
            entry_short = trade["entry_prices"].get(short_symbol, 0)
            exit_long = exit_prices.get(long_symbol, 0)
            exit_short = exit_prices.get(short_symbol, 0)

            # Long return: (exit - entry) / entry * 100
            # Short return: (entry - exit) / entry * 100 (profit when price drops)
            long_return = ((exit_long - entry_long) / entry_long * 100) if entry_long > 0 else 0
            short_return = ((entry_short - exit_short) / entry_short * 100) if entry_short > 0 else 0

            # Combined spread return (what we actually made/lost)
            spread_return = long_return + short_return

            # Direction was correct if long asset outperformed short asset
            # i.e., long_return > -short_return (the asset we longed went up more)
            long_asset_return = long_return
            short_asset_return = -short_return  # What short asset actually did (positive = went up)
            correct_direction = long_asset_return > short_asset_return

            # Update trade
            trade["close_time"] = datetime.now().isoformat()
            trade["exit_prices"] = exit_prices
            trade["returns"] = {
                long_symbol: round(long_return, 4),
                short_symbol: round(short_return, 4)
            }
            trade["spread_return"] = round(spread_return, 4)
            trade["correct_direction"] = correct_direction
            trade["status"] = "closed"

            self._save()

            direction_emoji = "✅" if correct_direction else "❌"
            logger.info(
                f"[OUTCOME] Trade {trade_id} closed {direction_emoji}: "
                f"Long {long_symbol} {long_return:+.2f}%, "
                f"Short {short_symbol} {short_return:+.2f}%, "
                f"Spread: {spread_return:+.2f}%"
            )

            return {
                "trade_id": trade_id,
                "long_return": long_return,
                "short_return": short_return,
                "spread_return": spread_return,
                "correct_direction": correct_direction
            }

    def get_open_trade(self) -> Optional[Dict]:
        """Get the currently open trade, if any"""
        with self._lock:
            for trade in reversed(self._data["trades"]):
                if trade["status"] == "open":
                    return trade
            return None

    def get_rolling_stats(self, n: int = 10) -> Dict:
        """
        Get statistics for the last n closed trades.

        Args:
            n: Number of recent trades to analyze

        Returns:
            Dict with accuracy metrics and direction breakdown
        """
        with self._lock:
            # Get last n closed trades
            closed_trades = [t for t in self._data["trades"] if t["status"] == "closed"]
            recent = closed_trades[-n:] if len(closed_trades) >= n else closed_trades

            if not recent:
                return {
                    "total": 0,
                    "correct": 0,
                    "accuracy": 0.0,
                    "avg_spread_return": 0.0,
                    "eth_bias": {"count": 0, "correct": 0, "accuracy": 0.0},
                    "btc_bias": {"count": 0, "correct": 0, "accuracy": 0.0},
                    "sufficient_data": False
                }

            total = len(recent)
            correct = sum(1 for t in recent if t.get("correct_direction", False))
            accuracy = correct / total if total > 0 else 0.0

            # Average spread return
            spread_returns = [t.get("spread_return", 0) for t in recent]
            avg_spread = sum(spread_returns) / len(spread_returns) if spread_returns else 0.0

            # Breakdown by direction (which asset was longed)
            eth_trades = [t for t in recent if "ETH" in t.get("long_symbol", "").upper()]
            btc_trades = [t for t in recent if "BTC" in t.get("long_symbol", "").upper()]

            eth_correct = sum(1 for t in eth_trades if t.get("correct_direction", False))
            btc_correct = sum(1 for t in btc_trades if t.get("correct_direction", False))

            return {
                "total": total,
                "correct": correct,
                "accuracy": round(accuracy, 4),
                "avg_spread_return": round(avg_spread, 4),
                "eth_bias": {
                    "count": len(eth_trades),
                    "correct": eth_correct,
                    "accuracy": round(eth_correct / len(eth_trades), 4) if eth_trades else 0.0
                },
                "btc_bias": {
                    "count": len(btc_trades),
                    "correct": btc_correct,
                    "accuracy": round(btc_correct / len(btc_trades), 4) if btc_trades else 0.0
                },
                "sufficient_data": total >= 5
            }

    def get_trade_count(self) -> int:
        """Get total number of closed trades"""
        with self._lock:
            return sum(1 for t in self._data["trades"] if t["status"] == "closed")

    def get_trades_since_last_review(self) -> int:
        """Get number of trades since last strategy review"""
        with self._lock:
            last_review = self._data.get("last_review_trade_count", 0)
            current_count = sum(1 for t in self._data["trades"] if t["status"] == "closed")
            return current_count - last_review

    def mark_review_complete(self):
        """Mark that a strategy review has been completed"""
        with self._lock:
            current_count = sum(1 for t in self._data["trades"] if t["status"] == "closed")
            self._data["last_review_trade_count"] = current_count
            self._data["last_review_time"] = datetime.now().isoformat()
            self._save()
            logger.info(f"[OUTCOME] Review marked complete at trade {current_count}")
