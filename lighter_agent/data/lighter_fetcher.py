"""
Lighter DEX Data Fetcher
Pure Lighter SDK implementation - no Pacifica dependencies

Symbols fetched dynamically from Lighter API via SDK
"""

import logging
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class LighterDataFetcher:
    """
    Fetch market data from Lighter DEX using Lighter SDK only
    No HTTP requests, no Pacifica patterns
    Symbols and market IDs fetched dynamically from API
    """

    def __init__(self, sdk=None):
        """
        Initialize Lighter data fetcher

        Args:
            sdk: LighterSDK instance for fetching market metadata
        """
        self.sdk = sdk
        self.available_symbols = []  # Will be populated from API
        self.market_ids = {}  # Will be populated from API
        self._initialized = False

    async def _initialize_symbols(self):
        """
        Initialize available symbols and market IDs from SDK

        This is called automatically the first time data is fetched
        """
        if self._initialized or not self.sdk:
            return

        # Fetch symbols from SDK (which gets them from API)
        self.available_symbols = await self.sdk.get_all_market_symbols()

        # Build market_id mapping
        for symbol in self.available_symbols:
            market_id = await self.sdk.get_market_id_for_symbol(symbol)
            if market_id:
                self.market_ids[symbol] = market_id

        self._initialized = True
        logger.info(f"✅ Initialized Lighter fetcher with {len(self.available_symbols)} markets from API: {self.available_symbols}")

    async def fetch_kline(
        self,
        symbol: str,
        interval: str = "15m",
        limit: int = 100,
        candlestick_api=None
    ) -> Optional[pd.DataFrame]:
        """
        Fetch kline (OHLCV) data for a symbol using Lighter SDK

        Args:
            symbol: Trading symbol (e.g., "SOL")
            interval: Candle interval (must be: "1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d", "1w")
            limit: Number of candles to fetch
            candlestick_api: Lighter CandlestickApi instance (required)

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        # Ensure symbols are initialized
        await self._initialize_symbols()

        market_id = self.market_ids.get(symbol)
        if not market_id:
            logger.warning(f"Market ID not found for {symbol} (available: {self.available_symbols})")
            return None

        if not candlestick_api:
            logger.warning(f"Lighter CandlestickApi not provided - cannot fetch data for {symbol}")
            return None

        try:
            # Resolution must be lowercase: "1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d", "1w"
            valid_resolutions = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d", "1w"]
            resolution = interval if interval in valid_resolutions else "15m"
            
            # Calculate timestamps (milliseconds)
            end_timestamp = int(time.time() * 1000)
            interval_minutes = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "12h": 720, "1d": 1440, "1w": 10080}.get(interval, 15)
            start_timestamp = end_timestamp - (limit * interval_minutes * 60 * 1000)
            
            # Call Lighter SDK
            result = await candlestick_api.candlesticks(
                market_id=market_id,
                resolution=resolution,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                count_back=limit
            )

            if not result or not hasattr(result, 'candlesticks') or not result.candlesticks:
                logger.warning(f"No candlestick data returned for {symbol}")
                return None

            # Parse result.candlesticks (list of Candlestick objects)
            candles = result.candlesticks
            
            # Convert to list of dicts
            data = []
            for candle in candles:
                data.append({
                    'timestamp': candle.timestamp,
                    'open': float(candle.open),
                    'high': float(candle.high),
                    'low': float(candle.low),
                    'close': float(candle.close),
                    'volume': float(candle.volume1) if hasattr(candle, 'volume1') else float(candle.volume0)  # Use USD volume (volume1)
                })
            
            # Create DataFrame
            df = pd.DataFrame(data)
            
            # Convert timestamp to datetime (milliseconds)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce')
            
            # Sort by timestamp
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            logger.info(f"✅ Fetched {len(df)} candles for {symbol} ({resolution}) from Lighter")
            return df

        except Exception as e:
            logger.error(f"Error fetching Lighter kline for {symbol}: {e}", exc_info=True)
            return None

    async def fetch_current_price(self, symbol: str, candlestick_api=None) -> Optional[float]:
        """
        Fetch current price for a symbol (from most recent candle)
        
        Args:
            symbol: Lighter symbol (e.g., "SOL")
            candlestick_api: Lighter CandlestickApi instance (required)
        
        Returns:
            Current price or None if unavailable
        """
        try:
            kline_df = await self.fetch_kline(symbol, interval="1m", limit=1, candlestick_api=candlestick_api)
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
            symbol: Lighter symbol (e.g., "SOL")
            funding_api: Lighter FundingApi instance (optional)

        Returns:
            Funding rate as decimal (e.g., 0.0001 = 0.01%)
        """
        if not funding_api:
            # Funding rates not critical - return None if API not available
            return None

        # Ensure symbols are initialized
        await self._initialize_symbols()

        market_id = self.market_ids.get(symbol)
        if not market_id:
            return None

        try:
            result = await funding_api.funding_rates(market_id=market_id)
            if result and hasattr(result, 'funding_rate'):
                return float(result.funding_rate)
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
            symbol: Lighter symbol (e.g., "SOL")
            interval: Candle interval (default: 15m)
            limit: Number of candles (default: 100)
            candlestick_api: Lighter CandlestickApi instance (required)
            funding_api: Lighter FundingApi instance (optional)
        
        Returns:
            Dict with keys: symbol, kline_df, funding_rate, current_price
        """
        kline_df = await self.fetch_kline(symbol, interval, limit, candlestick_api)
        funding_rate = await self.fetch_funding_rate(symbol, funding_api) if funding_api else None
        current_price = await self.fetch_current_price(symbol, candlestick_api) if candlestick_api else None

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
        Fetch market data for all Lighter markets

        Args:
            symbols: List of symbols to fetch (default: all Lighter markets from API)
            interval: Candle interval (default: 15m)
            limit: Number of candles (default: 100)
            candlestick_api: Lighter CandlestickApi instance (required)
            funding_api: Lighter FundingApi instance (optional)

        Returns:
            Dict mapping symbol -> market data dict
        """
        # Ensure symbols are initialized
        await self._initialize_symbols()

        if symbols is None:
            symbols = self.available_symbols
        else:
            # Filter to only Lighter markets (from API)
            symbols = [s for s in symbols if s in self.available_symbols]

        results = {}
        for symbol in symbols:
            data = await self.fetch_market_data(
                symbol,
                interval,
                limit,
                candlestick_api=candlestick_api,
                funding_api=funding_api
            )
            if data and data.get('kline_df') is not None:
                results[symbol] = data

        logger.info(f"✅ Fetched data for {len(results)}/{len(symbols)} Lighter markets")
        return results
