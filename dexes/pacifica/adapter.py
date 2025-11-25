"""Pacifica DEX Adapter - Dynamic market discovery, no hardcoding"""

import asyncio
import logging
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dexes.base_adapter import BaseAdapter
from dexes.pacifica.pacifica_sdk import PacificaSDK
from llm_agent.data.pacifica_fetcher import PacificaDataFetcher
from llm_agent.data.indicator_calculator import IndicatorCalculator

logger = logging.getLogger(__name__)


class PacificaAdapter(BaseAdapter):
    """Adapter for Pacifica DEX - fetches markets dynamically"""
    
    def __init__(self, private_key: str, account_address: str, base_url: str = "https://api.pacifica.fi/api/v1"):
        self.sdk = PacificaSDK(private_key, account_address, base_url)
        self.data_fetcher = PacificaDataFetcher()
        self.indicator_calc = IndicatorCalculator()
        self._markets: Optional[Dict[str, Dict]] = None  # symbol -> market info
        self._info_cache: Optional[List] = None
        self._info_cache_time: Optional[datetime] = None
        self._info_cache_ttl = timedelta(hours=1)
    
    async def initialize(self):
        """Initialize and fetch markets"""
        await self._fetch_markets()
    
    async def _fetch_markets(self):
        """Fetch markets from /info endpoint"""
        try:
            # Use cached data if available
            now = datetime.now()
            if (self._info_cache is not None and
                self._info_cache_time is not None and
                now - self._info_cache_time < self._info_cache_ttl):
                info_data = self._info_cache
            else:
                # Fetch fresh data
                response = requests.get(f"{self.sdk.base_url}/info", timeout=5)
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success") and result.get("data"):
                        info_data = result["data"]
                        self._info_cache = info_data
                        self._info_cache_time = now
                    else:
                        logger.error("Pacifica /info returned no data")
                        return
                else:
                    logger.error(f"Pacifica /info failed: HTTP {response.status_code}")
                    return
            
            # Build mapping from real exchange data
            self._markets = {}
            for market in info_data:
                symbol = market.get("symbol")
                if symbol:
                    self._markets[symbol] = {
                        'symbol': symbol,
                        'funding_rate': market.get("funding_rate"),
                        'status': 'active',  # Pacifica doesn't have status field
                        'min_amount': market.get("min_amount"),
                        'lot_size': market.get("lot_size"),
                    }
            
            logger.info(f"✅ Fetched {len(self._markets)} markets from Pacifica exchange")
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch markets: {e}")
            raise
    
    def get_name(self) -> str:
        """Return adapter name"""
        return "pacifica"
    
    async def get_markets(self) -> List[Dict]:
        """Get all available markets"""
        if not self._markets:
            await self._fetch_markets()
        return list(self._markets.values())
    
    def get_market_id(self, symbol: str) -> Optional[int]:
        """Pacifica doesn't use market_id, return symbol index"""
        if not self._markets:
            return None
        if symbol in self._markets:
            # Return index in list for compatibility
            return list(self._markets.keys()).index(symbol)
        return None
    
    def get_symbol(self, market_id: int) -> Optional[str]:
        """Get symbol for market_id (index)"""
        if not self._markets:
            return None
        symbols = list(self._markets.keys())
        if 0 <= market_id < len(symbols):
            return symbols[market_id]
        return None
    
    def get_active_markets(self) -> List[str]:
        """Get list of active market symbols"""
        if not self._markets:
            return []
        return list(self._markets.keys())
    
    async def get_positions(self) -> List[Dict]:
        """Get open positions with correct symbol mapping"""
        result = self.sdk.get_positions()
        
        if not result.get('success') or not result.get('data'):
            return []
        
        positions = []
        for pos in result['data']:
            symbol = pos.get('symbol')
            
            if not symbol or symbol not in self._markets:
                logger.warning(f"⚠️ Unknown symbol {symbol} - skipping position")
                continue
            
            entry_price = float(pos.get('entry_price', 0))
            
            # Get current price from orderbook (non-blocking)
            try:
                # Use asyncio.to_thread to avoid blocking event loop
                book_response = await asyncio.to_thread(
                    requests.get, 
                    f"{self.sdk.base_url}/book?symbol={symbol}", 
                    timeout=5
                )
                if book_response.status_code == 200:
                    book_data = book_response.json()
                    if book_data.get('success') and book_data.get('data'):
                        book = book_data['data']
                        if book.get('l') and len(book['l']) > 0:
                            best_bid = float(book['l'][0][0]['p']) if len(book['l'][0]) > 0 else entry_price
                            best_ask = float(book['l'][1][0]['p']) if len(book['l']) > 1 and len(book['l'][1]) > 0 else best_bid
                            current_price = (best_bid + best_ask) / 2
                        else:
                            current_price = entry_price
                    else:
                        current_price = entry_price
                else:
                    current_price = entry_price
            except Exception:
                current_price = entry_price
            
            positions.append({
                'symbol': symbol,
                'side': 'LONG' if pos.get('side') == 'bid' else 'SHORT',
                'size': abs(float(pos.get('amount', 0))),
                'entry_price': entry_price,
                'current_price': current_price,
                'pnl': float(pos.get('pnl', 0)),
            })
        
        return positions
    
    async def get_balance(self) -> float:
        """Get account balance"""
        try:
            # Use asyncio.to_thread to avoid blocking event loop
            response = await asyncio.to_thread(
                requests.get,
                f"{self.sdk.base_url}/account",
                params={"account": self.sdk.account_address},
                timeout=10
            )
            if response.status_code == 200:
                account_data = response.json()
                if account_data.get("success") and account_data.get("data"):
                    data = account_data["data"]
                    available_balance = data.get("available_to_spend") or data.get("balance") or data.get("account_equity") or 0
                    return float(available_balance) if available_balance else 0.0
            return 0.0
        except Exception as e:
            logger.warning(f"Could not fetch balance: {e}")
            return 0.0
    
    async def place_order(self, symbol: str, side: str, amount: float, reduce_only: bool = False) -> Dict:
        """Place order"""
        # Convert side: "bid" = buy, "ask" = sell
        side_str = "bid" if side.lower() == "buy" else "ask"
        amount_str = str(amount)
        # Pacifica SDK create_market_order is synchronous, but we wrap in async
        # Since it's already async-compatible (returns immediately), we can just call it
        result = self.sdk.create_market_order(symbol, side_str, amount_str, reduce_only=reduce_only)
        return result
    
    async def get_market_data(self, symbol: str) -> Optional[Dict]:
        """Get market data for symbol (OHLCV, indicators, etc.)"""
        if symbol not in self._markets:
            return None
        
        # Fetch OHLCV data
        pacifica_data = self.data_fetcher.fetch_market_data(
            symbol=symbol,
            interval="15m",
            limit=100
        )
        
        if not pacifica_data:
            return None
        
        kline_df = pacifica_data.get('kline_df')
        if kline_df is None or kline_df.empty:
            return None
        
        # Calculate indicators
        indicators = self.indicator_calc.calculate_indicators(kline_df)
        
        # Get funding rate
        funding_rate = self.data_fetcher.fetch_funding_rate(symbol)
        
        return {
            'symbol': symbol,
            'price': float(kline_df['close'].iloc[-1]) if not kline_df.empty else 0,
            'volume_24h': float(kline_df['volume'].tail(96).sum()) if len(kline_df) >= 96 else 0,
            'funding_rate': funding_rate or 0,
            'indicators': indicators,
            'kline_df': kline_df,
        }

