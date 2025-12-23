"""
Outcome Tracker - Records and analyzes single-asset trade outcomes

Tracks trades by multiple dimensions:
- Symbol (BTC, ETH, SOL)
- Direction (LONG, SHORT)
- Confidence bracket (0-0.5, 0.5-0.7, 0.7-0.9, 0.9+)
- Time of day (optional)

Exchange-agnostic: Works with any exchange that provides entry/exit prices.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict, field
import threading

logger = logging.getLogger(__name__)


@dataclass
class TradeOutcome:
    """Represents a single trade's outcome"""
    id: int
    open_time: str
    close_time: Optional[str]
    symbol: str
    direction: str  # "LONG" or "SHORT"
    confidence: float
    entry_price: float
    exit_price: Optional[float]
    pnl_percent: Optional[float]
    pnl_usd: Optional[float]
    is_win: Optional[bool]
    llm_reasoning: str
    hold_duration_seconds: Optional[int]
    status: str  # "open" or "closed"
    tags: Dict = field(default_factory=dict)  # Additional metadata


class OutcomeTracker:
    """
    Tracks trade outcomes by symbol, direction, and confidence.

    Thread-safe JSON persistence for tracking trade results across
    bot restarts. Provides multi-dimensional statistics for analysis.

    Usage:
        tracker = OutcomeTracker(log_file="logs/strategies/llm_outcomes.json")

        # When opening a trade
        trade_id = tracker.record_entry(
            symbol="SOL/USDT-P",
            direction="LONG",
            confidence=0.75,
            entry_price=150.0,
            llm_reasoning="Strong momentum..."
        )

        # When closing a trade
        tracker.record_exit(
            trade_id=trade_id,
            exit_price=152.0,
            pnl_usd=1.50
        )

        # Get statistics
        stats = tracker.get_stats_by_dimension("direction")
    """

    DEFAULT_LOG_FILE = "logs/strategies/self_improving_llm_outcomes.json"

    # Confidence brackets for analysis
    CONFIDENCE_BRACKETS = [
        (0.0, 0.5, "very_low"),
        (0.5, 0.7, "low"),
        (0.7, 0.85, "medium"),
        (0.85, 0.95, "high"),
        (0.95, 1.0, "very_high")
    ]

    def __init__(self, log_file: str = None):
        """
        Initialize the outcome tracker.

        Args:
            log_file: Path to JSON log file. Defaults to logs/strategies/
        """
        self.log_file = log_file or self.DEFAULT_LOG_FILE
        self._lock = threading.RLock()  # Reentrant lock to allow nested calls
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
                    if 'trades' in data and 'metadata' in data:
                        return data
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Corrupted log file, creating new: {e}")

        return {
            "metadata": {
                "created": datetime.now().isoformat(),
                "version": "1.0",
                "description": "Self-improving LLM trade outcome log"
            },
            "trades": [],
            "next_id": 1,
            "last_review_trade_count": 0
        }

    def _save(self):
        """Save data to disk (call within lock)"""
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save outcome log: {e}")

    def _get_confidence_bracket(self, confidence: float) -> str:
        """Get the bracket name for a confidence value"""
        for low, high, name in self.CONFIDENCE_BRACKETS:
            if low <= confidence < high:
                return name
        return "very_high"  # 1.0 case

    def record_entry(
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
            llm_reasoning: LLM's reasoning for this trade
            tags: Optional metadata tags

        Returns:
            trade_id: Unique ID for this trade
        """
        with self._lock:
            trade_id = self._data["next_id"]
            self._data["next_id"] += 1

            trade = TradeOutcome(
                id=trade_id,
                open_time=datetime.now().isoformat(),
                close_time=None,
                symbol=symbol,
                direction=direction.upper(),
                confidence=confidence,
                entry_price=entry_price,
                exit_price=None,
                pnl_percent=None,
                pnl_usd=None,
                is_win=None,
                llm_reasoning=llm_reasoning,
                hold_duration_seconds=None,
                status="open",
                tags=tags or {}
            )

            self._data["trades"].append(asdict(trade))
            self._save()

            conf_bracket = self._get_confidence_bracket(confidence)
            logger.info(
                f"[OUTCOME] Trade {trade_id} opened: {direction} {symbol} "
                f"@ ${entry_price:.4f} (conf: {confidence:.2f}/{conf_bracket})"
            )
            return trade_id

    def record_exit(
        self,
        trade_id: int,
        exit_price: float,
        pnl_usd: float = None
    ) -> Optional[Dict]:
        """
        Record trade exit and calculate outcome.

        Args:
            trade_id: ID returned from record_entry
            exit_price: Exit price
            pnl_usd: Actual PnL in USD (if available)

        Returns:
            Outcome dict with results, or None if trade not found
        """
        with self._lock:
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

            # Calculate PnL percent
            entry_price = trade["entry_price"]
            direction = trade["direction"]

            if direction == "LONG":
                pnl_percent = ((exit_price - entry_price) / entry_price) * 100
            else:  # SHORT
                pnl_percent = ((entry_price - exit_price) / entry_price) * 100

            # Win = positive PnL
            is_win = pnl_percent > 0

            # Calculate hold duration
            open_time = datetime.fromisoformat(trade["open_time"])
            close_time = datetime.now()
            hold_seconds = int((close_time - open_time).total_seconds())

            # Update trade
            trade["close_time"] = close_time.isoformat()
            trade["exit_price"] = exit_price
            trade["pnl_percent"] = round(pnl_percent, 4)
            trade["pnl_usd"] = round(pnl_usd, 4) if pnl_usd else None
            trade["is_win"] = is_win
            trade["hold_duration_seconds"] = hold_seconds
            trade["status"] = "closed"

            self._save()

            emoji = "✅" if is_win else "❌"
            logger.info(
                f"[OUTCOME] Trade {trade_id} closed {emoji}: "
                f"{trade['direction']} {trade['symbol']} "
                f"PnL: {pnl_percent:+.2f}% (${pnl_usd or 0:+.2f})"
            )

            return {
                "trade_id": trade_id,
                "symbol": trade["symbol"],
                "direction": trade["direction"],
                "confidence": trade["confidence"],
                "pnl_percent": pnl_percent,
                "pnl_usd": pnl_usd,
                "is_win": is_win,
                "hold_seconds": hold_seconds
            }

    def get_open_trades(self) -> List[Dict]:
        """Get all currently open trades"""
        with self._lock:
            return [t for t in self._data["trades"] if t["status"] == "open"]

    def get_stats_by_dimension(
        self,
        dimension: str,
        n: int = 50
    ) -> Dict[str, Dict]:
        """
        Get statistics grouped by a specific dimension.

        Args:
            dimension: "symbol", "direction", or "confidence_bracket"
            n: Number of recent trades to analyze

        Returns:
            Dict mapping dimension values to stats
        """
        with self._lock:
            closed = [t for t in self._data["trades"] if t["status"] == "closed"]
            recent = closed[-n:] if len(closed) >= n else closed

            if not recent:
                return {}

            stats = {}

            for trade in recent:
                if dimension == "symbol":
                    # Normalize symbol (extract base)
                    symbol = trade["symbol"]
                    if "/" in symbol:
                        key = symbol.split("/")[0]  # "SOL" from "SOL/USDT-P"
                    else:
                        key = symbol
                elif dimension == "direction":
                    key = trade["direction"]
                elif dimension == "confidence_bracket":
                    key = self._get_confidence_bracket(trade.get("confidence", 0.5))
                else:
                    key = "unknown"

                if key not in stats:
                    stats[key] = {
                        "count": 0,
                        "wins": 0,
                        "total_pnl_percent": 0.0,
                        "total_pnl_usd": 0.0
                    }

                stats[key]["count"] += 1
                if trade.get("is_win"):
                    stats[key]["wins"] += 1
                stats[key]["total_pnl_percent"] += trade.get("pnl_percent", 0)
                stats[key]["total_pnl_usd"] += trade.get("pnl_usd", 0) or 0

            # Calculate derived metrics
            for key, data in stats.items():
                count = data["count"]
                data["win_rate"] = round(data["wins"] / count, 4) if count > 0 else 0
                data["avg_pnl_percent"] = round(data["total_pnl_percent"] / count, 4) if count > 0 else 0
                data["avg_pnl_usd"] = round(data["total_pnl_usd"] / count, 4) if count > 0 else 0

            return stats

    def get_combo_stats(self, n: int = 50) -> Dict[str, Dict]:
        """
        Get statistics for symbol+direction combos.

        Args:
            n: Number of recent trades to analyze

        Returns:
            Dict mapping "SYMBOL_DIRECTION" to stats
        """
        with self._lock:
            closed = [t for t in self._data["trades"] if t["status"] == "closed"]
            recent = closed[-n:] if len(closed) >= n else closed

            if not recent:
                return {}

            stats = {}

            for trade in recent:
                symbol = trade["symbol"]
                if "/" in symbol:
                    base = symbol.split("/")[0]
                else:
                    base = symbol

                key = f"{base}_{trade['direction']}"

                if key not in stats:
                    stats[key] = {
                        "symbol": base,
                        "direction": trade["direction"],
                        "count": 0,
                        "wins": 0,
                        "total_pnl_percent": 0.0,
                        "total_pnl_usd": 0.0
                    }

                stats[key]["count"] += 1
                if trade.get("is_win"):
                    stats[key]["wins"] += 1
                stats[key]["total_pnl_percent"] += trade.get("pnl_percent", 0)
                stats[key]["total_pnl_usd"] += trade.get("pnl_usd", 0) or 0

            # Calculate derived metrics
            for key, data in stats.items():
                count = data["count"]
                data["win_rate"] = round(data["wins"] / count, 4) if count > 0 else 0
                data["avg_pnl_percent"] = round(data["total_pnl_percent"] / count, 4) if count > 0 else 0
                data["avg_pnl_usd"] = round(data["total_pnl_usd"] / count, 4) if count > 0 else 0

            return stats

    def get_overall_stats(self, n: int = 50) -> Dict:
        """
        Get overall statistics for recent trades.

        Args:
            n: Number of recent trades to analyze

        Returns:
            Dict with overall stats
        """
        with self._lock:
            closed = [t for t in self._data["trades"] if t["status"] == "closed"]
            recent = closed[-n:] if len(closed) >= n else closed

            if not recent:
                return {
                    "total": 0,
                    "wins": 0,
                    "win_rate": 0.0,
                    "total_pnl_percent": 0.0,
                    "total_pnl_usd": 0.0,
                    "avg_pnl_percent": 0.0,
                    "avg_pnl_usd": 0.0,
                    "sufficient_data": False
                }

            wins = sum(1 for t in recent if t.get("is_win"))
            total_pnl_pct = sum(t.get("pnl_percent", 0) for t in recent)
            total_pnl_usd = sum(t.get("pnl_usd", 0) or 0 for t in recent)

            return {
                "total": len(recent),
                "wins": wins,
                "win_rate": round(wins / len(recent), 4),
                "total_pnl_percent": round(total_pnl_pct, 4),
                "total_pnl_usd": round(total_pnl_usd, 4),
                "avg_pnl_percent": round(total_pnl_pct / len(recent), 4),
                "avg_pnl_usd": round(total_pnl_usd / len(recent), 4),
                "sufficient_data": len(recent) >= 10
            }

    def get_trade_count(self) -> int:
        """Get total number of closed trades"""
        with self._lock:
            return sum(1 for t in self._data["trades"] if t["status"] == "closed")

    def get_trades_since_last_review(self) -> int:
        """Get number of trades since last strategy review"""
        with self._lock:
            last_review = self._data.get("last_review_trade_count", 0)
            current = self.get_trade_count()
            return current - last_review

    def mark_review_complete(self):
        """Mark that a strategy review has been completed"""
        with self._lock:
            current = sum(1 for t in self._data["trades"] if t["status"] == "closed")
            self._data["last_review_trade_count"] = current
            self._data["last_review_time"] = datetime.now().isoformat()
            self._save()
            logger.info(f"[OUTCOME] Review marked complete at trade {current}")
