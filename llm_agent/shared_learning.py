"""
Shared Learning Module
Cross-bot insights sharing between Hibachi and Extended bots

Features:
- Shared blocked combos (symbol + direction)
- Trading blackout windows
- Sentiment context synchronization
- Active position awareness (avoid conflicts)
- Confidence calibration data
- Win rate tracking by symbol/direction
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)

# Shared insights file location
SHARED_INSIGHTS_FILE = "logs/shared_insights.json"


class SharedLearning:
    """
    Cross-bot learning and insights sharing layer

    Both Hibachi and Extended bots read/write to shared state,
    allowing them to learn from each other's successes and failures.
    """

    def __init__(self, bot_name: str):
        """
        Args:
            bot_name: Identifier for this bot ('hibachi' or 'extended')
        """
        self.bot_name = bot_name
        self._cache: Optional[Dict] = None
        self._last_load: Optional[datetime] = None

        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)

        # Initialize file if not exists
        if not os.path.exists(SHARED_INSIGHTS_FILE):
            self._initialize_file()

    def _initialize_file(self):
        """Create initial shared insights file"""
        initial_data = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "blocked_combos": [],
            "reduced_combos": [],
            "blackout_windows_utc": [],
            "sentiment": {
                "fear_greed_combined": 50,
                "market_bias": "neutral",
                "updated": None
            },
            "active_positions": {
                "hibachi": [],
                "extended": []
            },
            "confidence_calibration": {
                "llm_0.6_actual": None,
                "llm_0.7_actual": None,
                "llm_0.8_actual": None,
                "llm_0.9_actual": None
            },
            "symbol_performance": {},
            "recent_trades": {
                "hibachi": [],
                "extended": []
            },
            "cross_bot_recommendations": [],
            "notes": []
        }
        self._save(initial_data)
        logger.info(f"Initialized shared insights file: {SHARED_INSIGHTS_FILE}")

    def _load(self, force_refresh: bool = False) -> Dict:
        """Load shared insights from file"""
        # Use cache if recent (within 5 seconds)
        if not force_refresh and self._cache and self._last_load:
            if datetime.now() - self._last_load < timedelta(seconds=5):
                return self._cache

        try:
            with open(SHARED_INSIGHTS_FILE, 'r') as f:
                data = json.load(f)
                self._cache = data
                self._last_load = datetime.now()
                return data
        except Exception as e:
            logger.error(f"Error loading shared insights: {e}")
            self._initialize_file()
            return self._load()

    def _save(self, data: Dict):
        """Save shared insights to file"""
        try:
            data['last_updated'] = datetime.now().isoformat()
            with open(SHARED_INSIGHTS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            self._cache = data
            self._last_load = datetime.now()
        except Exception as e:
            logger.error(f"Error saving shared insights: {e}")

    # =========== BLOCKED/REDUCED COMBOS ===========

    def is_blocked(self, symbol: str, direction: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a symbol+direction combo is blocked

        Args:
            symbol: Trading symbol (e.g., 'SOL', 'ETH')
            direction: 'LONG' or 'SHORT'

        Returns:
            Tuple of (is_blocked, reason)
        """
        data = self._load()
        combo_key = f"{symbol}_{direction}".upper()

        for blocked in data.get('blocked_combos', []):
            if blocked.get('combo') == combo_key:
                # Check expiry
                expires = blocked.get('expires')
                if expires:
                    if datetime.fromisoformat(expires) < datetime.now():
                        continue  # Expired, skip
                reason = f"Blocked: {blocked.get('win_rate', 0)*100:.0f}% WR over {blocked.get('sample_size', 0)} trades"
                return True, reason

        return False, None

    def get_size_multiplier(self, symbol: str, direction: str) -> Tuple[float, Optional[str]]:
        """
        Get position size multiplier for a combo (for reduced combos)

        Returns:
            Tuple of (multiplier, reason) - 1.0 means normal, 0.5 means reduce by half
        """
        data = self._load()
        combo_key = f"{symbol}_{direction}".upper()

        for reduced in data.get('reduced_combos', []):
            if reduced.get('combo') == combo_key:
                expires = reduced.get('expires')
                if expires and datetime.fromisoformat(expires) < datetime.now():
                    continue
                mult = reduced.get('multiplier', 0.5)
                reason = f"Reduced {(1-mult)*100:.0f}%: {reduced.get('win_rate', 0)*100:.0f}% WR"
                return mult, reason

        return 1.0, None

    def add_blocked_combo(self, symbol: str, direction: str, win_rate: float,
                          sample_size: int, expires_hours: int = 48, source_bot: str = None):
        """Add a blocked combo (win rate < 30%)"""
        data = self._load()
        combo_key = f"{symbol}_{direction}".upper()

        # Remove existing entry for this combo
        data['blocked_combos'] = [b for b in data.get('blocked_combos', [])
                                   if b.get('combo') != combo_key]

        data['blocked_combos'].append({
            'combo': combo_key,
            'win_rate': win_rate,
            'sample_size': sample_size,
            'expires': (datetime.now() + timedelta(hours=expires_hours)).isoformat(),
            'added_by': source_bot or self.bot_name,
            'added_at': datetime.now().isoformat()
        })

        self._save(data)
        logger.info(f"[SHARED] Blocked {combo_key} (WR: {win_rate*100:.0f}%, n={sample_size})")

    def add_reduced_combo(self, symbol: str, direction: str, win_rate: float,
                          sample_size: int, multiplier: float = 0.5,
                          expires_hours: int = 48, source_bot: str = None):
        """Add a reduced-size combo (win rate 30-40%)"""
        data = self._load()
        combo_key = f"{symbol}_{direction}".upper()

        data['reduced_combos'] = [r for r in data.get('reduced_combos', [])
                                   if r.get('combo') != combo_key]

        data['reduced_combos'].append({
            'combo': combo_key,
            'win_rate': win_rate,
            'sample_size': sample_size,
            'multiplier': multiplier,
            'expires': (datetime.now() + timedelta(hours=expires_hours)).isoformat(),
            'added_by': source_bot or self.bot_name,
            'added_at': datetime.now().isoformat()
        })

        self._save(data)
        logger.info(f"[SHARED] Reduced {combo_key} to {multiplier*100:.0f}% size (WR: {win_rate*100:.0f}%)")

    # =========== BLACKOUT WINDOWS ===========

    def is_in_blackout(self) -> Tuple[bool, Optional[str]]:
        """Check if current time is in a blackout window"""
        data = self._load()
        now = datetime.utcnow()
        current_time = now.strftime("%H:%M")

        for window in data.get('blackout_windows_utc', []):
            start = window.get('start', '00:00')
            end = window.get('end', '00:00')

            if start <= current_time <= end:
                return True, window.get('reason', 'Blackout window')

        return False, None

    def add_blackout_window(self, start_utc: str, end_utc: str, reason: str):
        """Add a trading blackout window (UTC times as HH:MM)"""
        data = self._load()

        # Check for duplicates
        for window in data.get('blackout_windows_utc', []):
            if window.get('start') == start_utc and window.get('end') == end_utc:
                return  # Already exists

        data['blackout_windows_utc'].append({
            'start': start_utc,
            'end': end_utc,
            'reason': reason,
            'added_by': self.bot_name,
            'added_at': datetime.now().isoformat()
        })

        self._save(data)
        logger.info(f"[SHARED] Added blackout window {start_utc}-{end_utc} UTC: {reason}")

    # =========== ACTIVE POSITIONS ===========

    def update_active_positions(self, positions: List[Dict]):
        """
        Update this bot's active positions in shared state

        Args:
            positions: List of {'symbol': str, 'direction': str, 'entry_time': str, 'size_usd': float}
        """
        data = self._load()
        data['active_positions'][self.bot_name] = positions
        self._save(data)

    def register_position(self, symbol: str, direction: str, bot_name: Optional[str] = None):
        """
        Register a single position for this bot (convenience method)

        Args:
            symbol: Trading symbol (e.g., 'BTC')
            direction: 'LONG' or 'SHORT'
            bot_name: Optional override for bot name (default: self.bot_name)
        """
        effective_bot = bot_name or self.bot_name
        data = self._load()

        # Ensure active_positions exists for this bot
        if effective_bot not in data.get('active_positions', {}):
            data['active_positions'][effective_bot] = []

        # Add position if not already present
        existing = data['active_positions'][effective_bot]
        already_exists = any(
            p.get('symbol', '').upper() == symbol.upper() and
            p.get('direction', '').upper() == direction.upper()
            for p in existing
        )

        if not already_exists:
            existing.append({
                'symbol': symbol.upper(),
                'direction': direction.upper(),
                'entry_time': datetime.now().isoformat(),
                'size_usd': 10.0  # Default size
            })
            data['active_positions'][effective_bot] = existing
            self._save(data)

    def unregister_position(self, symbol: str, bot_name: Optional[str] = None):
        """
        Unregister a position when closed

        Args:
            symbol: Trading symbol to remove
            bot_name: Optional override for bot name
        """
        effective_bot = bot_name or self.bot_name
        data = self._load()

        if effective_bot in data.get('active_positions', {}):
            positions = data['active_positions'][effective_bot]
            data['active_positions'][effective_bot] = [
                p for p in positions
                if p.get('symbol', '').upper() != symbol.upper()
            ]
            self._save(data)

    def get_other_bot_positions(self) -> List[Dict]:
        """Get positions from the other bot (to avoid conflicts)"""
        data = self._load()
        other_bot = 'extended' if self.bot_name == 'hibachi' else 'hibachi'
        return data.get('active_positions', {}).get(other_bot, [])

    def check_position_conflict(self, symbol: str, direction: str) -> Tuple[bool, Optional[str]]:
        """
        Check if entering this position would conflict with other bot

        Conflict = other bot has opposite direction on same symbol
        """
        other_positions = self.get_other_bot_positions()

        for pos in other_positions:
            if pos.get('symbol', '').upper() == symbol.upper():
                other_dir = pos.get('direction', '').upper()
                if other_dir and other_dir != direction.upper():
                    return True, f"Conflict: {self.bot_name} wants {direction} but other bot is {other_dir}"

        return False, None

    # =========== SENTIMENT ===========

    def update_sentiment(self, sentiment_data: Dict):
        """Update shared sentiment data from sentiment_fetcher"""
        data = self._load()
        data['sentiment'] = {
            'fear_greed_combined': sentiment_data.get('combined_score', 50),
            'market_bias': sentiment_data.get('market_bias', {}).get('direction', 'neutral'),
            'contrarian_signal': sentiment_data.get('market_bias', {}).get('contrarian_signal', 'neutral'),
            'recommendation': sentiment_data.get('market_bias', {}).get('recommendation', ''),
            'updated': datetime.now().isoformat()
        }
        self._save(data)

    def get_sentiment(self) -> Dict:
        """Get current sentiment data"""
        data = self._load()
        return data.get('sentiment', {})

    # =========== TRADE RECORDING ===========

    def record_trade(self, trade: Dict):
        """
        Record a completed trade for cross-bot learning

        Args:
            trade: Dict with symbol, direction, entry_price, exit_price, pnl, pnl_pct, confidence
        """
        data = self._load()

        # Add to recent trades (keep last 50 per bot)
        recent = data.get('recent_trades', {}).get(self.bot_name, [])
        trade['recorded_at'] = datetime.now().isoformat()
        trade['bot'] = self.bot_name
        recent.append(trade)
        recent = recent[-50:]  # Keep last 50

        if 'recent_trades' not in data:
            data['recent_trades'] = {}
        data['recent_trades'][self.bot_name] = recent

        # Update symbol performance
        symbol = trade.get('symbol', 'UNKNOWN')
        direction = trade.get('direction', 'UNKNOWN')
        combo_key = f"{symbol}_{direction}".upper()

        if 'symbol_performance' not in data:
            data['symbol_performance'] = {}

        if combo_key not in data['symbol_performance']:
            data['symbol_performance'][combo_key] = {
                'wins': 0,
                'losses': 0,
                'total_pnl': 0.0
            }

        perf = data['symbol_performance'][combo_key]
        pnl = trade.get('pnl', 0)
        if pnl > 0:
            perf['wins'] += 1
        else:
            perf['losses'] += 1
        perf['total_pnl'] += pnl

        # Auto-block if win rate drops below 30% with enough samples
        total = perf['wins'] + perf['losses']
        if total >= 10:
            win_rate = perf['wins'] / total
            if win_rate < 0.30:
                self.add_blocked_combo(symbol, direction, win_rate, total)
            elif win_rate < 0.40:
                self.add_reduced_combo(symbol, direction, win_rate, total)

        self._save(data)

    # =========== CONFIDENCE CALIBRATION ===========

    def update_confidence_calibration(self, confidence_bucket: str, actual_win_rate: float):
        """
        Update confidence calibration data

        Args:
            confidence_bucket: e.g., 'llm_0.8_actual'
            actual_win_rate: The actual win rate for this confidence level
        """
        data = self._load()
        if 'confidence_calibration' not in data:
            data['confidence_calibration'] = {}
        data['confidence_calibration'][confidence_bucket] = actual_win_rate
        self._save(data)

    def get_adjusted_confidence(self, llm_confidence: float) -> float:
        """
        Get calibrated confidence based on historical accuracy

        If LLM says 0.8 but historical shows 0.44 actual, return 0.44
        """
        data = self._load()
        cal = data.get('confidence_calibration', {})

        # Find closest bucket
        if llm_confidence >= 0.85:
            actual = cal.get('llm_0.9_actual')
        elif llm_confidence >= 0.75:
            actual = cal.get('llm_0.8_actual')
        elif llm_confidence >= 0.65:
            actual = cal.get('llm_0.7_actual')
        else:
            actual = cal.get('llm_0.6_actual')

        return actual if actual else llm_confidence

    # =========== RECOMMENDATIONS ===========

    def add_recommendation(self, recommendation: str, expires_hours: int = 24):
        """Add a cross-bot recommendation (from Qwen analysis)"""
        data = self._load()

        data['cross_bot_recommendations'].append({
            'text': recommendation,
            'added_by': self.bot_name,
            'added_at': datetime.now().isoformat(),
            'expires': (datetime.now() + timedelta(hours=expires_hours)).isoformat()
        })

        # Keep only non-expired recommendations
        data['cross_bot_recommendations'] = [
            r for r in data['cross_bot_recommendations']
            if datetime.fromisoformat(r.get('expires', '2000-01-01')) > datetime.now()
        ]

        self._save(data)

    def get_recommendations(self) -> List[str]:
        """Get active cross-bot recommendations"""
        data = self._load()
        recs = data.get('cross_bot_recommendations', [])

        active = []
        for r in recs:
            expires = r.get('expires')
            if expires and datetime.fromisoformat(expires) > datetime.now():
                active.append(r.get('text', ''))

        return active

    # =========== PROMPT CONTEXT ===========

    def get_prompt_context(self) -> str:
        """Generate shared learning context for LLM prompts"""
        data = self._load()

        lines = ["CROSS-BOT LEARNING INSIGHTS:"]

        # Blocked combos
        blocked = data.get('blocked_combos', [])
        active_blocked = [b for b in blocked
                         if not b.get('expires') or
                         datetime.fromisoformat(b['expires']) > datetime.now()]
        if active_blocked:
            lines.append("BLOCKED (DO NOT TRADE):")
            for b in active_blocked[:5]:  # Show top 5
                lines.append(f"  - {b['combo']}: {b['win_rate']*100:.0f}% WR (n={b['sample_size']})")

        # Reduced combos
        reduced = data.get('reduced_combos', [])
        active_reduced = [r for r in reduced
                         if not r.get('expires') or
                         datetime.fromisoformat(r['expires']) > datetime.now()]
        if active_reduced:
            lines.append("HIGH RISK (reduce position size):")
            for r in active_reduced[:5]:
                lines.append(f"  - {r['combo']}: {r['win_rate']*100:.0f}% WR")

        # Sentiment
        sentiment = data.get('sentiment', {})
        if sentiment.get('updated'):
            lines.append(f"MARKET SENTIMENT: {sentiment.get('market_bias', 'neutral').upper()}")
            if sentiment.get('contrarian_signal') and sentiment['contrarian_signal'] != 'neutral':
                lines.append(f"  Contrarian Signal: {sentiment['contrarian_signal']}")
            if sentiment.get('recommendation'):
                lines.append(f"  {sentiment['recommendation']}")

        # Other bot positions
        other_positions = self.get_other_bot_positions()
        if other_positions:
            lines.append("OTHER BOT POSITIONS (avoid conflicts):")
            for pos in other_positions[:3]:
                lines.append(f"  - {pos.get('symbol')}: {pos.get('direction')}")

        # Active recommendations
        recs = self.get_recommendations()
        if recs:
            lines.append("CROSS-BOT RECOMMENDATIONS:")
            for rec in recs[:3]:
                lines.append(f"  - {rec}")

        return "\n".join(lines)


