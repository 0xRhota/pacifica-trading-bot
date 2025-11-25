"""
Binance Futures Data Proxy for Hibachi
Uses Binance Futures API to fetch klines and funding rates as proxy data for Hibachi trading.

Since Hibachi doesn't provide historical candles or funding rates, we use Binance as a proxy
since both exchanges trade the same underlying assets (BTC, ETH, SOL, etc.).
"""

import logging
import aiohttp
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class BinanceFuturesProxy:
    """
    Fetch market data from Binance Futures as proxy for Hibachi DEX

    Binance provides:
    - Klines (OHLCV candles) for technical indicators
    - Funding rates for sentiment/positioning data
    - Mark prices for reference
    """

    BINANCE_FUTURES_URL = "https://fapi.binance.com"

    # Mapping: Hibachi symbol → Binance Futures symbol
    SYMBOL_MAP = {
        'BTC/USDT-P': 'BTCUSDT',
        'ETH/USDT-P': 'ETHUSDT',
        'SOL/USDT-P': 'SOLUSDT',
        'SUI/USDT-P': 'SUIUSDT',
        'XRP/USDT-P': 'XRPUSDT',
        'DOGE/USDT-P': 'DOGEUSDT',
        'BNB/USDT-P': 'BNBUSDT',
        'HYPE/USDT-P': 'HYPEUSDT',
        'VIRTUAL/USDT-P': 'VIRTUALUSDT',
        'SEI/USDT-P': 'SEIUSDT',
        'PUMP/USDT-P': 'PUMPUSDT',
        'PROVE/USDT-P': 'PROVEUSDT',
        'ENA/USDT-P': 'ENAUSDT',
        'XPL/USDT-P': 'XPLUSDT',
        'ZEC/USDT-P': 'ZECUSDT',
    }

    # Reverse mapping: Binance → Hibachi
    REVERSE_MAP = {v: k for k, v in SYMBOL_MAP.items()}

    def __init__(self):
        """Initialize Binance Futures proxy"""
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the session"""
        if self._session and not self._session.closed:
            await self._session.close()

    def hibachi_to_binance(self, hibachi_symbol: str) -> Optional[str]:
        """
        Convert Hibachi symbol to Binance Futures symbol

        Args:
            hibachi_symbol: e.g., 'BTC/USDT-P'

        Returns:
            Binance symbol e.g., 'BTCUSDT' or None if not mapped
        """
        # Try direct lookup first
        if hibachi_symbol in self.SYMBOL_MAP:
            return self.SYMBOL_MAP[hibachi_symbol]

        # Try to construct: 'XXX/USDT-P' → 'XXXUSDT'
        if '/USDT-P' in hibachi_symbol:
            base = hibachi_symbol.split('/')[0]
            return f"{base}USDT"

        return None

    async def fetch_klines(
        self,
        hibachi_symbol: str,
        interval: str = "15m",
        limit: int = 100
    ) -> Optional[pd.DataFrame]:
        """
        Fetch kline (OHLCV) data from Binance Futures

        Args:
            hibachi_symbol: Hibachi symbol (e.g., 'SOL/USDT-P')
            interval: Candle interval (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Number of candles (max 1500)

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        binance_symbol = self.hibachi_to_binance(hibachi_symbol)
        if not binance_symbol:
            logger.warning(f"No Binance mapping for Hibachi symbol: {hibachi_symbol}")
            return None

        try:
            session = await self._get_session()
            url = f"{self.BINANCE_FUTURES_URL}/fapi/v1/klines"
            params = {
                'symbol': binance_symbol,
                'interval': interval,
                'limit': min(limit, 1500)
            }

            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    logger.error(f"Binance klines error {resp.status}: {error}")
                    return None

                data = await resp.json()

                if not data:
                    return None

                # Parse Binance kline format:
                # [open_time, open, high, low, close, volume, close_time, ...]
                df = pd.DataFrame(data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])

                # Convert to numeric
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df['open'] = pd.to_numeric(df['open'])
                df['high'] = pd.to_numeric(df['high'])
                df['low'] = pd.to_numeric(df['low'])
                df['close'] = pd.to_numeric(df['close'])
                df['volume'] = pd.to_numeric(df['volume'])

                # Keep only needed columns
                df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

                logger.debug(f"Fetched {len(df)} klines for {hibachi_symbol} via Binance")
                return df

        except Exception as e:
            logger.error(f"Error fetching Binance klines for {hibachi_symbol}: {e}")
            return None

    async def fetch_funding_rate(self, hibachi_symbol: str) -> Optional[Dict]:
        """
        Fetch current funding rate from Binance Futures

        Args:
            hibachi_symbol: Hibachi symbol (e.g., 'BTC/USDT-P')

        Returns:
            Dict with:
                - funding_rate: Current funding rate (as decimal, e.g., 0.0001 = 0.01%)
                - funding_rate_pct: Funding rate as percentage string
                - mark_price: Current mark price
                - index_price: Current index price
                - next_funding_time: Timestamp of next funding
        """
        binance_symbol = self.hibachi_to_binance(hibachi_symbol)
        if not binance_symbol:
            logger.warning(f"No Binance mapping for Hibachi symbol: {hibachi_symbol}")
            return None

        try:
            session = await self._get_session()
            url = f"{self.BINANCE_FUTURES_URL}/fapi/v1/premiumIndex"
            params = {'symbol': binance_symbol}

            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    logger.error(f"Binance funding rate error {resp.status}: {error}")
                    return None

                data = await resp.json()

                funding_rate = float(data.get('lastFundingRate', 0))

                return {
                    'funding_rate': funding_rate,
                    'funding_rate_pct': f"{funding_rate * 100:+.4f}%",
                    'mark_price': float(data.get('markPrice', 0)),
                    'index_price': float(data.get('indexPrice', 0)),
                    'next_funding_time': datetime.fromtimestamp(
                        int(data.get('nextFundingTime', 0)) / 1000
                    ) if data.get('nextFundingTime') else None
                }

        except Exception as e:
            logger.error(f"Error fetching Binance funding rate for {hibachi_symbol}: {e}")
            return None

    async def fetch_all_funding_rates(
        self,
        hibachi_symbols: List[str]
    ) -> Dict[str, Dict]:
        """
        Fetch funding rates for multiple Hibachi symbols

        Args:
            hibachi_symbols: List of Hibachi symbols

        Returns:
            Dict mapping hibachi_symbol → funding rate data
        """
        results = {}

        for symbol in hibachi_symbols:
            data = await self.fetch_funding_rate(symbol)
            if data:
                results[symbol] = data

        return results

    async def fetch_market_data(
        self,
        hibachi_symbol: str,
        interval: str = "15m",
        limit: int = 100
    ) -> Optional[Dict]:
        """
        Fetch comprehensive market data for a Hibachi symbol

        Args:
            hibachi_symbol: Hibachi symbol
            interval: Candle interval
            limit: Number of candles

        Returns:
            Dict with kline_df, funding_rate_data, current_price
        """
        klines = await self.fetch_klines(hibachi_symbol, interval, limit)
        funding = await self.fetch_funding_rate(hibachi_symbol)

        current_price = None
        if klines is not None and len(klines) > 0:
            current_price = float(klines.iloc[-1]['close'])
        elif funding:
            current_price = funding.get('mark_price')

        return {
            'kline_df': klines,
            'funding_rate': funding.get('funding_rate') if funding else None,
            'funding_rate_pct': funding.get('funding_rate_pct') if funding else None,
            'mark_price': funding.get('mark_price') if funding else None,
            'current_price': current_price
        }


