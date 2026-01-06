"""
Lighter DEX Data Fetcher
Pure Lighter SDK implementation with Cambrian API fallback

Symbols fetched dynamically from Lighter API via SDK
Falls back to Cambrian API for candlestick data when Lighter is geo-blocked
"""

import asyncio
import logging
import pandas as pd
import requests
import os
from typing import Optional, Dict, List
from datetime import datetime
import time
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Cambrian token address mapping for fallback (Solana SPL token addresses)
# Only tokens verified to have active OHLCV data on Cambrian
CAMBRIAN_TOKEN_ADDRESSES = {
    # Major assets
    "SOL": "So11111111111111111111111111111111111111112",
    "ETH": "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",  # Wormhole wETH
    "BTC": "3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh",  # Wormhole wBTC (Portal)
    # Solana ecosystem
    "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
    "PYTH": "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "1000BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # Same as BONK (adjusted in price)
    "WIF": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
    "POPCAT": "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr",
    # DeFi tokens (verified working)
    "UNI": "8FU95xFJhUUkyyCLU13HSzDLs7oC4QZdXQHL6SCeab36",  # Wormhole UNI
}


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
        self._candlesticks_blocked = False  # Track if Lighter candlesticks are geo-blocked
        self._position_prices = {}  # Cache for prices from positions
        self._cambrian_api_key = os.getenv("CAMBRIAN_API_KEY")

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

    def _fetch_cambrian_candlesticks(self, symbol: str, interval: str = "15m", limit: int = 100) -> Optional[pd.DataFrame]:
        """
        Fallback: Fetch candlestick data from Cambrian API when Lighter is blocked

        Args:
            symbol: Trading symbol (e.g., "SOL", "BTC", "ETH")
            interval: Candle interval
            limit: Number of candles

        Returns:
            DataFrame with OHLCV data or None
        """
        if not self._cambrian_api_key:
            logger.warning("CAMBRIAN_API_KEY not set - cannot use fallback")
            return None

        token_address = CAMBRIAN_TOKEN_ADDRESSES.get(symbol)
        if not token_address:
            logger.debug(f"No Cambrian token address for {symbol}")
            return None

        try:
            # Calculate timestamps
            before_time = int(time.time())
            interval_minutes = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "12h": 720, "1d": 1440}.get(interval, 15)
            after_time = before_time - (limit * interval_minutes * 60)

            url = "https://opabinia.cambrian.network/api/v1/solana/ohlcv/token"
            params = {
                "token_address": token_address,
                "after_time": after_time,
                "before_time": before_time,
                "interval": interval
            }
            headers = {
                "X-API-Key": self._cambrian_api_key,
                "Content-Type": "application/json"
            }

            response = requests.get(url, params=params, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Cambrian API error for {symbol}: HTTP {response.status_code}")
                return None

            data = response.json()
            if not data or len(data) == 0:
                return None

            table = data[0]
            columns = [col["name"] for col in table.get("columns", [])]
            rows = table.get("data", [])

            if not rows:
                return None

            df = pd.DataFrame(rows, columns=columns)

            # Standardize column names
            rename_map = {
                "openPrice": "open",
                "highPrice": "high",
                "lowPrice": "low",
                "closePrice": "close",
                "volume": "volume",
                "unixTime": "timestamp"
            }
            for old, new in rename_map.items():
                if old in df.columns:
                    df = df.rename(columns={old: new})

            # Convert types
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
            for col in ["open", "high", "low", "close", "volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            df = df.sort_values("timestamp").reset_index(drop=True)
            logger.info(f"✅ Fetched {len(df)} candles for {symbol} from Cambrian (fallback)")
            return df

        except Exception as e:
            logger.error(f"Cambrian fallback error for {symbol}: {e}")
            return None

    async def update_position_prices(self) -> Dict[str, float]:
        """
        Fetch current prices from account positions
        This works even when candlesticks are blocked

        Returns:
            Dict mapping symbol -> current price
        """
        if not self.sdk:
            return {}

        try:
            positions_result = await self.sdk.get_positions()
            if not positions_result.get('success'):
                return {}

            prices = {}
            for pos in positions_result.get('data', []):
                symbol = pos.get('symbol')
                size = pos.get('size', 0)
                value = pos.get('value', 0)
                if symbol and size > 0:
                    prices[symbol] = value / size

            self._position_prices = prices
            logger.info(f"✅ Updated {len(prices)} prices from positions")
            return prices

        except Exception as e:
            logger.error(f"Error fetching position prices: {e}")
            return {}

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

        # If we know candlesticks are blocked, skip to fallback
        if self._candlesticks_blocked:
            return self._fetch_cambrian_candlesticks(symbol, interval, limit)

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
            error_str = str(e).lower()
            # Detect 403 Forbidden (geo-blocking)
            if '403' in error_str or 'forbidden' in error_str:
                logger.warning(f"⚠️ Lighter candlesticks blocked (403) - switching to Cambrian fallback")
                self._candlesticks_blocked = True
                return self._fetch_cambrian_candlesticks(symbol, interval, limit)

            # Don't log full traceback for 403 errors (expected when geo-blocked)
            logger.debug(f"Error fetching Lighter kline for {symbol}: {e}")
            return None

    async def fetch_current_price(self, symbol: str, candlestick_api=None) -> Optional[float]:
        """
        Fetch current price for a symbol
        Tries: 1) Candlesticks 2) Position data 3) Cached position prices

        Args:
            symbol: Lighter symbol (e.g., "SOL")
            candlestick_api: Lighter CandlestickApi instance (optional)

        Returns:
            Current price or None if unavailable
        """
        try:
            # Try candlesticks first (if not blocked)
            if candlestick_api and not self._candlesticks_blocked:
                kline_df = await self.fetch_kline(symbol, interval="1m", limit=1, candlestick_api=candlestick_api)
                if kline_df is not None and not kline_df.empty:
                    return float(kline_df.iloc[-1]['close'])

            # Fallback to position prices (from account data)
            if symbol in self._position_prices:
                return self._position_prices[symbol]

            # Try to update position prices if we have SDK
            if self.sdk:
                await self.update_position_prices()
                if symbol in self._position_prices:
                    return self._position_prices[symbol]

            # Try Cambrian fallback for major symbols
            if symbol in CAMBRIAN_TOKEN_ADDRESSES:
                df = self._fetch_cambrian_candlesticks(symbol, "1m", 1)
                if df is not None and not df.empty:
                    return float(df.iloc[-1]['close'])

            # Only log warning for symbols that should have Cambrian data
            if symbol in CAMBRIAN_TOKEN_ADDRESSES:
                logger.warning(f"Price fetch failed for {symbol}")
            # Skip logging for symbols without Cambrian mapping (expected behavior)
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

    def get_tradeable_symbols(self) -> List[str]:
        """
        Get list of symbols that can be traded (have data source available)

        When Lighter candlesticks are blocked, only returns symbols with Cambrian mapping

        Returns:
            List of tradeable symbol strings
        """
        if self._candlesticks_blocked:
            # Only return symbols with Cambrian fallback
            return [s for s in self.available_symbols if s in CAMBRIAN_TOKEN_ADDRESSES]
        return self.available_symbols

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

        # Probe for block status if not already known
        if not self._candlesticks_blocked and candlestick_api and self.available_symbols:
            # Try fetching one symbol to detect if Lighter is blocked
            probe_symbol = self.available_symbols[0]
            await self.fetch_kline(probe_symbol, interval, 1, candlestick_api)
            # After probe, _candlesticks_blocked will be set if blocked

        if symbols is None:
            # When candlesticks are blocked, only fetch symbols with Cambrian data
            if self._candlesticks_blocked:
                symbols = self.get_tradeable_symbols()
                logger.info(f"📊 Cambrian fallback active - trading {len(symbols)} supported symbols: {symbols}")
            else:
                symbols = self.available_symbols
        else:
            # Filter to only Lighter markets (from API)
            symbols = [s for s in symbols if s in self.available_symbols]

        results = {}
        for i, symbol in enumerate(symbols):
            data = await self.fetch_market_data(
                symbol,
                interval,
                limit,
                candlestick_api=candlestick_api,
                funding_api=funding_api
            )
            if data and data.get('kline_df') is not None:
                results[symbol] = data

            # Rate limiting: 100ms delay between requests to avoid 429 errors
            if i < len(symbols) - 1:
                await asyncio.sleep(0.1)

        logger.info(f"✅ Fetched data for {len(results)}/{len(symbols)} Lighter markets")
        return results
