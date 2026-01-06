"""
Paradex DEX Data Fetcher
Fetches market data, orderbook, and positions from Paradex

Zero-fee exchange with tight spreads on major pairs (ETH, BTC, SOL)
Uses ParadexSubkey for authentication (trading-only keys)
"""

import asyncio
import logging
import pandas as pd
import os
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import time
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class ParadexDataFetcher:
    """
    Fetch market data from Paradex DEX
    Uses paradex_py SDK with ParadexSubkey authentication
    """

    def __init__(self, paradex_client=None):
        """
        Initialize Paradex data fetcher

        Args:
            paradex_client: ParadexSubkey instance (initialized externally)
        """
        self.client = paradex_client
        self.available_markets = []
        self.market_info = {}  # Symbol -> market metadata
        self._initialized = False

    async def initialize(self):
        """Initialize markets list from Paradex API"""
        if self._initialized or not self.client:
            return

        try:
            markets_response = self.client.api_client.fetch_markets()
            if markets_response and markets_response.get('results'):
                for market in markets_response['results']:
                    symbol = market.get('symbol')
                    if symbol and symbol.endswith('-USD-PERP'):
                        # Extract base symbol (ETH-USD-PERP -> ETH)
                        base = symbol.replace('-USD-PERP', '')
                        self.available_markets.append(base)
                        self.market_info[base] = {
                            'symbol': symbol,
                            'base_currency': market.get('base_currency'),
                            'quote_currency': market.get('quote_currency'),
                            'min_notional': float(market.get('min_notional', 10)),
                            'max_order_size': float(market.get('max_order_size', 0)),
                            'tick_size': float(market.get('price_tick_size', 0.0001)),
                            'step_size': float(market.get('order_size_increment', 0.0001)),
                        }

            self._initialized = True
            logger.info(f"Initialized Paradex with {len(self.available_markets)} markets")

        except Exception as e:
            logger.error(f"Failed to initialize Paradex markets: {e}")

    def _get_full_symbol(self, symbol: str) -> str:
        """Convert base symbol to full Paradex symbol"""
        if symbol.endswith('-USD-PERP'):
            return symbol
        return f"{symbol}-USD-PERP"

    def fetch_bbo(self, symbol: str) -> Optional[Dict]:
        """
        Fetch best bid/offer for a symbol

        Args:
            symbol: Base symbol (e.g., "ETH") or full symbol (e.g., "ETH-USD-PERP")

        Returns:
            Dict with bid, ask, spread info
        """
        if not self.client:
            return None

        full_symbol = self._get_full_symbol(symbol)

        try:
            bbo = self.client.api_client.fetch_bbo(market=full_symbol)
            if bbo:
                bid = float(bbo.get('bid', 0))
                ask = float(bbo.get('ask', 0))
                spread = ask - bid if bid > 0 and ask > 0 else 0
                spread_pct = (spread / bid * 100) if bid > 0 else 0

                return {
                    'symbol': symbol,
                    'bid': bid,
                    'ask': ask,
                    'spread': spread,
                    'spread_pct': spread_pct,
                    'mid_price': (bid + ask) / 2 if bid > 0 and ask > 0 else 0
                }
            return None

        except Exception as e:
            logger.debug(f"BBO fetch error for {symbol}: {e}")
            return None

    def fetch_orderbook(self, symbol: str, depth: int = 10) -> Optional[Dict]:
        """
        Fetch orderbook for a symbol

        Args:
            symbol: Base symbol (e.g., "ETH")
            depth: Number of levels to fetch

        Returns:
            Dict with bids, asks, and analysis
        """
        if not self.client:
            return None

        full_symbol = self._get_full_symbol(symbol)

        try:
            orderbook = self.client.api_client.fetch_orderbook(market=full_symbol)
            if orderbook:
                bids = orderbook.get('bids', [])[:depth]
                asks = orderbook.get('asks', [])[:depth]

                # Calculate orderbook imbalance
                bid_volume = sum(float(b[1]) for b in bids) if bids else 0
                ask_volume = sum(float(a[1]) for a in asks) if asks else 0
                total_volume = bid_volume + ask_volume

                imbalance = 0
                if total_volume > 0:
                    imbalance = (bid_volume - ask_volume) / total_volume

                return {
                    'symbol': symbol,
                    'bids': bids,
                    'asks': asks,
                    'bid_volume': bid_volume,
                    'ask_volume': ask_volume,
                    'imbalance': imbalance,  # Positive = more bids (bullish), negative = more asks (bearish)
                    'timestamp': datetime.now().isoformat()
                }
            return None

        except Exception as e:
            logger.debug(f"Orderbook fetch error for {symbol}: {e}")
            return None

    def fetch_trades(self, symbol: str, limit: int = 50) -> Optional[List[Dict]]:
        """
        Fetch recent trades for a symbol

        Args:
            symbol: Base symbol (e.g., "ETH")
            limit: Number of trades to fetch

        Returns:
            List of trade dicts
        """
        if not self.client:
            return None

        full_symbol = self._get_full_symbol(symbol)

        try:
            trades = self.client.api_client.fetch_trades(market=full_symbol)
            if trades and trades.get('results'):
                return trades['results'][:limit]
            return None

        except Exception as e:
            logger.debug(f"Trades fetch error for {symbol}: {e}")
            return None

    def fetch_funding_rate(self, symbol: str) -> Optional[float]:
        """
        Fetch current funding rate for a symbol

        Args:
            symbol: Base symbol (e.g., "ETH")

        Returns:
            Funding rate as decimal (e.g., 0.0001 = 0.01%)
        """
        if not self.client:
            return None

        full_symbol = self._get_full_symbol(symbol)

        try:
            funding = self.client.api_client.fetch_funding_data(market=full_symbol)
            if funding:
                return float(funding.get('funding_rate', 0))
            return None

        except Exception as e:
            logger.debug(f"Funding rate fetch error for {symbol}: {e}")
            return None

    def calculate_technicals(self, trades: List[Dict]) -> Dict:
        """
        Calculate technical indicators from trade data

        Args:
            trades: List of recent trades

        Returns:
            Dict with RSI, MACD, volume analysis
        """
        if not trades or len(trades) < 20:
            return {}

        try:
            # Extract prices and create DataFrame
            prices = [float(t.get('price', 0)) for t in trades if t.get('price')]
            volumes = [float(t.get('size', 0)) for t in trades if t.get('size')]

            if len(prices) < 20:
                return {}

            df = pd.DataFrame({'price': prices, 'volume': volumes})

            # RSI (14 period)
            delta = df['price'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss.replace(0, 0.0001)
            rsi = 100 - (100 / (1 + rs))
            current_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50

            # Simple moving averages
            sma_fast = df['price'].rolling(window=10).mean().iloc[-1]
            sma_slow = df['price'].rolling(window=20).mean().iloc[-1]

            # MACD (simplified)
            ema_12 = df['price'].ewm(span=12, adjust=False).mean()
            ema_26 = df['price'].ewm(span=26, adjust=False).mean()
            macd = ema_12 - ema_26
            signal = macd.ewm(span=9, adjust=False).mean()
            macd_histogram = float(macd.iloc[-1] - signal.iloc[-1])

            # Volume analysis
            avg_volume = df['volume'].mean()
            recent_volume = df['volume'].iloc[-5:].mean()
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1

            # Price momentum
            price_change_pct = ((prices[-1] - prices[0]) / prices[0] * 100) if prices[0] > 0 else 0

            return {
                'rsi': current_rsi,
                'sma_fast': float(sma_fast) if not pd.isna(sma_fast) else 0,
                'sma_slow': float(sma_slow) if not pd.isna(sma_slow) else 0,
                'macd_histogram': macd_histogram,
                'volume_ratio': volume_ratio,
                'price_change_pct': price_change_pct,
                'current_price': prices[-1],
                'high_price': max(prices),
                'low_price': min(prices)
            }

        except Exception as e:
            logger.debug(f"Technical calculation error: {e}")
            return {}

    def fetch_market_data(self, symbol: str) -> Optional[Dict]:
        """
        Fetch comprehensive market data for a symbol

        Args:
            symbol: Base symbol (e.g., "ETH")

        Returns:
            Dict with all market data and technicals
        """
        bbo = self.fetch_bbo(symbol)
        if not bbo:
            return None

        orderbook = self.fetch_orderbook(symbol)
        trades = self.fetch_trades(symbol, limit=100)
        funding = self.fetch_funding_rate(symbol)
        technicals = self.calculate_technicals(trades) if trades else {}

        market_info = self.market_info.get(symbol, {})

        return {
            'symbol': symbol,
            'full_symbol': self._get_full_symbol(symbol),
            'price': bbo.get('mid_price', 0),
            'bid': bbo.get('bid', 0),
            'ask': bbo.get('ask', 0),
            'spread_pct': bbo.get('spread_pct', 0),
            'funding_rate': funding,
            'orderbook_imbalance': orderbook.get('imbalance', 0) if orderbook else 0,
            'bid_volume': orderbook.get('bid_volume', 0) if orderbook else 0,
            'ask_volume': orderbook.get('ask_volume', 0) if orderbook else 0,
            'min_order_size': market_info.get('min_order_size', 0),
            'step_size': market_info.get('step_size', 0),
            **technicals,
            'timestamp': datetime.now().isoformat()
        }

    async def fetch_all_markets(self, symbols: Optional[List[str]] = None) -> Dict[str, Dict]:
        """
        Fetch market data for all available Paradex markets

        Args:
            symbols: List of symbols to fetch (default: all available)

        Returns:
            Dict mapping symbol -> market data
        """
        await self.initialize()

        if symbols is None:
            symbols = self.available_markets

        results = {}
        for i, symbol in enumerate(symbols):
            data = self.fetch_market_data(symbol)
            if data:
                results[symbol] = data

            # Rate limiting
            if i < len(symbols) - 1:
                await asyncio.sleep(0.05)  # 50ms delay

        logger.info(f"Fetched data for {len(results)}/{len(symbols)} Paradex markets")
        return results

    def fetch_positions(self) -> List[Dict]:
        """
        Fetch open positions

        Returns:
            List of position dicts
        """
        if not self.client:
            return []

        try:
            positions = self.client.api_client.fetch_positions()
            if positions and positions.get('results'):
                result = []
                for pos in positions['results']:
                    size = float(pos.get('size', 0))
                    if size != 0:
                        symbol = pos.get('market', '').replace('-USD-PERP', '')
                        result.append({
                            'symbol': symbol,
                            'full_symbol': pos.get('market'),
                            'side': 'LONG' if size > 0 else 'SHORT',
                            'size': abs(size),
                            'entry_price': float(pos.get('average_entry_price', 0)),  # Fixed field name
                            'unrealized_pnl': float(pos.get('unrealized_pnl', 0)),
                            'liquidation_price': float(pos.get('liquidation_price', 0)) if pos.get('liquidation_price') else None
                        })
                return result
            return []

        except Exception as e:
            logger.error(f"Positions fetch error: {e}")
            return []

    def fetch_account_summary(self) -> Dict:
        """
        Fetch account summary

        Returns:
            Dict with account balance and margin info
        """
        if not self.client:
            return {}

        try:
            summary = self.client.api_client.fetch_account_summary()
            return {
                'account_value': float(summary.account_value),
                'free_collateral': float(summary.free_collateral),
                'unrealized_pnl': float(summary.unrealized_pnl) if hasattr(summary, 'unrealized_pnl') else 0
            }

        except Exception as e:
            logger.error(f"Account summary fetch error: {e}")
            return {}

    def get_tradeable_symbols(self) -> List[str]:
        """Get list of tradeable symbols"""
        return self.available_markets.copy()
