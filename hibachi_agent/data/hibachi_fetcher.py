"""
Hibachi DEX Data Fetcher
Uses HibachiSDK for market data
"""

import logging
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class HibachiDataFetcher:
    """
    Fetch market data from Hibachi DEX using HibachiSDK
    """

    def __init__(self, sdk=None):
        """
        Initialize Hibachi data fetcher

        Args:
            sdk: HibachiSDK instance
        """
        self.sdk = sdk
        self.available_symbols = []
        self._initialized = False

    async def _initialize_symbols(self):
        """
        Initialize available symbols from Hibachi SDK
        Retries on each call if symbols are empty (handles rate limit recovery)
        """
        # Only skip if already successfully initialized with markets
        if self._initialized and self.available_symbols:
            return

        if not self.sdk:
            return

        try:
            # Get markets from Hibachi
            markets = await self.sdk.get_markets()
            if markets:
                self.available_symbols = [m['symbol'] for m in markets]
                self._initialized = True
                logger.info(f"✅ Initialized Hibachi fetcher with {len(self.available_symbols)} markets: {self.available_symbols}")
            else:
                logger.warning("No markets returned from Hibachi SDK - will retry next cycle")
        except Exception as e:
            logger.error(f"Error initializing Hibachi symbols (will retry): {e}")

    async def fetch_kline(
        self,
        symbol: str,
        interval: str = "15m",
        limit: int = 100
    ) -> Optional[pd.DataFrame]:
        """
        Fetch kline (OHLCV) data for a symbol

        Note: Hibachi SDK doesn't have historical kline endpoint yet
        For now, return None - will need to add this to SDK or use mock data

        Args:
            symbol: Trading symbol (e.g., "SOL/USDT-P")
            interval: Candle interval
            limit: Number of candles

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        await self._initialize_symbols()

        # TODO: Implement when Hibachi SDK has kline endpoint
        # For now, return None - bot will work with current price only
        logger.debug(f"Kline data not yet implemented for Hibachi {symbol}")
        return None

    async def fetch_current_price(self, symbol: str) -> Optional[float]:
        """
        Fetch current price for a symbol

        Args:
            symbol: Hibachi symbol (e.g., "SOL/USDT-P")

        Returns:
            Current price or None
        """
        await self._initialize_symbols()

        if not self.sdk:
            return None

        try:
            price = await self.sdk.get_price(symbol)
            return float(price) if price else None
        except Exception as e:
            logger.error(f"Error fetching Hibachi price for {symbol}: {e}")
            return None

    async def fetch_funding_rate(self, symbol: str) -> Optional[float]:
        """
        Fetch funding rate for a symbol

        Args:
            symbol: Hibachi symbol (e.g., "SOL/USDT-P")

        Returns:
            Funding rate or None
        """
        # TODO: Implement when Hibachi SDK has funding rate endpoint
        # For now, return None
        return None

    async def fetch_market_data(
        self,
        symbol: str,
        interval: str = "15m",
        limit: int = 100
    ) -> Optional[Dict]:
        """
        Fetch comprehensive market data for a symbol

        Args:
            symbol: Hibachi symbol
            interval: Candle interval
            limit: Number of candles

        Returns:
            Dict with kline_df, funding_rate, current_price
        """
        await self._initialize_symbols()

        kline_df = await self.fetch_kline(symbol, interval, limit)
        current_price = await self.fetch_current_price(symbol)
        funding_rate = await self.fetch_funding_rate(symbol)

        return {
            'kline_df': kline_df,
            'current_price': current_price,
            'funding_rate': funding_rate
        }

    async def fetch_all_markets(
        self,
        symbols: List[str],
        interval: str = "15m",
        limit: int = 100
    ) -> Dict[str, Dict]:
        """
        Fetch market data for multiple symbols

        Args:
            symbols: List of symbols
            interval: Candle interval
            limit: Number of candles

        Returns:
            Dict mapping symbol -> market data
        """
        results = {}

        for symbol in symbols:
            data = await self.fetch_market_data(symbol, interval, limit)
            if data:
                results[symbol] = data

        return results
