"""
Strategy C - Smart Whale Copy (for Extended)
Whale: 0x335f45392f8d87745aaae68f5c192849afd9b60e (BTC Scalper)

PHILOSOPHY:
Track whale's position CHANGES, not just current positions.
Copy new entries and exits intelligently.

WHALE PROFILE (as of 2025-12-04):
- Account: $2M
- Trade frequency: ~1.5 min avg gap (~35 trades/hr)
- Win rate: 48.4% (profitable despite <50% WR = good risk management)
- PnL: +$1,726 (last 200 fills)
- Focus: BTC ONLY (100% of trades)
- Style: High-frequency BTC scalper

SMART RULES:
1. Don't open if we already have a position in that asset
2. Copy CLOSE signals (if whale closes, we close)
3. Copy direction changes (if whale flips long->short, we flip)
4. Skip if we just closed that asset recently (2h cooldown)
5. Simple proportional sizing based on our account

NO LLM COSTS - pure rule-based copy trading.
"""

import logging
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class StrategyCSmartCopy:
    """
    Smart whale copy trading - tracks position changes, not just snapshots.

    Copies entries AND exits intelligently.
    """

    STRATEGY_NAME = "STRATEGY_C_SMART_COPY"

    # Whale configuration - BTC Scalper (switched 2025-12-04)
    # Previous: 0x023a3d058020fb76cca98f01b3c48c8938a22355 (Multi-Asset, position holder)
    # Current: High-frequency BTC scalper, ~35 trades/hr, 48.4% WR, profitable
    WHALE_ADDRESS = "0x335f45392f8d87745aaae68f5c192849afd9b60e"
    WHALE_NAME = "BTC Scalper (0x335f)"
    HYPERLIQUID_API = "https://api.hyperliquid.xyz/info"

    # Assets to copy - BTC ONLY (whale trades 100% BTC)
    COPY_ASSETS = ["BTC"]

    # Map to Extended symbols
    SYMBOL_MAP = {
        "BTC": "BTC-USD",
        "ETH": "ETH-USD",
        "SOL": "SOL-USD"
    }

    def __init__(self):
        """Initialize Smart Copy Strategy"""
        # Track whale's last known positions for change detection
        self.last_whale_positions = {}  # coin -> {side, size, entry_price}
        self.last_fetch_time = None

        # Track recent closes to avoid re-entry too fast
        self.recent_closes = {}  # symbol -> close_time
        self.close_cooldown_hours = 2

        logger.info("=" * 60)
        logger.info(f"STRATEGY C: SMART WHALE COPY")
        logger.info(f"  Whale: {self.WHALE_NAME}")
        logger.info(f"  Address: {self.WHALE_ADDRESS}")
        logger.info(f"  Assets: {', '.join(self.COPY_ASSETS)}")
        logger.info(f"  Logic: Copy entries + exits, no position stacking")
        logger.info("=" * 60)

    def _fetch_whale_positions(self) -> Dict[str, Dict]:
        """
        Fetch whale's current positions from Hyperliquid API

        Returns:
            Dict mapping coin -> position info
        """
        try:
            payload = {
                "type": "clearinghouseState",
                "user": self.WHALE_ADDRESS
            }

            response = requests.post(
                self.HYPERLIQUID_API,
                json=payload,
                timeout=10
            )

            if response.status_code != 200:
                logger.error(f"[SMART-COPY] Hyperliquid API error: {response.status_code}")
                return {}

            data = response.json()
            margin = data.get('marginSummary', {})
            positions = data.get('assetPositions', [])

            whale_account_value = float(margin.get('accountValue', 0))

            whale_positions = {}
            for p in positions:
                pos = p.get('position', {})
                coin = pos.get('coin', '')

                if coin in self.COPY_ASSETS:
                    size = float(pos.get('szi', 0))
                    entry_price = float(pos.get('entryPx', 0))

                    if size != 0:
                        side = 'LONG' if size > 0 else 'SHORT'
                        notional = abs(size * entry_price)

                        whale_positions[coin] = {
                            'side': side,
                            'size': abs(size),
                            'entry_price': entry_price,
                            'notional': notional
                        }
                    else:
                        # Whale is flat on this coin
                        whale_positions[coin] = {
                            'side': 'FLAT',
                            'size': 0,
                            'entry_price': 0,
                            'notional': 0
                        }

            # Fill in FLAT for any asset not in response
            for coin in self.COPY_ASSETS:
                if coin not in whale_positions:
                    whale_positions[coin] = {
                        'side': 'FLAT',
                        'size': 0,
                        'entry_price': 0,
                        'notional': 0
                    }

            self.last_fetch_time = datetime.now()
            return whale_positions

        except Exception as e:
            logger.error(f"[SMART-COPY] Error fetching whale positions: {e}")
            return {}

    def _detect_changes(self, current_positions: Dict[str, Dict]) -> List[Dict]:
        """
        Compare current whale positions to last known and detect changes.

        Returns:
            List of detected changes (new entry, close, flip)
        """
        changes = []

        for coin in self.COPY_ASSETS:
            current = current_positions.get(coin, {'side': 'FLAT', 'size': 0})
            last = self.last_whale_positions.get(coin, {'side': 'FLAT', 'size': 0})

            current_side = current['side']
            last_side = last['side']

            symbol = self.SYMBOL_MAP[coin]

            # Case 1: Was flat, now has position -> NEW ENTRY
            if last_side == 'FLAT' and current_side != 'FLAT':
                changes.append({
                    'type': 'NEW_ENTRY',
                    'coin': coin,
                    'symbol': symbol,
                    'side': current_side,
                    'reason': f"Whale opened {current_side} {coin}"
                })
                logger.info(f"[SMART-COPY] Detected: Whale opened {current_side} {coin}")

            # Case 2: Had position, now flat -> CLOSE
            elif last_side != 'FLAT' and current_side == 'FLAT':
                changes.append({
                    'type': 'CLOSE',
                    'coin': coin,
                    'symbol': symbol,
                    'side': None,
                    'reason': f"Whale closed {last_side} {coin}"
                })
                logger.info(f"[SMART-COPY] Detected: Whale closed {last_side} {coin}")

            # Case 3: Had position, now opposite -> FLIP
            elif last_side != 'FLAT' and current_side != 'FLAT' and last_side != current_side:
                changes.append({
                    'type': 'FLIP',
                    'coin': coin,
                    'symbol': symbol,
                    'side': current_side,
                    'reason': f"Whale flipped {last_side} -> {current_side} {coin}"
                })
                logger.info(f"[SMART-COPY] Detected: Whale flipped {last_side} -> {current_side} {coin}")

            # Case 4: Same direction but size changed significantly (>50%)
            elif last_side == current_side and last_side != 'FLAT':
                size_change = abs(current['size'] - last['size']) / max(last['size'], 0.0001)
                if size_change > 0.5:  # 50% size change
                    if current['size'] > last['size']:
                        changes.append({
                            'type': 'ADD',
                            'coin': coin,
                            'symbol': symbol,
                            'side': current_side,
                            'reason': f"Whale added to {current_side} {coin} (+{size_change*100:.0f}%)"
                        })
                        logger.info(f"[SMART-COPY] Detected: Whale added to {current_side} {coin}")
                    else:
                        changes.append({
                            'type': 'REDUCE',
                            'coin': coin,
                            'symbol': symbol,
                            'side': current_side,
                            'reason': f"Whale reduced {current_side} {coin} (-{size_change*100:.0f}%)"
                        })
                        logger.info(f"[SMART-COPY] Detected: Whale reduced {current_side} {coin}")

        return changes

    def _is_on_cooldown(self, symbol: str) -> bool:
        """Check if symbol was recently closed and on cooldown"""
        if symbol not in self.recent_closes:
            return False

        close_time = self.recent_closes[symbol]
        cooldown_end = close_time + timedelta(hours=self.close_cooldown_hours)

        if datetime.now() < cooldown_end:
            remaining = (cooldown_end - datetime.now()).total_seconds() / 60
            logger.info(f"[SMART-COPY] {symbol} on cooldown ({remaining:.0f}m remaining)")
            return True

        return False

    def _record_close(self, symbol: str):
        """Record a close for cooldown tracking"""
        self.recent_closes[symbol] = datetime.now()

    async def get_copy_decisions(
        self,
        our_positions: List[Dict],
        account_balance: float
    ) -> List[Dict]:
        """
        Main entry point: Get copy decisions based on whale position changes.

        Args:
            our_positions: Our current open positions
            account_balance: Our account balance in USD

        Returns:
            List of trade decisions (in format ready for executor)
        """
        # Fetch current whale positions
        current_whale = self._fetch_whale_positions()

        if not current_whale:
            logger.warning("[SMART-COPY] Could not fetch whale positions - skipping")
            return []

        # Log whale status
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"[SMART-COPY] WHALE STATUS")
        logger.info("=" * 60)
        for coin in self.COPY_ASSETS:
            pos = current_whale.get(coin, {'side': 'FLAT'})
            if pos['side'] != 'FLAT':
                logger.info(f"  {coin}: {pos['side']} ${pos['notional']:,.0f}")
            else:
                logger.info(f"  {coin}: FLAT")
        logger.info("=" * 60)

        # First run - just store positions, no trades
        if not self.last_whale_positions:
            logger.info("[SMART-COPY] First run - storing baseline, no trades")
            self.last_whale_positions = current_whale
            return []

        # Detect changes since last check
        changes = self._detect_changes(current_whale)

        if not changes:
            logger.info("[SMART-COPY] No whale position changes detected")
            self.last_whale_positions = current_whale
            return []

        logger.info(f"[SMART-COPY] Detected {len(changes)} whale changes")

        # Build our position map
        our_position_map = {}
        for pos in our_positions:
            symbol = pos.get('symbol', '')
            if symbol:
                our_position_map[symbol] = pos

        # Generate decisions
        decisions = []

        for change in changes:
            change_type = change['type']
            symbol = change['symbol']
            side = change['side']
            reason = change['reason']

            # Check cooldown
            if change_type in ['NEW_ENTRY', 'ADD'] and self._is_on_cooldown(symbol):
                logger.info(f"[SMART-COPY] Skipping {symbol} - on cooldown")
                continue

            # Check if we already have position
            have_position = symbol in our_position_map

            if change_type == 'NEW_ENTRY':
                if have_position:
                    logger.info(f"[SMART-COPY] Skip {side} {symbol} - already have position")
                    continue

                # Open new position
                action = 'LONG' if side == 'LONG' else 'SHORT'
                decisions.append({
                    'action': action,
                    'symbol': symbol,
                    'reasoning': f"[SMART-COPY] {reason}",
                    'confidence': 0.85
                })

            elif change_type == 'CLOSE':
                if not have_position:
                    logger.info(f"[SMART-COPY] Skip CLOSE {symbol} - no position to close")
                    continue

                # Close our position
                decisions.append({
                    'action': 'CLOSE',
                    'symbol': symbol,
                    'reasoning': f"[SMART-COPY] {reason}",
                    'confidence': 0.9
                })
                self._record_close(symbol)

            elif change_type == 'FLIP':
                # Close existing if we have one, then open opposite
                if have_position:
                    decisions.append({
                        'action': 'CLOSE',
                        'symbol': symbol,
                        'reasoning': f"[SMART-COPY] Closing for flip - {reason}",
                        'confidence': 0.9
                    })
                    self._record_close(symbol)

                # Open new direction (but respect cooldown)
                if not self._is_on_cooldown(symbol):
                    action = 'LONG' if side == 'LONG' else 'SHORT'
                    decisions.append({
                        'action': action,
                        'symbol': symbol,
                        'reasoning': f"[SMART-COPY] {reason}",
                        'confidence': 0.85
                    })

            elif change_type == 'REDUCE':
                # If whale reduced significantly, consider closing
                if have_position:
                    decisions.append({
                        'action': 'CLOSE',
                        'symbol': symbol,
                        'reasoning': f"[SMART-COPY] {reason} - taking profit with whale",
                        'confidence': 0.75
                    })
                    self._record_close(symbol)

            elif change_type == 'ADD':
                # Skip if we already have position (no stacking)
                if have_position:
                    logger.info(f"[SMART-COPY] Skip ADD {symbol} - already have position (no stacking)")
                    continue

                # Open if we don't have
                action = 'LONG' if side == 'LONG' else 'SHORT'
                decisions.append({
                    'action': action,
                    'symbol': symbol,
                    'reasoning': f"[SMART-COPY] {reason}",
                    'confidence': 0.8
                })

        # Update last known positions
        self.last_whale_positions = current_whale

        # Log decisions
        if decisions:
            logger.info("")
            logger.info("=" * 60)
            logger.info(f"[SMART-COPY] DECISIONS ({len(decisions)})")
            logger.info("=" * 60)
            for d in decisions:
                logger.info(f"  {d['action']} {d['symbol']}: {d['reasoning']}")
            logger.info("=" * 60)

        return decisions

    def get_status_summary(self) -> Dict:
        """Get current strategy status"""
        return {
            "strategy": self.STRATEGY_NAME,
            "whale": self.WHALE_NAME,
            "assets": self.COPY_ASSETS,
            "last_fetch": self.last_fetch_time.strftime("%H:%M:%S") if self.last_fetch_time else "Never",
            "tracked_positions": len(self.last_whale_positions),
            "cooldowns_active": len([s for s, t in self.recent_closes.items()
                                    if datetime.now() < t + timedelta(hours=self.close_cooldown_hours)])
        }
