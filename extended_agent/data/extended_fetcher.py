"""
Extended Market Data Fetcher
Fetches OHLCV, funding rates, and market data from Extended DEX
"""

import logging
import pandas as pd
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import asyncio

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dexes.extended.extended_sdk import ExtendedSDK, create_extended_sdk_from_env

logger = logging.getLogger(__name__)


class ExtendedDataFetcher:
    """
    Fetch market data from Extended DEX
    Provides OHLCV candles, funding rates, OI, and prices
    """

    def __init__(self, sdk: Optional[ExtendedSDK] = None):
        """
        Initialize Extended data fetcher

        Args:
            sdk: ExtendedSDK instance (creates from env if not provided)
        """
        self.sdk = sdk or create_extended_sdk_from_env()
        self.available_symbols = []
        self._initialized = False

        logger.info("ExtendedDataFetcher initialized")

    async def _initialize_symbols(self):
        """Fetch and cache available symbols"""
        if self._initialized:
            return

        try:
            markets = await self.sdk.get_markets()
            if markets:
                # Only active markets
                self.available_symbols = [
                    m["name"] for m in markets
                    if m.get("status") == "ACTIVE" and m.get("active", False)
                ]
                self._initialized = True
                logger.info(f"Extended: {len(self.available_symbols)} active markets available")
        except Exception as e:
            logger.error(f"Failed to initialize Extended symbols: {e}")

    async def fetch_kline(
        self,
        symbol: str,
        interval: str = "5m",
        limit: int = 100
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV candle data

        Args:
            symbol: Market symbol (e.g., "BTC-USD")
            interval: Candle interval (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Number of candles

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        try:
            candles = await self.sdk.get_candles(
                market=symbol,
                interval=interval,
                limit=limit,
                candle_type="trades"
            )

            if not candles:
                logger.warning(f"No candle data for {symbol}")
                return None

            # Convert to DataFrame
            df = pd.DataFrame(candles)

            # Rename columns to standard format
            df = df.rename(columns={
                "o": "open",
                "h": "high",
                "l": "low",
                "c": "close",
                "v": "volume",
                "T": "timestamp"
            })

            # Convert types
            for col in ["open", "high", "low", "close", "volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # Convert timestamp from milliseconds
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

            # Sort by time ascending (Extended returns descending)
            df = df.sort_values("timestamp").reset_index(drop=True)

            logger.debug(f"Fetched {len(df)} candles for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Error fetching klines for {symbol}: {e}")
            return None

    async def fetch_funding_rate(self, symbol: str) -> Optional[float]:
        """
        Fetch current funding rate for a symbol

        Args:
            symbol: Market symbol (e.g., "BTC-USD")

        Returns:
            Current funding rate (decimal)
        """
        try:
            stats = await self.sdk.get_market_stats(symbol)
            if stats:
                rate = float(stats.get("fundingRate", 0))
                return rate
            return None
        except Exception as e:
            logger.error(f"Error fetching funding rate for {symbol}: {e}")
            return None

    async def fetch_open_interest(self, symbol: str) -> Optional[float]:
        """
        Fetch current open interest for a symbol

        Args:
            symbol: Market symbol (e.g., "BTC-USD")

        Returns:
            Open interest in USD
        """
        try:
            stats = await self.sdk.get_market_stats(symbol)
            if stats:
                oi = float(stats.get("openInterest", 0))
                return oi
            return None
        except Exception as e:
            logger.error(f"Error fetching OI for {symbol}: {e}")
            return None

    async def fetch_market_data(
        self,
        symbol: str,
        interval: str = "5m",
        limit: int = 100
    ) -> Optional[Dict]:
        """
        Fetch comprehensive market data for a symbol

        Args:
            symbol: Market symbol (e.g., "BTC-USD")
            interval: Candle interval
            limit: Number of candles

        Returns:
            Dict with kline_df, funding_rate, current_price, oi, etc.
        """
        await self._initialize_symbols()

        if symbol not in self.available_symbols:
            logger.warning(f"{symbol} not available on Extended")
            return None

        try:
            # Fetch all data concurrently
            kline_task = self.fetch_kline(symbol, interval, limit)
            stats_task = self.sdk.get_market_stats(symbol)

            kline_df, stats = await asyncio.gather(kline_task, stats_task)

            current_price = None
            funding_rate = None
            oi = None
            volume_24h = None

            if stats:
                current_price = float(stats.get("lastPrice", 0))
                funding_rate = float(stats.get("fundingRate", 0))
                oi = float(stats.get("openInterest", 0))
                volume_24h = float(stats.get("dailyVolume", 0))

            return {
                "symbol": symbol,
                "kline_df": kline_df,
                "current_price": current_price,
                "funding_rate": funding_rate,
                "oi": oi,
                "volume_24h": volume_24h
            }

        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {e}")
            return None

    async def fetch_all_markets(
        self,
        symbols: Optional[List[str]] = None,
        interval: str = "5m",
        limit: int = 100
    ) -> Dict[str, Dict]:
        """
        Fetch market data for multiple symbols concurrently

        Args:
            symbols: List of symbols (default: all available)
            interval: Candle interval
            limit: Number of candles per symbol

        Returns:
            Dict mapping symbol -> market data
        """
        await self._initialize_symbols()

        if symbols is None:
            symbols = self.available_symbols

        # Limit concurrent requests to avoid rate limiting
        results = {}
        batch_size = 10

        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            tasks = [self.fetch_market_data(s, interval, limit) for s in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for symbol, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Error fetching {symbol}: {result}")
                elif result:
                    results[symbol] = result

            # Small delay between batches to avoid rate limits
            if i + batch_size < len(symbols):
                await asyncio.sleep(0.5)

        logger.info(f"Fetched data for {len(results)}/{len(symbols)} Extended markets")
        return results


# Test the fetcher
if __name__ == "__main__":
    import asyncio

    async def test():
        fetcher = ExtendedDataFetcher()

        # Initialize and show markets
        await fetcher._initialize_symbols()
        print(f"Available markets: {len(fetcher.available_symbols)}")
        print(f"First 10: {fetcher.available_symbols[:10]}")

        # Fetch BTC data
        data = await fetcher.fetch_market_data("BTC-USD", interval="5m", limit=20)
        if data:
            print(f"\nBTC-USD:")
            print(f"  Price: ${data['current_price']:,.2f}")
            print(f"  Funding: {data['funding_rate']:.6f}")
            print(f"  OI: ${data['oi']:,.0f}")
            print(f"  24h Vol: ${data['volume_24h']:,.0f}")
            if data['kline_df'] is not None:
                print(f"  Candles: {len(data['kline_df'])}")
                print(data['kline_df'].tail())

    asyncio.run(test())
