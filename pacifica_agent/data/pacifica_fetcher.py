"""
Pacifica DEX Data Fetcher
Uses Pacifica HTTP API for market data

Symbols fetched dynamically from Pacifica API
"""

import logging
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime
import time
import aiohttp

logger = logging.getLogger(__name__)


class PacificaDataFetcher:
    """
    Fetch market data from Pacifica DEX using HTTP API
    Symbols and market IDs fetched dynamically from API
    """

    def __init__(self, sdk=None):
        """
        Initialize Pacifica data fetcher

        Args:
            sdk: PacificaSDK instance (optional, for symbol loading - not used for market data)
        """
        self.sdk = sdk
        self.base_url = "https://api.pacifica.fi/api/v1"
        self.available_symbols = []  # Will be populated from API
        self._initialized = False

    async def _initialize_symbols(self):
        """
        Initialize available symbols from Pacifica API

        This is called automatically the first time data is fetched
        """
        if self._initialized:
            return

        try:
            # Fetch all markets from Pacifica API
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/markets", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Extract symbols from markets data
                        if isinstance(data, dict) and 'data' in data:
                            markets = data['data']
                            self.available_symbols = [m.get('symbol') for m in markets if m.get('symbol')]
                        elif isinstance(data, list):
                            self.available_symbols = [m.get('symbol') for m in data if m.get('symbol')]
                        else:
                            logger.warning(f"Unexpected markets response format: {type(data)}")
                            # Fallback to common symbols
                            self.available_symbols = ['BTC', 'SOL', 'ETH', 'DOGE', 'WIF']
                    else:
                        logger.warning(f"Markets API returned status {resp.status}, using fallback symbols")
                        # Fallback to common symbols
                        self.available_symbols = ['BTC', 'SOL', 'ETH', 'DOGE', 'WIF']

            self._initialized = True
            logger.info(f"✅ Initialized Pacifica fetcher with {len(self.available_symbols)} markets from API: {self.available_symbols}")

        except Exception as e:
            logger.error(f"Error initializing Pacifica symbols: {e}, using fallback")
            self.available_symbols = ['BTC', 'SOL', 'ETH', 'DOGE', 'WIF']
            self._initialized = True

    async def fetch_kline(
        self,
        symbol: str,
        interval: str = "15m",
        limit: int = 100,
        candlestick_api=None  # Not used for Pacifica, included for API compatibility
    ) -> Optional[pd.DataFrame]:
        """
        Fetch kline (OHLCV) data for a symbol using Pacifica API

        Args:
            symbol: Trading symbol (e.g., "SOL")
            interval: Candle interval (e.g., "15m")
            limit: Number of candles to fetch
            candlestick_api: Ignored (for API compatibility with Lighter)

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        # Ensure symbols are initialized
        await self._initialize_symbols()

        if symbol not in self.available_symbols:
            logger.warning(f"Symbol {symbol} not in available markets (available: {self.available_symbols})")

        try:
            # Calculate timestamps (milliseconds for Pacifica)
            end_timestamp = int(time.time() * 1000)
            interval_minutes = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "2h": 120, "4h": 240, "8h": 480, "12h": 720, "1d": 1440}.get(interval, 15)
            start_timestamp = end_timestamp - (limit * interval_minutes * 60 * 1000)

            # Call Pacifica API
            url = f"{self.base_url}/kline"
            params = {
                'symbol': symbol,
                'interval': interval,
                'start_time': start_timestamp,
                'limit': limit
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        logger.warning(f"Pacifica kline API returned status {resp.status} for {symbol}")
                        return None

                    result = await resp.json()

            if not result or 'data' not in result:
                logger.warning(f"No candlestick data returned for {symbol}")
                return None

            # Parse result.data (list of candles)
            candles = result['data']

            # Convert to list of dicts
            # Note: Pacifica API uses abbreviated keys: t, o, h, l, c, v
            data = []
            for candle in candles:
                data.append({
                    'timestamp': candle.get('t', candle.get('timestamp', candle.get('time', 0))),
                    'open': float(candle.get('o', candle.get('open', 0))),
                    'high': float(candle.get('h', candle.get('high', 0))),
                    'low': float(candle.get('l', candle.get('low', 0))),
                    'close': float(candle.get('c', candle.get('close', 0))),
                    'volume': float(candle.get('v', candle.get('volume', 0)))
                })

            # Create DataFrame
            df = pd.DataFrame(data)

            if df.empty:
                return None

            # Convert timestamp to datetime (milliseconds)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce')

            # Sort by timestamp
            df = df.sort_values('timestamp').reset_index(drop=True)

            logger.info(f"✅ Fetched {len(df)} candles for {symbol} ({interval}) from Pacifica")
            return df

        except Exception as e:
            logger.error(f"Error fetching Pacifica kline for {symbol}: {e}", exc_info=True)
            return None

    async def fetch_current_price(self, symbol: str, candlestick_api=None) -> Optional[float]:
        """
        Fetch current price for a symbol (from most recent candle or price API)

        Args:
            symbol: Pacifica symbol (e.g., "SOL")
            candlestick_api: Ignored (for API compatibility)

        Returns:
            Current price or None if unavailable
        """
        try:
            # Try price API first
            url = f"{self.base_url}/price"
            params = {'symbol': symbol}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result and 'data' in result:
                            price = result['data'].get('price')
                            if price:
                                return float(price)

            # Fallback: get from 1m candle
            kline_df = await self.fetch_kline(symbol, interval="1m", limit=1)
            if kline_df is not None and not kline_df.empty:
                return float(kline_df.iloc[-1]['close'])

            logger.warning(f"Price fetch failed for {symbol}")
            return None

        except Exception as e:
            logger.error(f"Price fetch error for {symbol}: {e}")
            return None

    async def fetch_funding_rate(self, symbol: str, funding_api=None) -> Optional[float]:
        """
        Fetch current funding rate for a symbol

        Args:
            symbol: Pacifica symbol (e.g., "SOL")
            funding_api: Ignored (for API compatibility)

        Returns:
            Funding rate as decimal (e.g., 0.0001 = 0.01%)
        """
        try:
            # Pacifica funding rate API (if available)
            url = f"{self.base_url}/funding"
            params = {'symbol': symbol}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result and 'data' in result:
                            rate = result['data'].get('funding_rate')
                            if rate is not None:
                                return float(rate)

            # Funding rates not critical - return None if unavailable
            return None

        except Exception as e:
            logger.debug(f"Funding rate fetch failed for {symbol}: {e}")
            return None

    async def fetch_market_data(
        self,
        symbol: str,
        interval: str = "15m",
        limit: int = 100,
        candlestick_api=None,
        funding_api=None
    ) -> Optional[Dict]:
        """
        Fetch comprehensive market data for a symbol

        Args:
            symbol: Pacifica symbol (e.g., "SOL")
            interval: Candle interval (default: 15m)
            limit: Number of candles (default: 100)
            candlestick_api: Ignored (for API compatibility)
            funding_api: Ignored (for API compatibility)

        Returns:
            Dict with keys: symbol, kline_df, funding_rate, current_price
        """
        kline_df = await self.fetch_kline(symbol, interval, limit)
        funding_rate = await self.fetch_funding_rate(symbol)
        current_price = await self.fetch_current_price(symbol) if kline_df is None or kline_df.empty else None

        return {
            "symbol": symbol,
            "kline_df": kline_df,
            "funding_rate": funding_rate,
            "current_price": current_price
        }

    async def fetch_all_markets(
        self,
        symbols: Optional[List[str]] = None,
        interval: str = "15m",
        limit: int = 100,
        candlestick_api=None,
        funding_api=None
    ) -> Dict[str, Dict]:
        """
        Fetch market data for all Pacifica markets

        Args:
            symbols: List of symbols to fetch (default: all Pacifica markets from API)
            interval: Candle interval (default: 15m)
            limit: Number of candles (default: 100)
            candlestick_api: Ignored (for API compatibility)
            funding_api: Ignored (for API compatibility)

        Returns:
            Dict mapping symbol -> market data dict
        """
        # Ensure symbols are initialized
        await self._initialize_symbols()

        if symbols is None:
            symbols = self.available_symbols
        else:
            # Filter to only Pacifica markets (from API)
            symbols = [s for s in symbols if s in self.available_symbols]

        results = {}
        for symbol in symbols:
            data = await self.fetch_market_data(
                symbol,
                interval,
                limit
            )
            if data and data.get('kline_df') is not None:
                results[symbol] = data

        logger.info(f"✅ Fetched data for {len(results)}/{len(symbols)} Pacifica markets")
        return results
