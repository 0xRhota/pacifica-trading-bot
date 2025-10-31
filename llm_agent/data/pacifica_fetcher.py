"""
Pacifica Data Fetcher
Fetches OHLCV candles and funding rates from Pacifica API

Usage:
    fetcher = PacificaDataFetcher()
    market_data = fetcher.fetch_market_data(symbol="SOL", interval="15m", limit=100)
    funding_rate = fetcher.fetch_funding_rate(symbol="SOL")
"""

import requests
import logging
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PacificaDataFetcher:
    """Fetch market data from Pacifica API"""

    BASE_URL = "https://api.pacifica.fi/api/v1"

    # All 28 Pacifica perpetuals
    AVAILABLE_SYMBOLS = [
        "ETH", "BTC", "SOL", "PUMP", "XRP", "HYPE", "DOGE", "FARTCOIN",
        "ENA", "BNB", "SUI", "kBONK", "PENGU", "AAVE", "LINK", "kPEPE",
        "LTC", "LDO", "UNI", "CRV", "WLFI", "AVAX", "ASTER", "XPL",
        "2Z", "PAXG", "ZEC", "MON"
    ]

    def __init__(self):
        """Initialize Pacifica data fetcher"""
        self._info_cache: Optional[Dict] = None
        self._info_cache_time: Optional[datetime] = None
        self._info_cache_ttl = timedelta(hours=1)  # Cache /info for 1 hour

    def _get_info_data(self) -> Dict:
        """
        Fetch /info endpoint (cached for 1 hour)

        Returns:
            Dict with market info including funding rates
        """
        # Check cache
        if (self._info_cache is not None and
            self._info_cache_time is not None and
            datetime.now() - self._info_cache_time < self._info_cache_ttl):
            return self._info_cache

        # Fetch fresh data
        try:
            response = requests.get(f"{self.BASE_URL}/info", timeout=5)
            if response.status_code == 200:
                result = response.json()

                # API returns: {"success": true, "data": [...], "error": null}
                if result.get("success") and result.get("data"):
                    data = result["data"]
                    self._info_cache = data
                    self._info_cache_time = datetime.now()
                    logger.info(f"✅ Pacifica /info cached ({len(data)} markets)")
                    return data
                else:
                    logger.warning("Pacifica /info returned no data")
                    return []
            else:
                logger.warning(f"Pacifica /info failed: HTTP {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Pacifica /info error: {e}")
            return []

    def fetch_funding_rate(self, symbol: str) -> Optional[float]:
        """
        Fetch current funding rate for a symbol

        Args:
            symbol: Pacifica symbol (e.g., "SOL")

        Returns:
            Funding rate as decimal (e.g., 0.0001 = 0.01%)
        """
        info_data = self._get_info_data()

        # info_data is a list of market dicts
        for market in info_data:
            if market.get("symbol") == symbol:
                funding_rate = market.get("funding_rate")
                if funding_rate is not None:
                    return float(funding_rate)

        logger.warning(f"Funding rate not found for {symbol}")
        return None

    def fetch_kline(
        self,
        symbol: str,
        interval: str = "15m",
        limit: int = 100
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV candle data from Pacifica

        Args:
            symbol: Pacifica symbol (e.g., "SOL")
            interval: Candle interval (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 8h, 12h, 1d)
            limit: Number of candles to fetch (default: 100)

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        try:
            # Calculate start_time (X candles back from now)
            interval_minutes = self._parse_interval_to_minutes(interval)
            start_time = datetime.now() - timedelta(minutes=interval_minutes * limit)
            start_time_ms = int(start_time.timestamp() * 1000)

            # Fetch data
            params = {
                "symbol": symbol,
                "interval": interval,
                "start_time": start_time_ms,
                "limit": limit
            }

            response = requests.get(f"{self.BASE_URL}/kline", params=params, timeout=10)

            if response.status_code == 200:
                result = response.json()

                # API returns: {"success": true, "data": [...], "error": null}
                if not result.get("success") or not result.get("data"):
                    logger.warning(f"No candles returned for {symbol}")
                    return None

                data = result["data"]

                # Convert to DataFrame
                # API format: {"t": timestamp, "o": open, "h": high, "l": low, "c": close, "v": volume}
                df = pd.DataFrame(data)

                # Rename columns
                df = df.rename(columns={
                    "t": "timestamp",
                    "o": "open",
                    "h": "high",
                    "l": "low",
                    "c": "close",
                    "v": "volume"
                })

                # Ensure proper column types
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df['open'] = df['open'].astype(float)
                df['high'] = df['high'].astype(float)
                df['low'] = df['low'].astype(float)
                df['close'] = df['close'].astype(float)
                df['volume'] = df['volume'].astype(float)

                logger.info(f"✅ Fetched {len(df)} candles for {symbol} ({interval})")
                return df

            else:
                logger.warning(f"Pacifica kline failed for {symbol}: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Pacifica kline error for {symbol}: {e}")
            return None

    def fetch_current_price(self, symbol: str) -> Optional[float]:
        """
        Fetch current price for a symbol (from most recent candle)

        Args:
            symbol: Pacifica symbol (e.g., "SOL")

        Returns:
            Current price or None if unavailable
        """
        # Get most recent candle (1 candle, 1m interval for latest price)
        try:
            kline_df = self.fetch_kline(symbol, interval="1m", limit=1)
            if kline_df is not None and not kline_df.empty:
                return float(kline_df.iloc[-1]['close'])

            logger.warning(f"Price fetch failed for {symbol}")
            return None

        except Exception as e:
            logger.error(f"Price fetch error for {symbol}: {e}")
            return None

    def fetch_market_data(
        self,
        symbol: str,
        interval: str = "15m",
        limit: int = 100
    ) -> Optional[Dict]:
        """
        Fetch comprehensive market data for a symbol

        Args:
            symbol: Pacifica symbol (e.g., "SOL")
            interval: Candle interval (default: 15m)
            limit: Number of candles (default: 100)

        Returns:
            Dict with keys: symbol, kline_df, funding_rate, current_price
        """
        kline_df = self.fetch_kline(symbol, interval, limit)
        funding_rate = self.fetch_funding_rate(symbol)
        current_price = self.fetch_current_price(symbol)

        return {
            "symbol": symbol,
            "kline_df": kline_df,
            "funding_rate": funding_rate,
            "current_price": current_price
        }

    def fetch_all_markets(
        self,
        symbols: Optional[List[str]] = None,
        interval: str = "15m",
        limit: int = 100
    ) -> Dict[str, Dict]:
        """
        Fetch market data for multiple symbols

        Args:
            symbols: List of symbols (default: all 28 Pacifica markets)
            interval: Candle interval (default: 15m)
            limit: Number of candles (default: 100)

        Returns:
            Dict mapping symbol → market data dict
        """
        if symbols is None:
            symbols = self.AVAILABLE_SYMBOLS

        results = {}
        for symbol in symbols:
            results[symbol] = self.fetch_market_data(symbol, interval, limit)

        return results

    @staticmethod
    def _parse_interval_to_minutes(interval: str) -> int:
        """Convert interval string to minutes"""
        mapping = {
            "1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
            "1h": 60, "2h": 120, "4h": 240, "8h": 480, "12h": 720, "1d": 1440
        }
        return mapping.get(interval, 15)
