"""
Lighter Market Data Aggregator
Uses Lighter DEX data instead of Pacifica

Symbols fetched dynamically from Lighter API via SDK
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta

# Import shared components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from llm_agent.data.macro_fetcher import MacroContextFetcher
from llm_agent.data.indicator_calculator import IndicatorCalculator
from llm_agent.data.oi_fetcher import OIDataFetcher
from lighter_agent.data.lighter_fetcher import LighterDataFetcher

logger = logging.getLogger(__name__)


class LighterMarketDataAggregator:
    """
    Market data aggregator for Lighter DEX
    Uses Lighter API for OHLCV data, not Pacifica
    Symbols fetched dynamically from API
    """

    def __init__(
        self,
        cambrian_api_key: str,
        sdk=None,
        interval: str = "15m",
        candle_limit: int = 100,
        macro_refresh_hours: int = 12
    ):
        """
        Initialize Lighter market data aggregator

        Args:
            cambrian_api_key: Cambrian API key for Deep42 (macro context only)
            sdk: LighterSDK instance for fetching market metadata
            interval: Candle interval (default: 15m)
            candle_limit: Number of candles to fetch (default: 100)
            macro_refresh_hours: Hours between macro context refreshes (default: 12)
        """
        self.interval = interval
        self.candle_limit = candle_limit

        # Lighter data fetcher with SDK for dynamic symbol loading
        self.lighter = LighterDataFetcher(sdk=sdk)

        # Will be set by bot when SDK is initialized
        self.candlestick_api = None
        self.funding_api = None

        # Shared components (macro context, indicators, OI)
        self.macro_fetcher = MacroContextFetcher(
            cambrian_api_key=cambrian_api_key,
            refresh_interval_hours=macro_refresh_hours  # Note: parameter name is refresh_interval_hours, not refresh_hours
        )
        self.indicator_calc = IndicatorCalculator()
        self.oi_fetcher = OIDataFetcher()

        logger.info(f"✅ LighterMarketDataAggregator initialized (interval={interval}, candles={candle_limit})")

    @property
    def lighter_markets(self) -> List[str]:
        """
        Get list of available Lighter markets from fetcher (loaded dynamically from API)

        Returns:
            List of symbol strings
        """
        return self.lighter.available_symbols

    async def fetch_market_data(self, symbol: str) -> Optional[Dict]:
        """
        Fetch comprehensive market data for a single Lighter symbol (async)

        Args:
            symbol: Lighter symbol (dynamically loaded from API)

        Returns:
            Dict with all market data, or None if symbol not available on Lighter
        """
        # Check if symbol is available on Lighter (from API)
        if symbol not in self.lighter_markets:
            logger.warning(f"Symbol {symbol} not available on Lighter (available: {', '.join(self.lighter_markets)})")
            return None

        # Fetch Lighter data (not Pacifica!) - requires SDK
        if not self.candlestick_api:
            logger.warning(f"CandlestickApi not initialized - cannot fetch data for {symbol}")
            return None

        lighter_data = await self.lighter.fetch_market_data(
            symbol=symbol,
            interval=self.interval,
            limit=self.candle_limit,
            candlestick_api=self.candlestick_api,
            funding_api=self.funding_api
        )

        if not lighter_data:
            logger.warning(f"No data returned from Lighter for {symbol}")
            return None

        kline_df = lighter_data['kline_df']
        funding_rate = lighter_data['funding_rate']
        current_price = lighter_data['current_price']

        # Calculate indicators
        if kline_df is not None and not kline_df.empty:
            kline_df = self.indicator_calc.calculate_all_indicators(kline_df)
            indicators = self.indicator_calc.get_latest_values(kline_df)

            # Calculate 24h volume from recent candles
            volume_24h = self._calculate_24h_volume(kline_df)
        else:
            indicators = {}
            volume_24h = None

        # Fetch OI (may not be available for all Lighter markets)
        oi = self.oi_fetcher.fetch_oi(symbol)

        return {
            "symbol": symbol,
            "price": current_price or indicators.get('price'),
            "volume_24h": volume_24h,
            "funding_rate": funding_rate,
            "oi": oi,
            "indicators": indicators,
            "kline_df": kline_df
        }

    async def fetch_all_markets(self, symbols: Optional[List[str]] = None) -> Dict[str, Dict]:
        """
        Fetch market data for all Lighter markets (async)

        Args:
            symbols: List of symbols (default: all Lighter markets from API)

        Returns:
            Dict mapping symbol -> market data dict
        """
        if symbols is None:
            symbols = self.lighter_markets

            # LIQUIDITY FILTER: Only trade high-volume crypto, exclude illiquid forex/commodities
            # Forex pairs (low liquidity on Lighter)
            forex_pairs = ['USDCAD', 'USDCHF', 'GBPUSD', 'EURUSD', 'USDJPY', 'AUDUSD', 'NZDUSD']
            # Commodities (low liquidity)
            commodities = ['XAU', 'XAG', 'PAXG', 'OIL', 'GAS']
            # Obscure low-volume tokens
            low_volume = ['VIRTUAL', 'ASTER', 'XPL', 'CHEEMS', 'CLOUD', 'FARTCOIN']

            excluded = set(forex_pairs + commodities + low_volume)
            symbols = [s for s in symbols if s not in excluded]

            logger.info(f"🔍 Liquidity filter: {len(self.lighter_markets)} total markets → {len(symbols)} liquid crypto markets (excluded {len(excluded)} illiquid)")
        else:
            # Filter to only Lighter markets (from API)
            symbols = [s for s in symbols if s in self.lighter_markets]
            if not symbols:
                logger.warning(f"No valid Lighter symbols in provided list")
                return {}

        if not self.candlestick_api:
            logger.warning("CandlestickApi not initialized - cannot fetch market data")
            return {}

        # Use fetcher's async method
        results = await self.lighter.fetch_all_markets(
            symbols=symbols,
            interval=self.interval,
            limit=self.candle_limit,
            candlestick_api=self.candlestick_api,
            funding_api=self.funding_api
        )

        # Process each result to add indicators
        for symbol, data in results.items():
            kline_df = data.get('kline_df')
            if kline_df is not None and not kline_df.empty:
                kline_df = self.indicator_calc.calculate_all_indicators(kline_df)
                indicators = self.indicator_calc.get_latest_values(kline_df)
                volume_24h = self._calculate_24h_volume(kline_df)
                oi = self.oi_fetcher.fetch_oi(symbol)
                
                data['indicators'] = indicators
                data['volume_24h'] = volume_24h
                data['oi'] = oi
                data['price'] = data.get('current_price') or indicators.get('price')
                data['kline_df'] = kline_df

        logger.info(f"✅ Fetched data for {len(results)}/{len(symbols)} Lighter markets")
        return results

    def get_macro_context(self, force_refresh: bool = False) -> str:
        """Get macro market context (same as Pacifica aggregator)"""
        return self.macro_fetcher.get_macro_context(force_refresh=force_refresh)

    def format_market_table(self, market_data: Dict[str, Dict]) -> str:
        """
        Format market data as table (same format as Pacifica aggregator)

        Args:
            market_data: Dict from fetch_all_markets()

        Returns:
            Formatted table string
        """
        lines = []
        lines.append("Market Data (Latest):")
        lines.append("Sources: Lighter DEX (Price, Volume, Funding), HyperLiquid/Binance (OI), Calculated (Indicators)")
        lines.append(
            f"{'Symbol':<10} {'Price':>12} {'24h Vol':>12} "
            f"{'Funding':>10} {'OI':>15} {'RSI':>6} {'MACD':>8} {'SMA20>50':>10}"
        )
        lines.append("-" * 95)

        for symbol, data in market_data.items():
            if data is None:
                lines.append(f"{symbol:<10} {'N/A':>12}")
                continue

            price = data.get('price', 0)
            volume = data.get('volume_24h', 0)
            funding = data.get('funding_rate', 0)
            oi = data.get('oi')
            indicators = data.get('indicators', {})

            rsi = indicators.get('rsi', 0)
            macd_diff = indicators.get('macd_diff', 0)
            sma_20_above_50 = indicators.get('sma_20_above_50', False)

            price_str = f"${price:,.2f}" if price else "N/A"
            volume_str = f"${volume/1000:.0f}K" if volume else "N/A"
            funding_str = f"{funding*100:.4f}%" if funding else "N/A"
            oi_str = f"{oi:,.0f}" if oi else "N/A"
            rsi_str = f"{rsi:.0f}" if rsi else "N/A"
            macd_str = f"{macd_diff:+.1f}" if macd_diff is not None else "N/A"
            sma_str = "Yes" if sma_20_above_50 else "No"

            lines.append(
                f"{symbol:<10} {price_str:>12} {volume_str:>12} "
                f"{funding_str:>10} {oi_str:>15} {rsi_str:>6} {macd_str:>8} {sma_str:>10}"
            )

        return "\n".join(lines)

    def _calculate_24h_volume(self, kline_df) -> Optional[float]:
        """Calculate 24h volume from candles (same as Pacifica aggregator)"""
        if kline_df is None or kline_df.empty:
            return None

        # Sum volume from last 24h of candles
        # Assuming 15m candles = 96 candles per day
        # Or use last 24 hours of data
        if 'timestamp' in kline_df.columns and 'volume' in kline_df.columns:
            now = datetime.now()
            cutoff = now - timedelta(hours=24)
            
            # Filter candles within last 24h
            recent_candles = kline_df[kline_df['timestamp'] >= cutoff]
            if not recent_candles.empty:
                volume_sum = recent_candles['volume'].sum()
                # Get average price for USD conversion
                avg_price = recent_candles['close'].mean()
                if avg_price > 0:
                    return float(volume_sum * avg_price)
            
            # Fallback: use last 96 candles (24h of 15m candles)
            last_96 = kline_df.tail(96)
            if not last_96.empty and 'close' in last_96.columns:
                volume_sum = last_96['volume'].sum()
                avg_price = last_96['close'].mean()
                if avg_price > 0:
                    return float(volume_sum * avg_price)

        return None

