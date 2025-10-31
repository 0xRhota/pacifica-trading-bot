"""
Token Analysis Tool
Allows LLM to discover and analyze tokens dynamically each cycle

Features:
- Get list of available perpetual tokens (HyperLiquid + Pacifica)
- Request detailed analysis of specific tokens (technicals + sentiment)
- Re-evaluate open positions with current market conditions
"""

import logging
import requests
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class TokenAnalysisTool:
    """Tool for LLM to discover and analyze tokens dynamically"""

    def __init__(self, cambrian_api_key: str):
        """
        Initialize token analysis tool

        Args:
            cambrian_api_key: Cambrian API key for Deep42 queries
        """
        self.cambrian_api_key = cambrian_api_key
        self.hyperliquid_url = "https://api.hyperliquid.xyz/info"
        self.deep42_url = "https://deep42.cambrian.network/api/v1/deep42/agents/deep42"

    def get_available_tokens(self, limit: int = 50) -> List[str]:
        """
        Get list of available perpetual tokens from HyperLiquid

        Args:
            limit: Max tokens to return (default: 50)

        Returns:
            List of token symbols sorted by open interest
        """
        try:
            response = requests.post(
                self.hyperliquid_url,
                json={"type": "metaAndAssetCtxs"},
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                meta = data[0]
                contexts = data[1]

                # Build list of (symbol, OI) tuples
                tokens_with_oi = []
                for i, market in enumerate(meta['universe']):
                    symbol = market['name']
                    if i < len(contexts):
                        oi = contexts[i].get('openInterest')
                        if oi:
                            tokens_with_oi.append((symbol, float(oi)))

                # Sort by OI descending
                tokens_with_oi.sort(key=lambda x: x[1], reverse=True)

                # Return top N symbols
                top_tokens = [symbol for symbol, _ in tokens_with_oi[:limit]]
                logger.info(f"✅ Found {len(top_tokens)} tokens on HyperLiquid")
                return top_tokens

            else:
                logger.warning(f"HyperLiquid fetch failed: HTTP {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"HyperLiquid error: {e}")
            return []

    def analyze_token(self, symbol: str) -> Optional[str]:
        """
        Get Deep42 analysis for a specific token

        Args:
            symbol: Token symbol (e.g., "PENGU", "SOL", "BTC")

        Returns:
            Deep42 analysis string or None if failed
        """
        try:
            question = (
                f"What is the current sentiment, recent news, and key technical "
                f"factors for {symbol}? Include any catalysts, developments, or "
                f"risks that could affect its price in the next 24-48 hours."
            )

            headers = {
                "X-API-KEY": self.cambrian_api_key,
                "Content-Type": "application/json"
            }
            params = {"question": question}

            response = requests.get(self.deep42_url, headers=headers, params=params, timeout=60)
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer")
                logger.info(f"✅ Deep42 token analysis: {symbol}")
                return answer
            else:
                logger.warning(f"Deep42 token analysis failed for {symbol}: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Deep42 token analysis error for {symbol}: {e}")
            return None

    def evaluate_position(self, symbol: str, entry_price: float, current_price: float,
                          side: str, time_held: str) -> Optional[str]:
        """
        Get Deep42 evaluation of an open position

        Args:
            symbol: Token symbol
            entry_price: Entry price
            current_price: Current price
            side: LONG or SHORT
            time_held: How long position has been open

        Returns:
            Deep42 evaluation string or None if failed
        """
        try:
            pnl_pct = ((current_price - entry_price) / entry_price * 100) if side == "LONG" else ((entry_price - current_price) / entry_price * 100)

            question = (
                f"I have an open {side} position on {symbol}. "
                f"Entry: ${entry_price:.2f}, Current: ${current_price:.2f}, "
                f"P&L: {pnl_pct:+.2f}%, Time held: {time_held}. "
                f"Should I close this position now or let it run? "
                f"Consider current market conditions, technicals, and any upcoming catalysts."
            )

            headers = {
                "X-API-KEY": self.cambrian_api_key,
                "Content-Type": "application/json"
            }
            params = {"question": question}

            response = requests.get(self.deep42_url, headers=headers, params=params, timeout=60)
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer")
                logger.info(f"✅ Deep42 position evaluation: {symbol} {side}")
                return answer
            else:
                logger.warning(f"Deep42 position evaluation failed for {symbol}: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Deep42 position evaluation error for {symbol}: {e}")
            return None
