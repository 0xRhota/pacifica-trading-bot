"""
Strategy D - Pairs Trade (for Extended)
Volume generation while staying flat.

PHILOSOPHY:
Open opposing positions on correlated assets (ETH vs BTC).
Hold for 1 hour, close both. Correlation means ~50% win rate = near break-even.
Goal: Generate volume without bleeding money.

PAIRS TRADE MECHANICS:
1. Long ETH/USDT-P, Short BTC/USDT-P (equal $ amounts)
2. Hold for 1 hour
3. Close both positions
4. Log actual PnL from each trade
5. Repeat

NO LLM COSTS - pure mechanical strategy.
"""

import logging
import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# Dedicated log file for pairs strategy
PAIRS_LOG_FILE = "logs/strategy_d_pairs.log"


class StrategyDPairsTrade:
    """
    Pairs trade strategy - long one asset, short another.
    Designed for volume generation while staying near break-even.
    """

    STRATEGY_NAME = "STRATEGY_D_PAIRS_TRADE"

    # Default pair: Long ETH, Short BTC
    LONG_ASSET = "ETH/USDT-P"
    SHORT_ASSET = "BTC/USDT-P"

    # Hold time in seconds (1 hour)
    HOLD_TIME_SECONDS = 3600

    def __init__(
        self,
        position_size_usd: float = 100.0,
        hold_time_seconds: int = 3600,
        long_asset: str = "ETH/USDT-P",
        short_asset: str = "BTC/USDT-P",
        llm_agent = None  # LLM agent for dynamic direction selection
    ):
        """
        Initialize Pairs Trade Strategy

        Args:
            position_size_usd: Dollar amount per leg (total exposure = 2x this)
            hold_time_seconds: How long to hold before closing (default: 1 hour)
            long_asset: Asset to go long (default, can be swapped by LLM)
            short_asset: Asset to go short (default, can be swapped by LLM)
            llm_agent: LLM agent for analyzing which asset to long/short
        """
        self.position_size_usd = position_size_usd
        self.hold_time_seconds = hold_time_seconds
        self.ASSET_A = long_asset  # Default first asset
        self.ASSET_B = short_asset  # Default second asset
        self.llm_agent = llm_agent

        # Track active pairs trade
        self.active_trade = None  # Will store {open_time, long_entry, short_entry, ...}

        # Track cumulative stats
        self.stats = {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "total_pnl": 0.0,
            "total_volume": 0.0
        }

        # Ensure log directory exists
        Path("logs").mkdir(exist_ok=True)

        # Load existing stats if available
        self._load_stats()

        logger.info("=" * 60)
        logger.info("STRATEGY D: PAIRS TRADE (DYNAMIC)")
        logger.info(f"  Assets: {self.ASSET_A} vs {self.ASSET_B}")
        logger.info(f"  Direction: LLM selects based on relative strength")
        logger.info(f"  Size: ${self.position_size_usd} per leg")
        logger.info(f"  Hold: {self.hold_time_seconds}s ({self.hold_time_seconds/60:.0f} min)")
        logger.info(f"  Stats: {self.stats['total_trades']} trades, ${self.stats['total_pnl']:.2f} PnL")
        logger.info("=" * 60)

    def _load_stats(self):
        """Load stats from log file if exists"""
        try:
            if os.path.exists(PAIRS_LOG_FILE):
                with open(PAIRS_LOG_FILE, 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        if '"type": "stats"' in line:
                            data = json.loads(line.strip())
                            self.stats = data.get("stats", self.stats)
        except Exception as e:
            logger.warning(f"Could not load stats: {e}")

    def _log_trade(self, trade_data: Dict):
        """Log trade to dedicated pairs log file"""
        try:
            trade_data["timestamp"] = datetime.now().isoformat()
            with open(PAIRS_LOG_FILE, 'a') as f:
                f.write(json.dumps(trade_data) + "\n")
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")

    def _save_stats(self):
        """Save current stats to log"""
        self._log_trade({"type": "stats", "stats": self.stats})

    def sync_with_positions(self, our_positions: List[Dict]) -> Optional[str]:
        """
        Sync active_trade state with actual positions.
        Detects orphaned positions (one leg missing from pair).

        Args:
            our_positions: Current open positions

        Returns:
            Symbol of orphaned position if found, None otherwise
        """
        # Check for either asset in positions
        asset_a_pos = any(p.get('symbol') == self.ASSET_A for p in our_positions)
        asset_b_pos = any(p.get('symbol') == self.ASSET_B for p in our_positions)

        # Both legs present - we're good
        if asset_a_pos and asset_b_pos:
            if self.active_trade is None:
                # Positions exist but we're not tracking - restore tracking
                logger.warning(f"[PAIRS] Found both legs but no active_trade - syncing")
                self.active_trade = {
                    "open_time": datetime.now(),  # Best guess
                    "long_asset": self.ASSET_A,  # Can't know direction, assume A is long
                    "short_asset": self.ASSET_B,
                    "status": "active"
                }
            return None

        # Neither leg present - clear tracking
        if not asset_a_pos and not asset_b_pos:
            if self.active_trade is not None:
                logger.warning(f"[PAIRS] No positions but have active_trade - clearing")
                self.active_trade = None
            return None

        # One leg orphaned - need to close it
        if asset_a_pos:
            logger.warning(f"[PAIRS] ORPHANED: {self.ASSET_A} (other leg missing)")
            self.active_trade = None
            return self.ASSET_A
        if asset_b_pos:
            logger.warning(f"[PAIRS] ORPHANED: {self.ASSET_B} (other leg missing)")
            self.active_trade = None
            return self.ASSET_B

        return None

    async def should_open_pair(self, our_positions: List[Dict]) -> bool:
        """
        Check if we should open a new pairs trade

        Args:
            our_positions: Current open positions

        Returns:
            True if we should open a new pair
        """
        # Sync state with actual positions first
        orphan = self.sync_with_positions(our_positions)
        if orphan:
            logger.info(f"[PAIRS] Cannot open new pair - orphaned {orphan} needs cleanup")
            return False

        # Don't open if we already have an active trade
        if self.active_trade is not None:
            return False

        # Don't open if we have any positions in our target assets
        for pos in our_positions:
            symbol = pos.get('symbol', '')
            if symbol in [self.ASSET_A, self.ASSET_B]:
                logger.info(f"[PAIRS] Already have position in {symbol}, skipping")
                return False

        return True

    async def should_close_pair(self) -> bool:
        """
        Check if we should close the current pairs trade

        Returns:
            True if hold time has elapsed
        """
        if self.active_trade is None:
            return False

        open_time = self.active_trade.get("open_time")
        if not open_time:
            return False

        elapsed = (datetime.now() - open_time).total_seconds()
        return elapsed >= self.hold_time_seconds

    def get_time_remaining(self) -> Optional[int]:
        """Get seconds remaining until close"""
        if self.active_trade is None:
            return None

        open_time = self.active_trade.get("open_time")
        if not open_time:
            return None

        elapsed = (datetime.now() - open_time).total_seconds()
        remaining = self.hold_time_seconds - elapsed
        return max(0, int(remaining))

    async def _ask_llm_direction(self, market_data_dict: Dict) -> Tuple[str, str, str]:
        """
        Ask LLM which asset is more likely to go UP

        Args:
            market_data_dict: Market data for both assets

        Returns:
            (long_symbol, short_symbol, reasoning)
        """
        if not self.llm_agent:
            # No LLM - default to Long ASSET_A, Short ASSET_B
            return (self.ASSET_A, self.ASSET_B, "No LLM - using default direction")

        # Build simple comparison prompt
        asset_a_data = market_data_dict.get(self.ASSET_A, {})
        asset_b_data = market_data_dict.get(self.ASSET_B, {})

        prompt = f"""You are comparing TWO assets for a pairs trade. You will LONG the stronger one and SHORT the weaker one.

ASSET A: {self.ASSET_A}
  Price: ${asset_a_data.get('price', 0):.2f}
  RSI: {asset_a_data.get('rsi', 0):.1f}
  MACD: {asset_a_data.get('macd', 0):.4f}
  24h Change: {asset_a_data.get('price_change_24h', 0):.2f}%
  Volume: ${asset_a_data.get('volume_24h', 0):,.0f}

ASSET B: {self.ASSET_B}
  Price: ${asset_b_data.get('price', 0):.2f}
  RSI: {asset_b_data.get('rsi', 0):.1f}
  MACD: {asset_b_data.get('macd', 0):.4f}
  24h Change: {asset_b_data.get('price_change_24h', 0):.2f}%
  Volume: ${asset_b_data.get('volume_24h', 0):,.0f}

Which asset is MORE LIKELY TO GO UP in the next 1 hour?

Respond ONLY with:
LONG: <symbol>
SHORT: <symbol>
REASON: <one sentence why>

Example:
LONG: ETH/USDT-P
SHORT: BTC/USDT-P
REASON: ETH showing stronger RSI recovery and positive MACD divergence
"""

        try:
            # Call LLM (query is sync, not async)
            result = self.llm_agent.model_client.query(prompt)
            if not result or not result.get('content'):
                logger.warning("[PAIRS-LLM] Empty response from LLM")
                return (self.ASSET_A, self.ASSET_B, "LLM empty response - using default")
            text = result['content'].strip()

            # Parse response
            long_symbol = None
            short_symbol = None
            reason = "LLM analysis"

            for line in text.split('\n'):
                if line.startswith('LONG:'):
                    long_symbol = line.replace('LONG:', '').strip()
                elif line.startswith('SHORT:'):
                    short_symbol = line.replace('SHORT:', '').strip()
                elif line.startswith('REASON:'):
                    reason = line.replace('REASON:', '').strip()

            # Validate response
            if long_symbol in [self.ASSET_A, self.ASSET_B] and short_symbol in [self.ASSET_A, self.ASSET_B]:
                if long_symbol != short_symbol:
                    logger.info(f"[PAIRS-LLM] {long_symbol} > {short_symbol}: {reason}")
                    return (long_symbol, short_symbol, reason)

            # Fallback if LLM response invalid
            logger.warning(f"[PAIRS-LLM] Invalid response: {text[:100]}")
            return (self.ASSET_A, self.ASSET_B, "LLM failed - using default")

        except Exception as e:
            logger.error(f"[PAIRS-LLM] Error: {e}")
            return (self.ASSET_A, self.ASSET_B, f"LLM error - using default")

    async def get_open_decisions(self, account_balance: float, market_data_dict: Dict = None) -> List[Dict]:
        """
        Get decisions to open a new pairs trade

        Args:
            account_balance: Current account balance
            market_data_dict: Market data for LLM analysis (optional)

        Returns:
            List of decisions (LONG + SHORT)
        """
        # Calculate position size (use smaller of configured or 40% of balance per leg)
        size_per_leg = min(self.position_size_usd, account_balance * 0.4)

        # Ask LLM which asset to long/short
        long_symbol, short_symbol, reasoning = await self._ask_llm_direction(market_data_dict or {})

        logger.info("")
        logger.info("=" * 60)
        logger.info("PAIRS TRADE: OPENING NEW PAIR")
        logger.info(f"  Long: {long_symbol} (${size_per_leg:.2f})")
        logger.info(f"  Short: {short_symbol} (${size_per_leg:.2f})")
        logger.info(f"  Total exposure: ${size_per_leg * 2:.2f}")
        logger.info(f"  Reasoning: {reasoning}")
        logger.info("=" * 60)
        logger.info("")

        # Track that we're opening
        self.active_trade = {
            "open_time": datetime.now(),
            "long_asset": long_symbol,
            "short_asset": short_symbol,
            "size_per_leg": size_per_leg,
            "long_entry_price": None,  # Will be filled after execution
            "short_entry_price": None,
            "status": "opening",
            "llm_reasoning": reasoning
        }

        return [
            {
                "action": "LONG",
                "symbol": long_symbol,
                "reasoning": f"PAIRS TRADE: {reasoning}",
                "confidence": 0.8,  # Above 0.7 fee filter threshold
                "position_size_usd": size_per_leg
            },
            {
                "action": "SHORT",
                "symbol": short_symbol,
                "reasoning": f"PAIRS TRADE: Opposite leg to {long_symbol}",
                "confidence": 0.8,  # Above 0.7 fee filter threshold
                "position_size_usd": size_per_leg
            }
        ]

    async def get_close_decisions(self) -> List[Dict]:
        """
        Get decisions to close the current pairs trade

        Returns:
            List of CLOSE decisions
        """
        if self.active_trade is None:
            return []

        elapsed_min = (datetime.now() - self.active_trade["open_time"]).total_seconds() / 60

        logger.info("")
        logger.info("=" * 60)
        logger.info("PAIRS TRADE: CLOSING PAIR")
        logger.info(f"  Held for: {elapsed_min:.1f} minutes")
        logger.info(f"  Closing: {self.active_trade['long_asset']} (long)")
        logger.info(f"  Closing: {self.active_trade['short_asset']} (short)")
        logger.info("=" * 60)
        logger.info("")

        return [
            {
                "action": "CLOSE",
                "symbol": self.active_trade["long_asset"],
                "reasoning": f"PAIRS TRADE: Closing long leg after {elapsed_min:.0f}min hold"
            },
            {
                "action": "CLOSE",
                "symbol": self.active_trade["short_asset"],
                "reasoning": f"PAIRS TRADE: Closing short leg after {elapsed_min:.0f}min hold"
            }
        ]

    def record_entry(self, symbol: str, price: float, size: float):
        """Record entry price after execution"""
        if self.active_trade is None:
            return

        if symbol == self.active_trade.get("long_asset"):
            self.active_trade["long_entry_price"] = price
            self.active_trade["long_size"] = size
            logger.info(f"[PAIRS] Recorded long entry: {symbol} @ ${price:.2f}")
        elif symbol == self.active_trade.get("short_asset"):
            self.active_trade["short_entry_price"] = price
            self.active_trade["short_size"] = size
            logger.info(f"[PAIRS] Recorded short entry: {symbol} @ ${price:.2f}")

        # Check if both legs are filled
        if (self.active_trade.get("long_entry_price") and
            self.active_trade.get("short_entry_price")):
            self.active_trade["status"] = "open"
            logger.info("[PAIRS] Both legs filled - pair is now OPEN")

    def record_exit(self, symbol: str, price: float, pnl: float):
        """Record exit and calculate PnL"""
        if self.active_trade is None:
            return

        if symbol == self.active_trade.get("long_asset"):
            self.active_trade["long_exit_price"] = price
            self.active_trade["long_pnl"] = pnl
            logger.info(f"[PAIRS] Recorded long exit: {symbol} @ ${price:.2f}, PnL: ${pnl:.2f}")
        elif symbol == self.active_trade.get("short_asset"):
            self.active_trade["short_exit_price"] = price
            self.active_trade["short_pnl"] = pnl
            logger.info(f"[PAIRS] Recorded short exit: {symbol} @ ${price:.2f}, PnL: ${pnl:.2f}")

        # Check if both legs are closed
        if (self.active_trade.get("long_exit_price") and
            self.active_trade.get("short_exit_price")):
            self._finalize_trade()

    def _finalize_trade(self):
        """Calculate final PnL and log completed trade"""
        if self.active_trade is None:
            return

        long_pnl = self.active_trade.get("long_pnl", 0)
        short_pnl = self.active_trade.get("short_pnl", 0)
        total_pnl = long_pnl + short_pnl

        hold_time = (datetime.now() - self.active_trade["open_time"]).total_seconds()
        volume = self.active_trade.get("size_per_leg", 0) * 2

        # Update stats
        self.stats["total_trades"] += 1
        self.stats["total_pnl"] += total_pnl
        self.stats["total_volume"] += volume
        if total_pnl > 0:
            self.stats["wins"] += 1
        else:
            self.stats["losses"] += 1

        win_rate = (self.stats["wins"] / self.stats["total_trades"] * 100) if self.stats["total_trades"] > 0 else 0

        # Log completed trade
        trade_log = {
            "type": "trade",
            "long_asset": self.active_trade["long_asset"],
            "short_asset": self.active_trade["short_asset"],
            "long_entry": self.active_trade.get("long_entry_price"),
            "long_exit": self.active_trade.get("long_exit_price"),
            "short_entry": self.active_trade.get("short_entry_price"),
            "short_exit": self.active_trade.get("short_exit_price"),
            "long_pnl": long_pnl,
            "short_pnl": short_pnl,
            "total_pnl": total_pnl,
            "hold_time_seconds": hold_time,
            "volume": volume
        }
        self._log_trade(trade_log)
        self._save_stats()

        logger.info("")
        logger.info("=" * 60)
        logger.info("PAIRS TRADE COMPLETE")
        logger.info(f"  Long PnL:  ${long_pnl:+.2f}")
        logger.info(f"  Short PnL: ${short_pnl:+.2f}")
        logger.info(f"  NET PnL:   ${total_pnl:+.2f}")
        logger.info(f"  Hold time: {hold_time/60:.1f} min")
        logger.info("-" * 60)
        logger.info(f"  CUMULATIVE: {self.stats['total_trades']} trades, ${self.stats['total_pnl']:+.2f} PnL")
        logger.info(f"  Win rate: {win_rate:.1f}% | Volume: ${self.stats['total_volume']:,.0f}")
        logger.info("=" * 60)
        logger.info("")

        # Clear active trade
        self.active_trade = None

    def get_status(self) -> Dict:
        """Get current strategy status"""
        status = {
            "strategy": self.STRATEGY_NAME,
            "long_asset": self.LONG_ASSET,
            "short_asset": self.SHORT_ASSET,
            "position_size": self.position_size_usd,
            "hold_time": self.hold_time_seconds,
            "stats": self.stats.copy(),
            "active_trade": None
        }

        if self.active_trade:
            remaining = self.get_time_remaining()
            status["active_trade"] = {
                "status": self.active_trade.get("status"),
                "time_remaining_seconds": remaining,
                "time_remaining_min": remaining / 60 if remaining else None
            }

        return status
