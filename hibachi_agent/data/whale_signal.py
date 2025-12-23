"""
Whale Signal Fetcher for Hibachi
Fetches whale positions from Hyperliquid and formats as LLM context

NOT for blind copying - just another signal input for Qwen to consider
alongside technicals (RSI, MACD, etc.) and risk data (Cambrian).

Whale: 0x023a3d058020fb76cca98f01b3c48c8938a22355
- $28M account, 28 trades/min
- Focus on BTC/ETH/SOL
- +$966K unrealized profit
"""

import logging
import requests
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class WhaleSignalFetcher:
    """
    Fetch whale positions as signal context for LLM

    This is NOT copy trading - it's just another data point
    for Qwen to consider when making decisions.
    """

    WHALE_ADDRESS = "0x023a3d058020fb76cca98f01b3c48c8938a22355"
    WHALE_NAME = "Multi-Asset Scalper (0x023a)"
    HYPERLIQUID_API = "https://api.hyperliquid.xyz/info"

    # Map Hyperliquid symbols to Hibachi symbols
    SYMBOL_MAP = {
        "BTC": "BTC/USDT-P",
        "ETH": "ETH/USDT-P",
        "SOL": "SOL/USDT-P"
    }

    def __init__(self):
        self.last_fetch_time = None
        self.cached_positions = {}
        self.cache_ttl_seconds = 60  # Cache for 1 minute

        logger.info(f"[WHALE] Signal fetcher initialized - tracking {self.WHALE_NAME}")

    def fetch_positions(self) -> Dict[str, Dict]:
        """
        Fetch whale's current positions from Hyperliquid

        Returns:
            Dict mapping symbol -> position info
        """
        # Check cache
        if self.last_fetch_time:
            age = (datetime.now() - self.last_fetch_time).total_seconds()
            if age < self.cache_ttl_seconds and self.cached_positions:
                return self.cached_positions

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
                logger.warning(f"[WHALE] API error: {response.status_code}")
                return self.cached_positions or {}

            data = response.json()
            margin = data.get('marginSummary', {})
            positions = data.get('assetPositions', [])

            account_value = float(margin.get('accountValue', 0))

            whale_positions = {}
            for p in positions:
                pos = p.get('position', {})
                coin = pos.get('coin', '')

                if coin in self.SYMBOL_MAP:
                    size = float(pos.get('szi', 0))
                    if size != 0:
                        entry_price = float(pos.get('entryPx', 0))
                        unrealized_pnl = float(pos.get('unrealizedPnl', 0))
                        notional = abs(size * entry_price)
                        side = 'LONG' if size > 0 else 'SHORT'
                        allocation_pct = (notional / account_value * 100) if account_value > 0 else 0

                        hibachi_symbol = self.SYMBOL_MAP[coin]
                        whale_positions[hibachi_symbol] = {
                            'coin': coin,
                            'side': side,
                            'size': abs(size),
                            'entry_price': entry_price,
                            'notional': notional,
                            'unrealized_pnl': unrealized_pnl,
                            'allocation_pct': allocation_pct
                        }

            self.cached_positions = whale_positions
            self.last_fetch_time = datetime.now()
            self.account_value = account_value

            return whale_positions

        except Exception as e:
            logger.warning(f"[WHALE] Error fetching positions: {e}")
            return self.cached_positions or {}

    def format_for_prompt(self) -> str:
        """
        Format whale positions as context for LLM prompt

        Returns:
            Formatted string to inject into prompt
        """
        positions = self.fetch_positions()

        if not positions:
            return ""

        lines = []
        lines.append("")
        lines.append("WHALE SIGNAL (0x023a - $28M account, proven trader):")
        lines.append("Symbol      | Bias  | Allocation | Unrealized P/L")
        lines.append("-" * 55)

        total_pnl = 0
        for symbol in ["BTC/USDT-P", "ETH/USDT-P", "SOL/USDT-P"]:
            if symbol in positions:
                p = positions[symbol]
                pnl_str = f"${p['unrealized_pnl']:+,.0f}"
                total_pnl += p['unrealized_pnl']
                lines.append(
                    f"{symbol:12} | {p['side']:5} | {p['allocation_pct']:5.1f}%     | {pnl_str}"
                )
            else:
                lines.append(f"{symbol:12} | FLAT  | 0.0%      | $0")

        lines.append("-" * 55)
        lines.append(f"Total Unrealized: ${total_pnl:+,.0f}")
        lines.append("")
        lines.append("NOTE: Whale signal is ONE input - combine with technicals for final decision.")
        lines.append("")

        return "\n".join(lines)

    def get_bias(self, symbol: str) -> Optional[str]:
        """
        Get whale's directional bias for a symbol

        Returns:
            'LONG', 'SHORT', or None if no position
        """
        positions = self.fetch_positions()
        if symbol in positions:
            return positions[symbol]['side']
        return None

    def log_status(self):
        """Log current whale positions"""
        positions = self.fetch_positions()

        if not positions:
            logger.info("[WHALE] No positions or fetch failed")
            return

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"[WHALE] {self.WHALE_NAME}")
        logger.info(f"[WHALE] Account: ${getattr(self, 'account_value', 0):,.0f}")
        logger.info("=" * 60)

        for symbol, p in positions.items():
            logger.info(
                f"  {symbol}: {p['side']} {p['allocation_pct']:.1f}% | "
                f"P/L: ${p['unrealized_pnl']:+,.0f}"
            )

        logger.info("=" * 60)
        logger.info("")
