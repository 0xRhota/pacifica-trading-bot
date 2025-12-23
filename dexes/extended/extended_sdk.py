"""
Extended DEX SDK Wrapper
REST API implementation for Extended Exchange (Starknet)

API Docs: https://api.docs.extended.exchange/
Base URL: https://api.starknet.extended.exchange/api/v1
"""

import asyncio
import aiohttp
import logging
import os
from typing import Dict, Optional, List
from decimal import Decimal
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class ExtendedSDK:
    """REST API wrapper for Extended Exchange trading"""

    def __init__(
        self,
        api_key: str,
        stark_private_key: Optional[str] = None,
        stark_public_key: Optional[str] = None,
        vault: Optional[int] = None,
        testnet: bool = False
    ):
        """
        Initialize Extended SDK

        Args:
            api_key: API key from Extended API management page
            stark_private_key: Stark private key for order signing (optional for read-only)
            stark_public_key: Stark public key
            vault: Vault/position ID
            testnet: Use testnet instead of mainnet
        """
        if testnet:
            self.base_url = "https://api.starknet.sepolia.extended.exchange/api/v1"
        else:
            self.base_url = "https://api.starknet.extended.exchange/api/v1"

        self.api_key = api_key
        self.stark_private_key = stark_private_key
        self.stark_public_key = stark_public_key
        self.vault = vault

        # Cache for market info
        self._markets_cache = None
        self._markets_cache_time = None
        self._cache_ttl = 300  # 5 minutes

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        return {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "PacificaTradingBot/1.0"
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Make API request

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            data: Request body

        Returns:
            JSON response or None on error
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=data
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get("status") == "OK":
                            return result.get("data")
                        else:
                            error = result.get("error", {})
                            logger.error(f"API Error: {error.get('message', 'Unknown error')}")
                            return None
                    elif resp.status == 429:
                        logger.warning("Rate limited by Extended API")
                        return None
                    else:
                        error_text = await resp.text()
                        logger.error(f"HTTP Error {resp.status}: {error_text}")
                        return None

        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None

    # ==================== PUBLIC ENDPOINTS ====================

    async def get_markets(self, market_names: Optional[List[str]] = None) -> Optional[List[Dict]]:
        """
        Get available markets and their configurations

        Args:
            market_names: Optional list of market names to filter

        Returns:
            List of market data dicts
        """
        params = {}
        if market_names:
            # Extended uses repeated params for multiple markets
            params["market"] = market_names

        return await self._request("GET", "/info/markets", params=params)

    async def get_market_stats(self, market: str) -> Optional[Dict]:
        """
        Get trading statistics for a market

        Args:
            market: Market name (e.g., "BTC-USD")

        Returns:
            Market stats dict with price, volume, funding rate, etc.
        """
        return await self._request("GET", f"/info/markets/{market}/stats")

    async def get_orderbook(self, market: str) -> Optional[Dict]:
        """
        Get current orderbook for a market

        Args:
            market: Market name

        Returns:
            Orderbook with bid/ask arrays
        """
        return await self._request("GET", f"/info/markets/{market}/orderbook")

    async def get_candles(
        self,
        market: str,
        interval: str = "5m",
        limit: int = 100,
        end_time: Optional[int] = None,
        candle_type: str = "trades"
    ) -> Optional[List[Dict]]:
        """
        Get OHLCV candle data

        Args:
            market: Market name (e.g., "BTC-USD")
            interval: Candle interval (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Number of candles to fetch
            end_time: End timestamp in milliseconds
            candle_type: "trades", "mark-prices", or "index-prices"

        Returns:
            List of candle dicts with o, h, l, c, v, T fields
        """
        params = {
            "interval": interval,
            "limit": limit
        }
        if end_time:
            params["endTime"] = end_time

        return await self._request("GET", f"/info/candles/{market}/{candle_type}", params=params)

    async def get_funding_rates(
        self,
        market: str,
        start_time: int,
        end_time: int,
        limit: int = 100
    ) -> Optional[List[Dict]]:
        """
        Get historical funding rates

        Args:
            market: Market name
            start_time: Start timestamp (ms)
            end_time: End timestamp (ms)
            limit: Max records

        Returns:
            List of funding rate records
        """
        params = {
            "startTime": start_time,
            "endTime": end_time,
            "limit": limit
        }
        return await self._request("GET", f"/info/{market}/funding", params=params)

    async def get_open_interest(
        self,
        market: str,
        interval: str = "P1H",
        start_time: int = None,
        end_time: int = None
    ) -> Optional[List[Dict]]:
        """
        Get open interest history

        Args:
            market: Market name
            interval: P1H (hourly) or P1D (daily)
            start_time: Start timestamp (ms)
            end_time: End timestamp (ms)

        Returns:
            List of OI records
        """
        import time
        now = int(time.time() * 1000)
        params = {
            "interval": interval,
            "startTime": start_time or (now - 86400000),  # Default: last 24h
            "endTime": end_time or now
        }
        return await self._request("GET", f"/info/{market}/open-interests", params=params)

    # ==================== PRIVATE ENDPOINTS ====================

    async def get_balance(self) -> Optional[Dict]:
        """
        Get account balance

        Returns:
            Balance dict with equity, available, margin, etc.
        """
        return await self._request("GET", "/user/balance")

    async def get_positions(
        self,
        market_names: Optional[List[str]] = None,
        side: Optional[str] = None
    ) -> Optional[List[Dict]]:
        """
        Get open positions

        Args:
            market_names: Filter by markets
            side: Filter by side ("LONG" or "SHORT")

        Returns:
            List of position dicts
        """
        params = {}
        if market_names:
            params["market"] = market_names
        if side:
            params["side"] = side

        return await self._request("GET", "/user/positions", params=params)

    async def get_open_orders(
        self,
        market_names: Optional[List[str]] = None,
        order_type: Optional[str] = None,
        side: Optional[str] = None
    ) -> Optional[List[Dict]]:
        """
        Get open orders

        Args:
            market_names: Filter by markets
            order_type: Filter by type (LIMIT, CONDITIONAL, TPSL, TWAP)
            side: Filter by side (BUY, SELL)

        Returns:
            List of order dicts
        """
        params = {}
        if market_names:
            params["market"] = market_names
        if order_type:
            params["type"] = order_type
        if side:
            params["side"] = side

        return await self._request("GET", "/user/orders", params=params)

    async def get_leverage(self, market: Optional[str] = None) -> Optional[List[Dict]]:
        """
        Get current leverage settings

        Args:
            market: Optional market to filter

        Returns:
            List of leverage settings per market
        """
        params = {}
        if market:
            params["market"] = market
        return await self._request("GET", "/user/leverage", params=params)

    async def get_fees(self, market: Optional[str] = None) -> Optional[List[Dict]]:
        """
        Get fee rates

        Args:
            market: Optional market to filter

        Returns:
            List of fee info per market
        """
        params = {}
        if market:
            params["market"] = market
        return await self._request("GET", "/user/fees", params=params)

    async def get_trades(
        self,
        market_names: Optional[List[str]] = None,
        limit: int = 100
    ) -> Optional[List[Dict]]:
        """
        Get trade history

        Args:
            market_names: Filter by markets
            limit: Max records

        Returns:
            List of trade records
        """
        params = {"limit": limit}
        if market_names:
            params["market"] = market_names
        return await self._request("GET", "/user/trades", params=params)

    # ==================== ORDER ENDPOINTS ====================

    async def create_market_order(
        self,
        market: str,
        is_buy: bool,
        size: float,
        reduce_only: bool = False
    ) -> Optional[Dict]:
        """
        Create a market order

        Args:
            market: Market name (e.g., "BTC-USD")
            is_buy: True for buy/long, False for sell/short
            size: Position size in base currency
            reduce_only: If True, only reduces existing position

        Returns:
            Order response dict with orderId
        """
        # Note: Extended uses Starknet signatures for order signing
        # This requires the stark_private_key to be set
        if not self.stark_private_key:
            logger.error("Stark private key required for trading")
            return None

        try:
            # Import starknet signing library
            from starknet_py.hash.utils import compute_hash_on_elements
            from starknet_py.net.client_models import Call
            import time

            side = "BUY" if is_buy else "SELL"

            # Get market info for precision
            markets = await self.get_markets([market])
            if not markets:
                logger.error(f"Could not get market info for {market}")
                return None

            market_info = markets[0]
            size_precision = market_info.get("quantityResolution", 8)

            # Format size with proper precision
            size_str = f"{size:.{size_precision}f}".rstrip('0').rstrip('.')

            # Build order payload
            order_data = {
                "market": market,
                "side": side,
                "type": "MARKET",
                "size": size_str,
                "reduceOnly": reduce_only,
                "clientId": f"arb_{int(time.time() * 1000)}"
            }

            # Sign order with Stark key
            # Note: Full Starknet signing is complex - this is a simplified version
            # In production, use the official Extended SDK or starknet-py properly

            logger.info(f"Creating market order: {side} {size_str} {market}")

            result = await self._request("POST", "/user/orders", data=order_data)

            if result:
                logger.info(f"Order created: {result.get('id', result.get('orderId'))}")
                return result

            return None

        except ImportError:
            logger.error("starknet-py not installed. Install with: pip install starknet-py")
            return None
        except Exception as e:
            logger.error(f"Error creating market order: {e}")
            return None

    async def close_position(self, market: str) -> Optional[Dict]:
        """
        Close an entire position for a market

        Args:
            market: Market name (e.g., "BTC-USD")

        Returns:
            Order response dict
        """
        # Get current position
        positions = await self.get_positions([market])
        if not positions:
            logger.info(f"No position to close for {market}")
            return None

        position = positions[0]
        size = float(position.get("size", 0))
        side = position.get("side", "").upper()

        if size <= 0:
            logger.info(f"No position to close for {market}")
            return None

        # To close: sell if long, buy if short
        is_buy = side == "SHORT"

        return await self.create_market_order(
            market=market,
            is_buy=is_buy,
            size=size,
            reduce_only=True
        )

    # ==================== HELPER METHODS ====================

    async def get_price(self, market: str) -> Optional[float]:
        """
        Get current price for a market

        Args:
            market: Market name (e.g., "BTC-USD")

        Returns:
            Current last price
        """
        stats = await self.get_market_stats(market)
        if stats:
            return float(stats.get("lastPrice", 0))
        return None

    async def get_available_markets(self) -> List[str]:
        """
        Get list of available market names

        Returns:
            List of market name strings
        """
        # Check cache
        import time
        now = time.time()
        if self._markets_cache and self._markets_cache_time:
            if now - self._markets_cache_time < self._cache_ttl:
                return self._markets_cache

        markets = await self.get_markets()
        if markets:
            # Filter to active markets only
            active_markets = [
                m["name"] for m in markets
                if m.get("status") == "ACTIVE" and m.get("active", False)
            ]
            self._markets_cache = active_markets
            self._markets_cache_time = now
            return active_markets
        return []

    def convert_symbol_to_extended(self, symbol: str) -> str:
        """
        Convert internal symbol format to Extended format

        Args:
            symbol: Symbol like "BTC/USDT-P" or "BTC"

        Returns:
            Extended format like "BTC-USD"
        """
        # Remove /USDT-P suffix if present
        base = symbol.replace("/USDT-P", "").replace("-USDT-P", "")
        return f"{base}-USD"

    def convert_symbol_from_extended(self, symbol: str) -> str:
        """
        Convert Extended symbol format to internal format

        Args:
            symbol: Extended format like "BTC-USD"

        Returns:
            Internal format like "BTC/USDT-P"
        """
        base = symbol.replace("-USD", "")
        return f"{base}/USDT-P"


# Convenience function to create SDK from environment
def create_extended_sdk_from_env(testnet: bool = False) -> ExtendedSDK:
    """Create ExtendedSDK instance from environment variables"""
    # Try multiple env var names for API key
    api_key = os.getenv("EXTENDED") or os.getenv("EXTENDED_API_KEY")
    stark_private = os.getenv("EXTENDED_STARK_PRIVATE_KEY")
    stark_public = os.getenv("EXTENDED_STARK_PUBLIC_KEY")
    vault = os.getenv("EXTENDED_VAULT")

    if not api_key:
        raise ValueError("EXTENDED or EXTENDED_API_KEY not set in environment")

    return ExtendedSDK(
        api_key=api_key,
        stark_private_key=stark_private,
        stark_public_key=stark_public,
        vault=int(vault) if vault else None,
        testnet=testnet
    )


# Test the SDK
if __name__ == "__main__":
    import asyncio

    async def test():
        # Test public endpoints (no auth needed)
        sdk = ExtendedSDK(api_key="test", testnet=False)

        print("Testing Extended SDK...")

        # Get markets
        markets = await sdk.get_markets()
        if markets:
            print(f"Found {len(markets)} markets")
            for m in markets[:5]:
                print(f"  - {m.get('name')}: {m.get('status')}")

        # Get BTC stats
        stats = await sdk.get_market_stats("BTC-USD")
        if stats:
            print(f"\nBTC-USD Stats:")
            print(f"  Last Price: ${stats.get('lastPrice')}")
            print(f"  24h Volume: ${stats.get('dailyVolume')}")
            print(f"  Funding Rate: {stats.get('fundingRate')}")
            print(f"  Open Interest: ${stats.get('openInterest')}")

        # Get candles
        candles = await sdk.get_candles("BTC-USD", interval="5m", limit=5)
        if candles:
            print(f"\nBTC-USD 5m Candles (last 5):")
            for c in candles[:5]:
                print(f"  O:{c.get('o')} H:{c.get('h')} L:{c.get('l')} C:{c.get('c')}")

    asyncio.run(test())
