"""
Orderbook Liquidity Checker for Pacifica DEX
Prevents orders from being placed on markets with insufficient liquidity
"""

import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class LiquidityChecker:
    """Check orderbook liquidity before placing orders"""

    def __init__(self, sdk):
        """
        Initialize liquidity checker

        Args:
            sdk: PacificaSDK instance for API calls
        """
        self.sdk = sdk
        self._orderbook_cache = {}  # Cache orderbooks briefly
        self._cache_ttl = 5  # 5 seconds cache

    async def check_liquidity(
        self,
        symbol: str,
        side: str,  # 'BUY' or 'SELL'
        size_usd: float,
        current_price: float,
        market_id: Optional[int] = None
    ) -> Dict:
        """
        Check if orderbook has enough liquidity to fill this order

        Args:
            symbol: Trading symbol (e.g., 'BTC', 'SOL')
            side: 'BUY' or 'SELL'
            size_usd: Order size in USD
            current_price: Current market price
            market_id: Market ID (optional, will lookup if not provided)

        Returns:
            Dict with:
                - has_liquidity: bool - Whether there's sufficient liquidity
                - available_liquidity_usd: float - Available liquidity in USD
                - depth_ratio: float - Ratio of available to required liquidity
                - reason: str - Explanation
        """
        try:
            # Note: Pacifica SDK doesn't use market_id, works directly with symbols
            # market_id parameter is kept for API compatibility but ignored

            # Fetch orderbook from API (using symbol directly)
            orderbook = await self._fetch_orderbook(symbol)
            if not orderbook:
                # If we can't fetch orderbook, allow reasonable orders on filtered markets
                # With leverage-aware sizing, orders can be $60-120 depending on confidence
                if size_usd <= 150:  # Allow orders up to $150 if orderbook unavailable
                    logger.warning(f"⚠️  Could not fetch orderbook for {symbol} - allowing order (${size_usd:.2f}) on pre-filtered liquid market")
                    return {
                        'has_liquidity': True,
                        'available_liquidity_usd': size_usd,
                        'depth_ratio': 1.0,
                        'reason': 'Orderbook unavailable, allowing order on pre-filtered market'
                    }
                else:
                    return {
                        'has_liquidity': False,
                        'available_liquidity_usd': 0,
                        'depth_ratio': 0,
                        'reason': 'Orderbook unavailable and order size too large'
                    }

            # Calculate required liquidity (order size in tokens)
            required_tokens = size_usd / current_price

            # Check appropriate side of orderbook
            if side == 'BUY':
                # For BUY orders, check ASK side (selling side)
                available_tokens = self._calculate_available_liquidity(
                    orderbook.get('asks', []),
                    current_price,
                    max_price_slippage=0.02  # 2% max slippage
                )
            else:  # SELL
                # For SELL orders, check BID side (buying side)
                available_tokens = self._calculate_available_liquidity(
                    orderbook.get('bids', []),
                    current_price,
                    max_price_slippage=0.02  # 2% max slippage
                )

            available_usd = available_tokens * current_price
            depth_ratio = available_usd / size_usd if size_usd > 0 else 0

            # Require at least 2x the order size in orderbook depth
            MIN_DEPTH_RATIO = 2.0
            has_liquidity = depth_ratio >= MIN_DEPTH_RATIO

            reason = (
                f"Orderbook has ${available_usd:.2f} available (ratio: {depth_ratio:.2f}x) "
                f"for ${size_usd:.2f} order"
            )

            if not has_liquidity:
                reason += f" - INSUFFICIENT (need {MIN_DEPTH_RATIO}x minimum)"

            return {
                'has_liquidity': has_liquidity,
                'available_liquidity_usd': available_usd,
                'depth_ratio': depth_ratio,
                'reason': reason
            }

        except Exception as e:
            logger.error(f"Error checking liquidity for {symbol}: {e}")
            # On error, be conservative and reject
            return {
                'has_liquidity': False,
                'available_liquidity_usd': 0,
                'depth_ratio': 0,
                'reason': f"Error: {str(e)}"
            }

    async def _fetch_orderbook(self, symbol: str) -> Optional[Dict]:
        """
        Fetch orderbook from Pacifica API

        Args:
            symbol: Trading symbol (e.g., 'BTC', 'SOL')

        Returns:
            Dict with 'bids' and 'asks' arrays, or empty dict if unavailable
        """
        try:
            # Fetch from Pacifica API (old working code from api.py)
            import aiohttp
            url = f"https://api.pacifica.fi/api/v1/book?symbol={symbol}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                    if resp.status == 200:
                        response = await resp.json()

                        # OLD WORKING CODE (from archive/2025-11-07-old-pacifica-framework/dexes/pacifica/api.py lines 130-142)
                        if response.get("success") and response.get("data"):
                            data = response["data"]
                            # Convert Pacifica format to standard format
                            # Pacifica returns: l: [[bids], [asks]]
                            if "l" in data and isinstance(data["l"], list) and len(data["l"]) >= 2:
                                bids = [[item["p"], item["a"]] for item in data["l"][0]] if data["l"][0] else []
                                asks = [[item["p"], item["a"]] for item in data["l"][1]] if data["l"][1] else []
                                logger.info(f"✅ Fetched orderbook for {symbol}: {len(bids)} bids, {len(asks)} asks")
                                return {"bids": bids, "asks": asks}

                        logger.warning(f"Unexpected orderbook format for {symbol}")
                        return {}
                    else:
                        logger.warning(f"Orderbook API returned status {resp.status} for {symbol}")
                        return {}

        except Exception as e:
            logger.warning(f"Could not fetch orderbook for {symbol}: {e}")
            return {}

    def _calculate_available_liquidity(
        self,
        levels: list,
        current_price: float,
        max_price_slippage: float = 0.02
    ) -> float:
        """
        Calculate available liquidity within acceptable price range

        Args:
            levels: Orderbook levels [[price, size], ...]
            current_price: Current market price
            max_price_slippage: Maximum acceptable price slippage (e.g., 0.02 = 2%)

        Returns:
            Total available size in tokens within price range
        """
        if not levels:
            return 0

        max_price_deviation = current_price * max_price_slippage
        min_acceptable_price = current_price - max_price_deviation
        max_acceptable_price = current_price + max_price_deviation

        total_size = 0
        for level in levels:
            if len(level) < 2:
                continue

            price, size = float(level[0]), float(level[1])

            # Check if price is within acceptable range
            if min_acceptable_price <= price <= max_acceptable_price:
                total_size += size
            else:
                # Once we hit levels outside price range, stop
                # (assumes orderbook is sorted)
                break

        return total_size
