"""
Trading strategies for volume farming on Pacifica
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import time
import random

logger = logging.getLogger(__name__)

@dataclass
class TradeSignal:
    symbol: str
    side: str  # "buy" or "sell"
    size: float
    confidence: float
    reason: str

class VolumeStrategy:
    """Main volume farming strategy"""
    
    def __init__(self, api_client):
        self.api = api_client
        self.last_trade_times = {}
        self.trade_count = 0
        
    async def generate_signals(self, symbols: List[str]) -> List[TradeSignal]:
        """Generate trading signals for volume farming"""
        signals = []
        
        for symbol in symbols:
            signal = await self._analyze_symbol(symbol)
            if signal:
                signals.append(signal)
                
        return signals
    
    async def _analyze_symbol(self, symbol: str) -> Optional[TradeSignal]:
        """Analyze symbol for trading opportunity based on market conditions"""

        # Randomized cooldown to avoid patterns (45-90 seconds)
        cooldown = random.uniform(45, 90)
        last_trade = self.last_trade_times.get(symbol, 0)
        if time.time() - last_trade < cooldown:
            return None

        try:
            # Get market data
            price = await self.api.get_market_price(symbol)
            orderbook = await self.api.get_orderbook(symbol)

            if not price or not orderbook:
                return None

            # Analyze orderbook for real opportunities
            if "bids" not in orderbook or "asks" not in orderbook:
                return None

            bids = orderbook.get("bids", [])
            asks = orderbook.get("asks", [])

            if not bids or not asks:
                return None

            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            spread = best_ask - best_bid
            spread_pct = spread / best_bid

            # Only trade if there's a reasonable spread (0.05%+ to cover fees)
            if spread_pct < 0.0005:
                return None

            # Decide direction based on orderbook depth and spread
            bid_volume = sum(float(b[1]) for b in bids[:5])
            ask_volume = sum(float(a[1]) for a in asks[:5])

            # Bull market mode - longs only, but vary confidence based on liquidity
            side = "buy"

            # Higher confidence when there's good ask-side liquidity
            if ask_volume > bid_volume * 1.2:
                confidence = min(0.9, 0.7 + (ask_volume / bid_volume) * 0.1)
            else:
                confidence = 0.65

            # Variable position sizes ($5-10 to start small)
            target_value = random.uniform(5, 10)
            size = target_value / price

            signal = TradeSignal(
                symbol=symbol,
                side=side,
                size=size,
                confidence=confidence,
                reason=f"Spread {spread_pct:.4f}%, {side} into liquidity"
            )

            self.last_trade_times[symbol] = time.time()
            self.trade_count += 1

            return signal

        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None

class SpreadCaptureStrategy:
    """Strategy to capture bid-ask spread for small profits"""
    
    def __init__(self, api_client):
        self.api = api_client
        
    async def generate_signals(self, symbols: List[str]) -> List[TradeSignal]:
        """Generate spread capture signals"""
        signals = []
        
        for symbol in symbols:
            signal = await self._check_spread_opportunity(symbol)
            if signal:
                signals.append(signal)
                
        return signals
    
    async def _check_spread_opportunity(self, symbol: str) -> Optional[TradeSignal]:
        """Check for profitable spread opportunities"""
        try:
            orderbook = await self.api.get_orderbook(symbol)
            
            if not orderbook or "bids" not in orderbook or "asks" not in orderbook:
                return None
                
            bids = orderbook["bids"]
            asks = orderbook["asks"]
            
            if not bids or not asks:
                return None
                
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            
            spread_pct = (best_ask - best_bid) / best_bid
            
            # If spread is large enough, try to capture it
            if spread_pct > 0.001:  # 0.1% spread
                # Place order between bid and ask
                mid_price = (best_bid + best_ask) / 2
                size = 50.0 / mid_price  # $50 position
                
                return TradeSignal(
                    symbol=symbol,
                    side="buy",  # Start with buy, will flip after
                    size=size,
                    confidence=0.8,
                    reason=f"Spread capture - {spread_pct:.4f}% spread"
                )
                
        except Exception as e:
            logger.error(f"Error checking spread for {symbol}: {e}")
            
        return None

class MomentumStrategy:
    """Simple momentum strategy for quick profits"""
    
    def __init__(self, api_client):
        self.api = api_client
        self.price_history = {}
        
    async def generate_signals(self, symbols: List[str]) -> List[TradeSignal]:
        """Generate momentum-based signals"""
        signals = []
        
        for symbol in symbols:
            signal = await self._check_momentum(symbol)
            if signal:
                signals.append(signal)
                
        return signals
    
    async def _check_momentum(self, symbol: str) -> Optional[TradeSignal]:
        """Check for momentum trading opportunities"""
        try:
            current_price = await self.api.get_market_price(symbol)
            
            if not current_price:
                return None
                
            # Store price history
            if symbol not in self.price_history:
                self.price_history[symbol] = []
                
            self.price_history[symbol].append({
                "price": current_price,
                "timestamp": time.time()
            })
            
            # Keep only last 10 price points
            self.price_history[symbol] = self.price_history[symbol][-10:]
            
            # Need at least 3 price points for momentum
            if len(self.price_history[symbol]) < 3:
                return None
                
            prices = [p["price"] for p in self.price_history[symbol]]
            
            # Calculate simple momentum
            short_ma = sum(prices[-3:]) / 3
            long_ma = sum(prices) / len(prices)
            
            momentum = (short_ma - long_ma) / long_ma
            
            # Trade on momentum
            if abs(momentum) > 0.001:  # 0.1% momentum
                side = "buy" if momentum > 0 else "sell"
                size = 75.0 / current_price  # $75 position
                
                return TradeSignal(
                    symbol=symbol,
                    side=side,
                    size=size,
                    confidence=min(abs(momentum) * 100, 0.9),
                    reason=f"Momentum {momentum:.4f}"
                )
                
        except Exception as e:
            logger.error(f"Error checking momentum for {symbol}: {e}")
            
        return None