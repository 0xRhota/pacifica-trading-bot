"""
Market Data Aggregator
Orchestrates all data sources and combines them into a unified market state

Phase 1 deliverable: Fetch and format market data for ALL 28 Pacifica perpetuals

Usage:
    from llm_agent.data import MarketDataAggregator

    aggregator = MarketDataAggregator(
        cambrian_api_key="your_key"
    )

    # Fetch all market data
    market_state = aggregator.fetch_all_markets()

    # Print formatted table
    print(aggregator.format_market_table(market_state))
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd

from .pacifica_fetcher import PacificaDataFetcher
from .oi_fetcher import OIDataFetcher
from .macro_fetcher import MacroContextFetcher
from .indicator_calculator import IndicatorCalculator

logger = logging.getLogger(__name__)


class MarketDataAggregator:
    """Orchestrates all data sources for LLM trading agent
    
    NOTE (2025-11-03): Cambrian candlestick/OHLCV data is DISABLED.
    - Candlestick data: Pacifica API only (via PacificaDataFetcher)
    - Cambrian usage: Deep42 analysis only (macro context, NOT candlestick data)
    - RBI agent: Uses Cambrian for backtesting (separate system)
    """

    def __init__(
        self,
        cambrian_api_key: str,
        interval: str = "15m",
        candle_limit: int = 100,
        macro_refresh_hours: int = 12
    ):
        """
        Initialize market data aggregator

        Args:
            cambrian_api_key: Cambrian API key for macro context (Deep42 only, NOT candlestick data)
            interval: Candle interval for technical analysis (default: 15m)
            candle_limit: Number of candles to fetch (default: 100)
            macro_refresh_hours: Macro context refresh interval (default: 12)
        """
        self.interval = interval
        self.candle_limit = candle_limit

        # Initialize fetchers
        # NOTE: Pacifica is the ONLY source for candlestick/OHLCV data
        self.pacifica = PacificaDataFetcher()
        self.oi_fetcher = OIDataFetcher()
        # Cambrian used ONLY for Deep42 (market intelligence), NOT candlestick data
        self.macro_fetcher = MacroContextFetcher(
            cambrian_api_key=cambrian_api_key,
            refresh_interval_hours=macro_refresh_hours
        )
        self.indicator_calc = IndicatorCalculator()

        logger.info(f"✅ MarketDataAggregator initialized (interval={interval}, candles={candle_limit})")

    def fetch_market_data(self, symbol: str) -> Dict:
        """
        Fetch comprehensive market data for a single symbol

        Args:
            symbol: Pacifica symbol (e.g., "SOL")

        Returns:
            Dict with all market data:
                - symbol: str
                - price: float
                - volume_24h: float
                - funding_rate: float
                - oi: Optional[float]
                - indicators: dict (RSI, MACD, SMA, etc.)
                - kline_df: pd.DataFrame (raw OHLCV with indicators)
        """
        # Fetch Pacifica data (ONLY source for candlestick/OHLCV data)
        # NOTE: Cambrian candlestick data is disabled - see class docstring
        pacifica_data = self.pacifica.fetch_market_data(
            symbol=symbol,
            interval=self.interval,
            limit=self.candle_limit
        )

        kline_df = pacifica_data['kline_df']
        funding_rate = pacifica_data['funding_rate']
        current_price = pacifica_data['current_price']

        # Calculate indicators
        if kline_df is not None and not kline_df.empty:
            kline_df = self.indicator_calc.calculate_all_indicators(kline_df)
            indicators = self.indicator_calc.get_latest_values(kline_df)

            # Calculate 24h volume from recent candles
            volume_24h = self._calculate_24h_volume(kline_df)
        else:
            indicators = {}
            volume_24h = None

        # Fetch OI
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

    def fetch_all_markets(self, symbols: Optional[List[str]] = None) -> Dict[str, Dict]:
        """
        Fetch market data for all symbols

        Args:
            symbols: List of symbols (default: all 28 Pacifica markets)

        Returns:
            Dict mapping symbol → market data
        """
        if symbols is None:
            symbols = self.pacifica.AVAILABLE_SYMBOLS

        logger.info(f"Fetching market data for {len(symbols)} symbols...")

        # Fetch Pacifica data for all markets
        results = {}
        for symbol in symbols:
            try:
                results[symbol] = self.fetch_market_data(symbol)
            except Exception as e:
                logger.error(f"Failed to fetch data for {symbol}: {e}")
                results[symbol] = None

        logger.info(f"✅ Fetched data for {len(results)} markets")
        return results

    def get_macro_context(self, force_refresh: bool = False) -> str:
        """
        Get cached macro context (or refresh if needed)

        Args:
            force_refresh: Force refresh even if cache is valid

        Returns:
            Formatted macro context string for LLM prompt
        """
        return self.macro_fetcher.get_macro_context(force_refresh=force_refresh)

    def format_market_table(self, market_data: Dict[str, Dict]) -> str:
        """
        Format market data as a readable table for LLM prompt

        Args:
            market_data: Dict from fetch_all_markets()

        Returns:
            Formatted table string
        """
        lines = []
        lines.append("Market Data (Latest):")
        lines.append("Sources: Pacifica DEX (Price, Volume, Funding), HyperLiquid/Binance (OI), Calculated (Indicators)")
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

            # Format values
            # Use dynamic decimal places for price based on magnitude
            if price:
                if price < 0.01:
                    price_str = f"${price:.6f}"  # 6 decimals for sub-cent (e.g., $0.004400)
                elif price < 1:
                    price_str = f"${price:.4f}"  # 4 decimals for sub-dollar (e.g., $0.1234)
                else:
                    price_str = f"${price:,.2f}"  # 2 decimals for normal prices (e.g., $123.45)
            else:
                price_str = "N/A"

            volume_str = self._format_volume(volume) if volume else "N/A"
            funding_str = f"{funding * 100:.4f}%" if funding else "N/A"
            oi_str = f"{oi:,.0f}" if oi else "N/A"
            rsi_str = f"{rsi:.0f}" if rsi else "N/A"
            macd_str = f"{'+' if macd_diff > 0 else ''}{macd_diff:.1f}" if macd_diff else "N/A"
            sma_str = "Yes" if sma_20_above_50 else "No"

            lines.append(
                f"{symbol:<10} {price_str:>12} {volume_str:>12} "
                f"{funding_str:>10} {oi_str:>15} {rsi_str:>6} {macd_str:>8} {sma_str:>10}"
            )

        return "\n".join(lines)

    def _calculate_24h_volume(self, df: pd.DataFrame) -> Optional[float]:
        """Calculate 24h volume from recent candles"""
        if df is None or df.empty:
            return None

        # Get candles from last 24 hours
        now = datetime.now()
        cutoff = now - pd.Timedelta(hours=24)

        recent = df[df['timestamp'] >= cutoff]
        if recent.empty:
            return None

        return recent['volume'].sum()

    @staticmethod
    def _format_volume(volume: float) -> str:
        """Format volume with appropriate suffix (K, M, B)"""
        if volume >= 1e9:
            return f"${volume / 1e9:.2f}B"
        elif volume >= 1e6:
            return f"${volume / 1e6:.2f}M"
        elif volume >= 1e3:
            return f"${volume / 1e3:.0f}K"
        else:
            return f"${volume:.0f}"
