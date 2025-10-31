"""
Data fetching module for LLM trading agent

Components:
- PacificaDataFetcher: OHLCV and funding rates from Pacifica API
- OIDataFetcher: Open Interest from Binance Futures + HyperLiquid
- MacroContextFetcher: Market context from Deep42 + CoinGecko + Fear & Greed
- IndicatorCalculator: Technical indicators using ta library
- MarketDataAggregator: Orchestrates all data sources
"""

from .oi_fetcher import OIDataFetcher
from .macro_fetcher import MacroContextFetcher
from .pacifica_fetcher import PacificaDataFetcher
from .indicator_calculator import IndicatorCalculator
from .aggregator import MarketDataAggregator

__all__ = [
    'OIDataFetcher',
    'MacroContextFetcher',
    'PacificaDataFetcher',
    'IndicatorCalculator',
    'MarketDataAggregator'
]
