"""Lighter DEX Adapter - Dynamic market discovery, no hardcoding"""

import asyncio
import logging
from typing import Dict, List, Optional
import lighter
from .lighter_sdk import LighterSDK
from dexes.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class LighterAdapter(BaseAdapter):
    """Adapter for Lighter DEX - fetches markets dynamically"""
    
    def __init__(self, api_key_private: str, api_key_public: str, account_index: int, api_key_index: int):
        # SDK will be initialized asynchronously
        if not api_key_private:
            raise ValueError("LIGHTER_API_KEY_PRIVATE is required. Check your .env file.")
        if not api_key_public:
            raise ValueError("LIGHTER_API_KEY_PUBLIC is required. Check your .env file.")
        self.api_key_private = api_key_private
        self.api_key_public = api_key_public
        self.account_index = account_index
        self.api_key_index = api_key_index
        self.sdk: Optional[LighterSDK] = None
        self._markets: Optional[Dict[int, Dict]] = None  # market_id -> {symbol, status, ...}
        self._market_id_to_symbol: Optional[Dict[int, str]] = None
        self._symbol_to_market_id: Optional[Dict[str, int]] = None
        # Cached API instances (created once, reused for all calls - same as old bot pattern)
        self._candlestick_api = None
        self._funding_api = None

    async def initialize(self):
        """Initialize SDK and fetch markets"""
        # Initialize SDK (matches LighterSDK.__init__ signature)
        # SDK __init__ is synchronous, which is fine
        self.sdk = LighterSDK(
            private_key=self.api_key_private,
            account_index=self.account_index,
            api_key_index=self.api_key_index
        )

        # Initialize API instances (same pattern as old bot - create once, reuse for all calls)
        import lighter
        self._candlestick_api = lighter.CandlestickApi(self.sdk.api_client)
        self._funding_api = lighter.FundingApi(self.sdk.api_client)
        logger.info("✅ Lighter API clients initialized (CandlestickApi, FundingApi)")

        await self._fetch_markets()
    
    async def _fetch_markets(self):
        """Fetch markets from exchange and build mapping"""
        try:
            config = lighter.Configuration(host='https://mainnet.zklighter.elliot.ai')
            api_client = lighter.ApiClient(configuration=config)
            order_api = lighter.OrderApi(api_client)
            
            # Lighter SDK order_books() is async - await it directly
            books = await order_api.order_books()
            await api_client.close()
            
            # Build mapping from real exchange data
            self._markets = {}
            self._market_id_to_symbol = {}
            self._symbol_to_market_id = {}
            
            if hasattr(books, 'order_books'):
                for book in books.order_books:
                    market_id = book.market_id
                    symbol = book.symbol
                    status = book.status
                    
                    # Store full book object for access to all properties
                    self._markets[market_id] = {
                        'symbol': symbol,
                        'market_id': market_id,
                        'status': status,
                        'taker_fee': book.taker_fee,
                        'maker_fee': book.maker_fee,
                        'supported_size_decimals': book.supported_size_decimals if hasattr(book, 'supported_size_decimals') else None,
                        'min_base_amount': book.min_base_amount if hasattr(book, 'min_base_amount') else None,
                    }
                    self._market_id_to_symbol[market_id] = symbol
                    self._symbol_to_market_id[symbol] = market_id
            
            logger.info(f"✅ Fetched {len(self._markets)} markets from Lighter exchange")
            logger.info(f"   Active markets: {sum(1 for m in self._markets.values() if m['status'] == 'active')}")

            # Log known market symbols with their IDs for debugging
            known_symbols = ['BTC', 'SOL', 'ETH', 'PENGU', 'XPL', 'ASTER']
            logger.info("   Known symbol mappings:")
            for sym in known_symbols:
                mid = self._symbol_to_market_id.get(sym)
                status = self._markets.get(mid, {}).get('status', 'unknown') if mid else 'not_found'
                logger.info(f"     {sym}: market_id={mid} status={status}")
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch markets: {e}")
            raise
    
    def get_name(self) -> str:
        """Return adapter name"""
        return "lighter"
    
    async def get_markets(self) -> List[Dict]:
        """Get all available markets"""
        if not self._markets:
            await self._fetch_markets()
        return list(self._markets.values())
    
    def get_market_id(self, symbol: str) -> Optional[int]:
        """Get market_id for symbol"""
        if not self._symbol_to_market_id:
            return None
        return self._symbol_to_market_id.get(symbol)
    
    def get_symbol(self, market_id: int) -> Optional[str]:
        """Get symbol for market_id"""
        if not self._market_id_to_symbol:
            return None
        return self._market_id_to_symbol.get(market_id)
    
    def get_active_markets(self) -> List[str]:
        """Get list of active market symbols"""
        if not self._markets:
            return []
        return [m['symbol'] for m in self._markets.values() if m['status'] == 'active']
    
    async def get_positions(self) -> List[Dict]:
        """Get open positions with correct symbol mapping"""
        result = await self.sdk.get_positions()
        
        if not result.get('success') or not result.get('data'):
            return []
        
        positions = []
        for pos in result['data']:
            market_id = pos.get('market_id')
            symbol = self.get_symbol(market_id)
            
            if not symbol:
                logger.warning(f"⚠️ Unknown market_id {market_id} - skipping position")
                continue
            
            # Get current price from market data
            market_data = await self.get_market_data(symbol)
            current_price = market_data.get('price', pos.get('entry_price', 0)) if market_data else pos.get('entry_price', 0)
            
            # Size is in base units (from API)
            size_base_units = abs(pos.get('size', 0))
            
            # Calculate P&L percentage if not provided
            entry_price = pos.get('entry_price', 0) or 0
            is_long = pos.get('is_long', True)
            pnl_pct = pos.get('pnl', 0) or 0
            
            # If P&L not provided, calculate it
            if pnl_pct == 0 and entry_price > 0 and current_price > 0:
                if is_long:
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                else:  # SHORT
                    pnl_pct = ((entry_price - current_price) / entry_price) * 100
            
            positions.append({
                'symbol': symbol,
                'market_id': market_id,
                'side': pos.get('side', 'LONG') if pos.get('side') else ('LONG' if is_long else 'SHORT'),
                'size': size_base_units,  # Base units (for closing)
                'size_usd': size_base_units * current_price if current_price > 0 else 0,  # USD value
                'size_raw': pos.get('size_raw', pos.get('size', 0)),
                'is_long': is_long,
                'entry_price': entry_price,
                'current_price': current_price,
                'pnl': pnl_pct,  # P&L percentage
                'time_held': 'N/A',  # Lighter API doesn't provide this, but include for formatting
            })
        
        return positions
    
    async def get_balance(self) -> float:
        """Get account balance"""
        return await self.sdk.get_balance()
    
    async def place_order(self, symbol: str, side: str, amount: float, reduce_only: bool = False) -> Dict:
        """Place order using dynamic market mapping - REUSES WORKING SDK METHOD"""
        if not self.sdk:
            return {'success': False, 'error': 'SDK not initialized'}
        
        # Get market_id dynamically (this is what makes it work with ALL markets)
        market_id = self.get_market_id(symbol)
        if market_id is None:
            return {'success': False, 'error': f'Unknown symbol: {symbol}'}
        
        # Get market info for decimals
        market_info = self._markets.get(market_id)
        if not market_info:
            return {'success': False, 'error': f'No market info for {symbol}'}
        
        # Get decimals from market info
        # ⚠️ CRITICAL: API sometimes returns WRONG decimals (e.g., BTC returns 5 but should be 6)
        # This causes orders to be 10x too small and get rejected by exchange
        # Use known correct decimals from SDK fallback, override API if wrong
        CORRECT_DECIMALS = {
            'BTC': 6,  # API incorrectly returns 5
            'SOL': 3,
            'ETH': 4,
            'PENGU': 0,
            'XPL': 2,
            'ASTER': 2,
            'ZEC': 3,  # Conservative estimate
        }

        # Try to get from our known correct values first
        decimals = CORRECT_DECIMALS.get(symbol)
        if decimals is None:
            # Fall back to API value only if we don't have a known correct value
            decimals = market_info.get('supported_size_decimals', 3)
            if decimals is None:
                decimals = 3  # Safe default
        decimals = int(decimals)
        
        # Convert side: SDK expects 'bid' for buy, 'ask' for sell
        side_str = "bid" if side.lower() == "buy" else "ask"
        
        # Get market data for price (needed for conversion)
        market_data = await self.get_market_data(symbol)
        if not market_data:
            return {'success': False, 'error': f'Could not get market data for {symbol}'}
        
        current_price = market_data.get('price', 0)
        if current_price == 0:
            return {'success': False, 'error': f'Invalid price for {symbol}'}
        
        # Convert USD amount to base units
        base_units = amount / current_price
        
        # Use SDK's create_market_order with dynamic market_id and decimals
        try:
            logger.info(f"📤 Placing {side.upper()} order for {symbol} | market_id={market_id} | USD=${amount:.2f} | base_units={base_units:.6f} | decimals={decimals}")
            result = await self.sdk.create_market_order(
                symbol=symbol,
                side=side_str,
                amount=base_units,
                reduce_only=reduce_only,
                market_id=market_id,  # Pass dynamic market_id
                decimals=decimals,  # Pass dynamic decimals
                current_price=current_price  # Pass current price for reduce-only orders
            )
            
            if result.get('success'):
                logger.info(f"✅ Order placed successfully for {symbol} | tx_hash={result.get('tx_hash')}")
            else:
                logger.error(f"❌ Order failed for {symbol}: {result.get('error')}")
            
            return result
        except Exception as e:
            logger.error(f"❌ Exception placing order for {symbol}: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    async def get_market_data(self, symbol: str) -> Optional[Dict]:
        """Get market data for symbol (OHLCV, indicators, etc.) - supports ALL markets dynamically"""
        market_id = self.get_market_id(symbol)
        if market_id is None:  # Use 'is None' not 'not market_id' because market_id=0 is valid!
            logger.warning(f"❌ No market_id found for symbol {symbol}")
            logger.debug(f"   Available mappings: {self._symbol_to_market_id}")
            return None

        if not self.sdk or not hasattr(self.sdk, 'api_client'):
            logger.error(f"❌ SDK not initialized or missing api_client for {symbol}")
            return None

        try:
            logger.debug(f"📊 Fetching market data for {symbol} (market_id={market_id})")
            import pandas as pd
            import time
            from llm_agent.data.indicator_calculator import IndicatorCalculator

            # Use cached candlestick_api (same pattern as old bot - reuse the same instance)
            candlestick_api = self._candlestick_api
            if not candlestick_api:
                logger.error(f"❌ CandlestickApi not initialized for {symbol}")
                return None

            indicator_calc = IndicatorCalculator()
            
            # Fetch both 5m and 4h timeframes
            end_timestamp = int(time.time() * 1000)
            
            # Fetch 5m candles (for EMA, MACD, RSI, Bollinger Bands, Stochastic)
            limit_5m = 100
            start_timestamp_5m = end_timestamp - (limit_5m * 5 * 60 * 1000)  # 5 min intervals
            
            result_5m = await candlestick_api.candlesticks(
                market_id=market_id,
                resolution="5m",
                start_timestamp=start_timestamp_5m,
                end_timestamp=end_timestamp,
                count_back=limit_5m
            )
            
            # Fetch 4h candles (for EMA, ATR, ADX)
            limit_4h = 100
            start_timestamp_4h = end_timestamp - (limit_4h * 4 * 60 * 60 * 1000)  # 4 hour intervals
            
            result_4h = await candlestick_api.candlesticks(
                market_id=market_id,
                resolution="4h",
                start_timestamp=start_timestamp_4h,
                end_timestamp=end_timestamp,
                count_back=limit_4h
            )
            
            # Process 5m data
            kline_df_5m = None
            indicators_5m = {}
            if result_5m and hasattr(result_5m, 'candlesticks') and result_5m.candlesticks:
                data_5m = []
                for candle in result_5m.candlesticks:
                    data_5m.append({
                        'timestamp': candle.timestamp,
                        'open': float(candle.open),
                        'high': float(candle.high),
                        'low': float(candle.low),
                        'close': float(candle.close),
                        'volume': float(candle.volume1) if hasattr(candle, 'volume1') else float(candle.volume0)
                    })
                
                kline_df_5m = pd.DataFrame(data_5m)
                kline_df_5m['timestamp'] = pd.to_datetime(kline_df_5m['timestamp'], unit='ms', errors='coerce')
                kline_df_5m = kline_df_5m.sort_values('timestamp').reset_index(drop=True)
                kline_df_5m.set_index('timestamp', inplace=True)
                
                if not kline_df_5m.empty:
                    # Calculate 5m indicators: EMA, MACD, RSI, Bollinger Bands, Stochastic
                    kline_df_5m = indicator_calc.calculate_all_indicators(kline_df_5m, timeframe="5m")
                    indicators_5m = indicator_calc.get_latest_values(kline_df_5m, timeframe="5m")
            
            # Process 4h data
            kline_df_4h = None
            indicators_4h = {}
            if result_4h and hasattr(result_4h, 'candlesticks') and result_4h.candlesticks:
                data_4h = []
                for candle in result_4h.candlesticks:
                    data_4h.append({
                        'timestamp': candle.timestamp,
                        'open': float(candle.open),
                        'high': float(candle.high),
                        'low': float(candle.low),
                        'close': float(candle.close),
                        'volume': float(candle.volume1) if hasattr(candle, 'volume1') else float(candle.volume0)
                    })
                
                kline_df_4h = pd.DataFrame(data_4h)
                kline_df_4h['timestamp'] = pd.to_datetime(kline_df_4h['timestamp'], unit='ms', errors='coerce')
                kline_df_4h = kline_df_4h.sort_values('timestamp').reset_index(drop=True)
                kline_df_4h.set_index('timestamp', inplace=True)
                
                if not kline_df_4h.empty:
                    # Calculate 4h indicators: EMA, ATR, ADX
                    kline_df_4h = indicator_calc.calculate_all_indicators(kline_df_4h, timeframe="4h")
                    indicators_4h = indicator_calc.get_latest_values(kline_df_4h, timeframe="4h")
            
            # Use 5m data for price/volume (most recent), fallback to 4h if 5m unavailable
            if kline_df_5m is not None and not kline_df_5m.empty:
                kline_df = kline_df_5m
                current_price = float(kline_df_5m['close'].iloc[-1])
                volume_24h = float(kline_df_5m['volume'].tail(96).sum()) if len(kline_df_5m) >= 96 else 0
            elif kline_df_4h is not None and not kline_df_4h.empty:
                kline_df = kline_df_4h
                current_price = float(kline_df_4h['close'].iloc[-1])
                volume_24h = float(kline_df_4h['volume'].tail(6).sum()) if len(kline_df_4h) >= 6 else 0  # 6 * 4h = 24h
            else:
                logger.warning(f"❌ No candlestick data returned for {symbol} (market_id={market_id})")
                return None
            
            # Combine indicators from both timeframes
            indicators = {
                **indicators_5m,  # 5m: EMA, MACD, RSI, Bollinger Bands, Stochastic
                **{f"4h_{k}": v for k, v in indicators_4h.items() if k != 'price'}  # 4h: EMA, ATR, ADX (prefix with 4h_)
            }
            # Add 4h price separately if needed
            if indicators_4h.get('price'):
                indicators['4h_price'] = indicators_4h['price']
            
            # Get funding rate
            funding_rate = 0
            try:
                # Use cached funding_api (same pattern as old bot)
                funding_api = self._funding_api
                if funding_api:
                    funding_rates = await funding_api.funding_rates()
                else:
                    funding_rates = None

                if funding_rates:
                    for rate in funding_rates:
                        if hasattr(rate, 'market_id') and rate.market_id == market_id:
                            funding_rate = float(rate.funding_rate) if hasattr(rate, 'funding_rate') else 0
                            break
            except Exception:
                pass  # Funding rate optional
            
            current_price = float(kline_df['close'].iloc[-1]) if not kline_df.empty else 0
            volume_24h = float(kline_df['volume'].tail(96).sum()) if len(kline_df) >= 96 else 0

            logger.debug(f"✅ Successfully fetched market data for {symbol}: price={current_price:.2f}, candles={len(kline_df)}, indicators={list(indicators.keys())[:5]}")
            return {
                'symbol': symbol,
                'price': current_price,
                'volume_24h': volume_24h,
                'funding_rate': funding_rate,
                'indicators': indicators,
                'kline_df': kline_df,
                'kline_df_5m': kline_df_5m,  # 5m data for reference
                'kline_df_4h': kline_df_4h,  # 4h data for reference
            }
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol} (market_id={market_id}): {type(e).__name__}: {e}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

