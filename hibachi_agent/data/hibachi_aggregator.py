"""
Hibachi Market Data Aggregator
Uses Hibachi DEX data

Symbols fetched dynamically from Hibachi API via SDK
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
from hibachi_agent.data.hibachi_fetcher import HibachiDataFetcher

logger = logging.getLogger(__name__)

# WHITELIST: Low-liquidity pairs for Strategy G
# Based on 2026-01-02 analysis:
#   - BTC/ETH lost $116 in 7 days with 20% win rate + $51 fees
#   - Pivoting to low-liq pairs where retail hasn't priced in moves
#   - Avoiding majors (BTC, ETH, SOL) - too efficient
# Strategy G: Low-Liquidity Momentum Hunter
WHITELISTED_SYMBOLS = {
    # Tier 1: Newest/Most Volatile
    "HYPE/USDT-P", "PUMP/USDT-P", "VIRTUAL/USDT-P",
    "ENA/USDT-P", "PROVE/USDT-P", "XPL/USDT-P",
    # Tier 2: Mid-Volatility
    "DOGE/USDT-P", "SEI/USDT-P", "SUI/USDT-P",
    "BNB/USDT-P", "ZEC/USDT-P", "XRP/USDT-P"
}


class HibachiMarketDataAggregator:
    """
    Market data aggregator for Hibachi DEX
    Uses Hibachi API for OHLCV data
    Symbols fetched dynamically from API
    """

    def __init__(
        self,
        cambrian_api_key: str,
        sdk=None,
        interval: str = "5m",  # 5m candles for HF scalping (was 15m)
        candle_limit: int = 100,
        macro_refresh_hours: int = 12
    ):
        """
        Initialize Hibachi market data aggregator

        Args:
            cambrian_api_key: Cambrian API key for Deep42 (macro context only)
            sdk: HibachiSDK instance for fetching market metadata
            interval: Candle interval (default: 5m for HF scalping)
            candle_limit: Number of candles to fetch (default: 100)
            macro_refresh_hours: Hours between macro context refreshes (default: 12)
        """
        self.interval = interval
        self.candle_limit = candle_limit

        # Hibachi data fetcher with SDK
        self.hibachi = HibachiDataFetcher(sdk=sdk)

        # Shared components (macro context, indicators, OI)
        self.macro_fetcher = MacroContextFetcher(
            cambrian_api_key=cambrian_api_key,
            refresh_interval_hours=macro_refresh_hours
        )
        self.indicator_calc = IndicatorCalculator()
        self.oi_fetcher = OIDataFetcher()

        logger.info(f"✅ HibachiMarketDataAggregator initialized (interval={interval}, candles={candle_limit})")

    @property
    def hibachi_markets(self) -> List[str]:
        """
        Get list of available Hibachi markets from fetcher
        WHITELIST: Only ETH, BTC (SOL blocked due to consistent losses)

        Returns:
            List of symbol strings
        """
        all_symbols = self.hibachi.available_symbols
        # WHITELIST mode: only trade specific symbols
        filtered = [s for s in all_symbols if s in WHITELISTED_SYMBOLS]
        symbol_names = [s.split('/')[0] for s in filtered]
        logger.info(f"Whitelist active: trading only {len(filtered)} symbols ({', '.join(symbol_names)})")
        return filtered

    async def fetch_market_data(self, symbol: str) -> Optional[Dict]:
        """
        Fetch comprehensive market data for a single Hibachi symbol (async)

        Args:
            symbol: Hibachi symbol (e.g., "SOL/USDT-P")

        Returns:
            Dict with all market data, or None if symbol not available
        """
        # Check if symbol is available on Hibachi
        if symbol not in self.hibachi_markets:
            logger.warning(f"Symbol {symbol} not available on Hibachi (available: {', '.join(self.hibachi_markets)})")
            return None

        # Fetch Hibachi data
        hibachi_data = await self.hibachi.fetch_market_data(
            symbol=symbol,
            interval=self.interval,
            limit=self.candle_limit
        )

        if not hibachi_data:
            logger.warning(f"No data returned from Hibachi for {symbol}")
            return None

        kline_df = hibachi_data['kline_df']
        funding_rate = hibachi_data['funding_rate']
        current_price = hibachi_data['current_price']

        # Calculate indicators if we have kline data
        if kline_df is not None and not kline_df.empty:
            kline_df = self.indicator_calc.calculate_all_indicators(kline_df)
            indicators = self.indicator_calc.get_latest_values(kline_df)
            volume_24h = self._calculate_24h_volume(kline_df)
        else:
            # No kline data - use current price only
            indicators = {'price': current_price}
            volume_24h = None

        # Fetch OI (may not be available for all Hibachi markets)
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
        Fetch market data for all Hibachi markets (async)

        Args:
            symbols: List of symbols (default: all Hibachi markets)

        Returns:
            Dict mapping symbol -> market data dict
        """
        # Try to initialize symbols if not already done (handles rate limit recovery)
        if not self.hibachi.available_symbols:
            logger.info("🔄 Attempting to initialize Hibachi symbols...")
            await self.hibachi._initialize_symbols()

        if symbols is None:
            symbols = self.hibachi_markets

            # Focus on top crypto markets (Hibachi has 15 total)
            # All Hibachi markets are crypto, no need to filter forex/commodities
            logger.info(f"🔍 Using all {len(symbols)} Hibachi crypto markets")
        else:
            # Filter to only Hibachi markets
            symbols = [s for s in symbols if s in self.hibachi_markets]
            if not symbols:
                logger.warning(f"No valid Hibachi symbols in provided list")
                return {}

        # Use fetcher's async method
        results = await self.hibachi.fetch_all_markets(
            symbols=symbols,
            interval=self.interval,
            limit=self.candle_limit
        )

        # Process each result to add indicators
        for symbol, data in results.items():
            kline_df = data.get('kline_df')
            if kline_df is not None and not kline_df.empty:
                kline_df = self.indicator_calc.calculate_all_indicators(kline_df)
                indicators = self.indicator_calc.get_latest_values(kline_df)
                volume_24h = self._calculate_24h_volume(kline_df)
            else:
                # No kline data - use current price only
                indicators = {'price': data.get('current_price')}
                volume_24h = None

            oi = self.oi_fetcher.fetch_oi(symbol)

            data['indicators'] = indicators
            data['volume_24h'] = volume_24h
            data['oi'] = oi
            data['price'] = data.get('current_price') or indicators.get('price')
            data['kline_df'] = kline_df

        logger.info(f"✅ Fetched data for {len(results)}/{len(symbols)} Hibachi markets")
        return results

    def get_macro_context(self, force_refresh: bool = False) -> str:
        """Get macro market context"""
        return self.macro_fetcher.get_macro_context(force_refresh=force_refresh)

    def get_directional_bias(self, force_refresh: bool = False) -> str:
        """
        Get Deep42's directional bias for BTC/market (4h cache)
        Returns raw Deep42 response for LLM to interpret
        """
        return self.macro_fetcher.get_btc_health(force_refresh=force_refresh)

    def format_market_table(self, market_data: Dict[str, Dict]) -> str:
        """
        Format market data as table

        Args:
            market_data: Dict from fetch_all_markets()

        Returns:
            Formatted table string
        """
        lines = []
        lines.append("Market Data (Latest):")
        lines.append("Sources: Hibachi DEX (Price), HyperLiquid/Binance (OI), Calculated (Indicators)")
        lines.append(
            f"{'Symbol':<15} {'Price':>12} {'24h Vol':>12} "
            f"{'Funding':>10} {'OI':>15} {'RSI':>6} {'MACD':>8} {'SMA20>50':>10}"
        )
        lines.append("-" * 100)

        for symbol, data in market_data.items():
            if data is None:
                lines.append(f"{symbol:<15} {'N/A':>12}")
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
                f"{symbol:<15} {price_str:>12} {volume_str:>12} "
                f"{funding_str:>10} {oi_str:>15} {rsi_str:>6} {macd_str:>8} {sma_str:>10}"
            )

        return "\n".join(lines)

    def _calculate_24h_volume(self, kline_df) -> Optional[float]:
        """Calculate 24h volume from candles"""
        if kline_df is None or kline_df.empty:
            return None

        # Sum volume from last 24h of candles
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