# =========== TESTING ===========

def main():
    """Test shared learning module"""
    logging.basicConfig(level=logging.INFO)

    # Simulate hibachi bot
    hibachi = SharedLearning('hibachi')

    # Test blocking
    hibachi.add_blocked_combo('SOL', 'SHORT', 0.25, 20)
    hibachi.add_reduced_combo('ETH', 'SHORT', 0.35, 15)

    # Check blocks
    blocked, reason = hibachi.is_blocked('SOL', 'SHORT')
    print(f"SOL SHORT blocked: {blocked} - {reason}")

    mult, reason = hibachi.get_size_multiplier('ETH', 'SHORT')
    print(f"ETH SHORT multiplier: {mult} - {reason}")

    # Record trades
    hibachi.record_trade({
        'symbol': 'BTC',
        'direction': 'LONG',
        'pnl': 5.23,
        'confidence': 0.75
    })

    # Update positions
    hibachi.update_active_positions([
        {'symbol': 'BTC', 'direction': 'LONG', 'entry_time': datetime.now().isoformat(), 'size_usd': 50}
    ])

    # Test extended bot
    extended = SharedLearning('extended')
    conflict, reason = extended.check_position_conflict('BTC', 'SHORT')
    print(f"BTC SHORT conflict: {conflict} - {reason}")

    # Get prompt context
    print("\n" + "=" * 60)
    print("PROMPT CONTEXT:")
    print("=" * 60)
    print(hibachi.get_prompt_context())


if __name__ == "__main__":
    main()
