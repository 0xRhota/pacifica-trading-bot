"""
Self-Learning Module for Trading Bot
Analyzes past trades to generate insights for the LLM

Features:
- Win/loss rate per symbol
- Best performing setups (RSI ranges, MACD conditions)
- Worst performing patterns to avoid
- Time-based performance (hour of day)
- Confidence calibration (was high confidence accurate?)
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)


class SelfLearning:
    """Analyzes trade history to generate learning insights for LLM"""

    # Shared notes file for all bots
    NOTES_FILE = Path(__file__).parent.parent / "logs" / "user_notes.json"

    def __init__(self, trade_tracker, min_trades_for_insight: int = 5):
        """
        Initialize self-learning module

        Args:
            trade_tracker: TradeTracker instance
            min_trades_for_insight: Minimum trades needed before generating insights
        """
        self.tracker = trade_tracker
        self.min_trades = min_trades_for_insight
        self.insights_cache = None
        self.cache_time = None
        self.cache_ttl = 300  # 5 min cache

    @classmethod
    def add_user_note(cls, message: str, expires_hours: int = 24) -> bool:
        """
        Add a user note that all bots will see in their learning context

        Args:
            message: The note to add
            expires_hours: How long the note should persist (default 24h)

        Returns:
            True if successful
        """
        try:
            notes = []
            if cls.NOTES_FILE.exists():
                with open(cls.NOTES_FILE, 'r') as f:
                    notes = json.load(f)

            # Add new note
            notes.append({
                'timestamp': datetime.now().isoformat(),
                'expires': (datetime.now() + timedelta(hours=expires_hours)).isoformat(),
                'message': message
            })

            # Save
            cls.NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(cls.NOTES_FILE, 'w') as f:
                json.dump(notes, f, indent=2)

            logger.info(f"Added user note: {message[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to add user note: {e}")
            return False

    @classmethod
    def get_active_notes(cls) -> List[Dict]:
        """Get all non-expired user notes"""
        if not cls.NOTES_FILE.exists():
            return []

        try:
            with open(cls.NOTES_FILE, 'r') as f:
                notes = json.load(f)

            # Filter expired notes
            now = datetime.now()
            active = []
            for note in notes:
                try:
                    expires = datetime.fromisoformat(note['expires'])
                    if expires > now:
                        active.append(note)
                except (ValueError, KeyError):
                    continue

            return active
        except Exception as e:
            logger.error(f"Failed to read user notes: {e}")
            return []

    def _get_closed_trades(self, hours: int = 168) -> List[Dict]:
        """Get closed trades from last N hours (default: 7 days)"""
        cutoff = datetime.now() - timedelta(hours=hours)
        closed = []

        for trade in self.tracker.trades:
            if trade.get('status') == 'closed' and trade.get('exit_timestamp'):
                try:
                    exit_time = datetime.fromisoformat(trade['exit_timestamp'])
                    if exit_time >= cutoff:
                        closed.append(trade)
                except (ValueError, TypeError):
                    continue

        return closed

    def analyze_symbol_performance(self, hours: int = 168) -> Dict[str, Dict]:
        """
        Analyze win/loss rate per symbol

        Returns:
            Dict mapping symbol to {wins, losses, win_rate, avg_pnl, total_pnl}
        """
        trades = self._get_closed_trades(hours)
        symbol_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnls': []})

        for trade in trades:
            symbol = trade.get('symbol')
            pnl = trade.get('pnl') or 0

            if pnl > 0:
                symbol_stats[symbol]['wins'] += 1
            else:
                symbol_stats[symbol]['losses'] += 1
            symbol_stats[symbol]['pnls'].append(pnl)

        # Calculate stats
        results = {}
        for symbol, stats in symbol_stats.items():
            total = stats['wins'] + stats['losses']
            results[symbol] = {
                'wins': stats['wins'],
                'losses': stats['losses'],
                'total': total,
                'win_rate': stats['wins'] / total if total > 0 else 0,
                'avg_pnl': sum(stats['pnls']) / len(stats['pnls']) if stats['pnls'] else 0,
                'total_pnl': sum(stats['pnls'])
            }

        return results

    def analyze_side_performance(self, hours: int = 168) -> Dict[str, Dict]:
        """
        Analyze LONG vs SHORT performance

        Returns:
            Dict with 'LONG' and 'SHORT' stats
        """
        trades = self._get_closed_trades(hours)
        side_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnls': []})

        for trade in trades:
            side = trade.get('side', '').upper()
            if side in ['BUY', 'LONG']:
                side = 'LONG'
            elif side in ['SELL', 'SHORT']:
                side = 'SHORT'
            else:
                continue

            pnl = trade.get('pnl') or 0
            if pnl > 0:
                side_stats[side]['wins'] += 1
            else:
                side_stats[side]['losses'] += 1
            side_stats[side]['pnls'].append(pnl)

        results = {}
        for side, stats in side_stats.items():
            total = stats['wins'] + stats['losses']
            results[side] = {
                'wins': stats['wins'],
                'losses': stats['losses'],
                'total': total,
                'win_rate': stats['wins'] / total if total > 0 else 0,
                'avg_pnl': sum(stats['pnls']) / len(stats['pnls']) if stats['pnls'] else 0,
                'total_pnl': sum(stats['pnls'])
            }

        return results

    def analyze_confidence_calibration(self, hours: int = 168) -> Dict:
        """
        Check if confidence scores correlate with actual outcomes

        Returns:
            Dict with confidence brackets and their actual win rates
        """
        trades = self._get_closed_trades(hours)

        # Bucket by confidence ranges
        buckets = {
            'low (0.5-0.6)': {'wins': 0, 'total': 0},
            'medium (0.6-0.75)': {'wins': 0, 'total': 0},
            'high (0.75-0.9)': {'wins': 0, 'total': 0},
            'very_high (0.9+)': {'wins': 0, 'total': 0}
        }

        for trade in trades:
            conf = trade.get('confidence') or 0.5  # Handle None values
            pnl = trade.get('pnl') or 0

            if conf < 0.6:
                bucket = 'low (0.5-0.6)'
            elif conf < 0.75:
                bucket = 'medium (0.6-0.75)'
            elif conf < 0.9:
                bucket = 'high (0.75-0.9)'
            else:
                bucket = 'very_high (0.9+)'

            buckets[bucket]['total'] += 1
            if pnl > 0:
                buckets[bucket]['wins'] += 1

        # Calculate win rates per bucket
        results = {}
        for bucket, stats in buckets.items():
            results[bucket] = {
                'total': stats['total'],
                'wins': stats['wins'],
                'win_rate': stats['wins'] / stats['total'] if stats['total'] > 0 else 0
            }

        return results

    def get_best_symbols(self, hours: int = 168, min_trades: int = 3) -> List[Tuple[str, float]]:
        """Get symbols with best win rates (min trades required)"""
        perf = self.analyze_symbol_performance(hours)

        good_symbols = []
        for symbol, stats in perf.items():
            if stats['total'] >= min_trades and stats['win_rate'] >= 0.5:
                good_symbols.append((symbol, stats['win_rate'], stats['total_pnl']))

        # Sort by win rate, then by total P/L
        good_symbols.sort(key=lambda x: (x[1], x[2]), reverse=True)
        return [(s, wr) for s, wr, _ in good_symbols[:10]]

    def get_worst_symbols(self, hours: int = 168, min_trades: int = 3) -> List[Tuple[str, float]]:
        """Get symbols with worst win rates (to avoid)"""
        perf = self.analyze_symbol_performance(hours)

        bad_symbols = []
        for symbol, stats in perf.items():
            if stats['total'] >= min_trades and stats['win_rate'] < 0.4:
                bad_symbols.append((symbol, stats['win_rate'], stats['total_pnl']))

        # Sort by win rate ascending (worst first)
        bad_symbols.sort(key=lambda x: (x[1], x[2]))
        return [(s, wr) for s, wr, _ in bad_symbols[:10]]

    def generate_learning_context(self, hours: int = 168) -> str:
        """
        Generate a learning context string to inject into LLM prompt

        Returns:
            Formatted string with trading insights from past performance
        """
        # Check cache
        if self.insights_cache and self.cache_time:
            if (datetime.now() - self.cache_time).total_seconds() < self.cache_ttl:
                return self.insights_cache

        trades = self._get_closed_trades(hours)

        if len(trades) < self.min_trades:
            return ""  # Not enough data

        lines = []

        # Include user notes first (important context from human)
        active_notes = self.get_active_notes()
        if active_notes:
            logger.info(f"📝 Including {len(active_notes)} user note(s) in LLM context")
            for note in active_notes:
                logger.info(f"   → {note.get('message', '')[:80]}...")
            lines.append("=" * 60)
            lines.append("USER NOTES (from human operator)")
            lines.append("=" * 60)
            for note in active_notes:
                ts = note.get('timestamp', '')[:16].replace('T', ' ')
                lines.append(f"[{ts}] {note.get('message', '')}")
            lines.append("")

        lines.append("=" * 60)
        lines.append("SELF-LEARNING INSIGHTS (from your past trades)")
        lines.append("=" * 60)

        # Overall stats
        total_pnl = sum((t.get('pnl') or 0) for t in trades)
        wins = len([t for t in trades if (t.get('pnl') or 0) > 0])
        total = len(trades)
        win_rate = wins / total if total > 0 else 0

        lines.append(f"\nOVERALL ({total} trades, last 7 days):")
        lines.append(f"  Win Rate: {win_rate:.1%} | Total P/L: ${total_pnl:.2f}")

        # Side performance
        side_perf = self.analyze_side_performance(hours)
        if side_perf:
            lines.append("\nLONG vs SHORT:")
            for side, stats in side_perf.items():
                if stats['total'] >= 2:
                    lines.append(f"  {side}: {stats['win_rate']:.1%} WR ({stats['total']} trades, ${stats['total_pnl']:.2f})")

        # Best symbols
        best = self.get_best_symbols(hours)
        if best:
            lines.append("\nBEST PERFORMING SYMBOLS (favor these):")
            for symbol, wr in best[:5]:
                lines.append(f"  {symbol}: {wr:.1%} win rate")

        # Worst symbols
        worst = self.get_worst_symbols(hours)
        if worst:
            lines.append("\nWORST PERFORMING SYMBOLS (avoid or reduce size):")
            for symbol, wr in worst[:5]:
                lines.append(f"  {symbol}: {wr:.1%} win rate")

        # Confidence calibration
        conf_cal = self.analyze_confidence_calibration(hours)
        calibration_issues = []
        for bucket, stats in conf_cal.items():
            if stats['total'] >= 3:
                # Check if high confidence trades are actually winning
                if 'high' in bucket and stats['win_rate'] < 0.5:
                    calibration_issues.append(f"  WARNING: {bucket} confidence only {stats['win_rate']:.0%} accurate")
                elif 'low' in bucket and stats['win_rate'] > 0.6:
                    calibration_issues.append(f"  NOTE: Low confidence trades doing well ({stats['win_rate']:.0%})")

        if calibration_issues:
            lines.append("\nCONFIDENCE CALIBRATION:")
            lines.extend(calibration_issues)

        # Recent streak
        recent = sorted(trades, key=lambda t: t.get('exit_timestamp', ''), reverse=True)[:5]
        recent_wins = len([t for t in recent if (t.get('pnl') or 0) > 0])
        if recent_wins >= 4:
            lines.append("\nSTREAK: Hot streak! Last 5 trades mostly winners - maintain discipline")
        elif recent_wins <= 1:
            lines.append("\nSTREAK: Cold streak - consider reducing position sizes until edge returns")

        lines.append("\n" + "=" * 60)

        result = "\n".join(lines)

        # Cache result
        self.insights_cache = result
        self.cache_time = datetime.now()

        return result

    def get_symbol_recommendation(self, symbol: str, hours: int = 168) -> Optional[str]:
        """
        Get recommendation for a specific symbol based on past performance

        Returns:
            None if no data, or recommendation string
        """
        perf = self.analyze_symbol_performance(hours)

        if symbol not in perf:
            return None

        stats = perf[symbol]
        if stats['total'] < 2:
            return None

        if stats['win_rate'] >= 0.6:
            return f"FAVORABLE: {symbol} has {stats['win_rate']:.0%} win rate ({stats['total']} trades)"
        elif stats['win_rate'] < 0.35:
            return f"AVOID: {symbol} has only {stats['win_rate']:.0%} win rate ({stats['total']} trades)"
        else:
            return None