# Test function
async def test_binance_proxy():
    """Test Binance proxy functionality"""
    proxy = BinanceFuturesProxy()

    try:
        print("Testing Binance Futures Proxy for Hibachi...")
        print("=" * 60)

        # Test klines
        print("\n1️⃣ Testing klines for SOL/USDT-P...")
        klines = await proxy.fetch_klines('SOL/USDT-P', interval='15m', limit=5)
        if klines is not None:
            print(f"✅ Got {len(klines)} candles")
            print(klines.tail(3).to_string())
        else:
            print("❌ Failed to get klines")

        # Test funding rate
        print("\n2️⃣ Testing funding rate for BTC/USDT-P...")
        funding = await proxy.fetch_funding_rate('BTC/USDT-P')
        if funding:
            print(f"✅ Funding Rate: {funding['funding_rate_pct']}")
            print(f"   Mark Price: ${funding['mark_price']:,.2f}")
            print(f"   Next Funding: {funding['next_funding_time']}")
        else:
            print("❌ Failed to get funding rate")

        # Test all funding rates
        print("\n3️⃣ Testing all funding rates...")
        symbols = ['BTC/USDT-P', 'ETH/USDT-P', 'SOL/USDT-P']
        all_funding = await proxy.fetch_all_funding_rates(symbols)
        for sym, data in all_funding.items():
            print(f"   {sym}: {data['funding_rate_pct']}")

        # Test full market data
        print("\n4️⃣ Testing full market data for ETH/USDT-P...")
        market_data = await proxy.fetch_market_data('ETH/USDT-P', interval='15m', limit=10)
        if market_data:
            print(f"✅ Current Price: ${market_data['current_price']:,.2f}")
            print(f"   Funding Rate: {market_data['funding_rate_pct']}")
            print(f"   Klines: {len(market_data['kline_df'])} candles")

    finally:
        await proxy.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_binance_proxy())
