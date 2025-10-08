#!/usr/bin/env python3
"""
Pacifica Trading Bot - Volume Farming Strategy
Designed to maximize trading volume while minimizing risk
"""

import asyncio
import aiohttp
import json
import time
import logging
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal
import hmac
import hashlib
import base64
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Position:
    symbol: str
    size: float
    entry_price: float
    side: str
    timestamp: float

@dataclass
class TradingConfig:
    api_key: str
    base_url: str = "https://api.pacifica.fi/api/v1"
    max_position_size: float = 100.0  # USD
    min_profit_threshold: float = 0.001  # 0.1%
    max_loss_threshold: float = 0.002   # 0.2%
    trade_frequency: int = 30  # seconds between trades
    symbols: List[str] = None
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["SOL-USD", "BTC-USD", "ETH-USD"]

class PacificaAPI:
    def __init__(self, config: TradingConfig):
        self.config = config
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _generate_signature(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        """Generate API signature for authentication"""
        message = timestamp + method + path + body
        signature = hmac.new(
            self.config.api_key.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode()
    
    async def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make authenticated API request"""
        url = f"{self.config.base_url}{endpoint}"
        timestamp = str(int(time.time() * 1000))
        
        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": self.config.api_key,
            "X-TIMESTAMP": timestamp,
        }
        
        body = json.dumps(data) if data else ""
        signature = self._generate_signature(timestamp, method.upper(), endpoint, body)
        headers["X-SIGNATURE"] = signature
        
        try:
            if method.upper() == "GET":
                async with self.session.get(url, headers=headers) as response:
                    return await response.json()
            else:
                async with self.session.request(method, url, headers=headers, data=body) as response:
                    return await response.json()
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return {}
    
    async def get_account_info(self, account_address: str = None) -> Dict:
        """Get account information"""
        # Pacifica API requires account address as query param
        # If not provided, we'll need to get it from the API key/wallet
        endpoint = "/account"
        if account_address:
            endpoint += f"?account={account_address}"
        response = await self._make_request("GET", endpoint)
        if response.get("success") and response.get("data"):
            return response["data"][0] if isinstance(response["data"], list) else response["data"]
        return {}
    
    async def get_positions(self) -> List[Dict]:
        """Get current positions"""
        response = await self._make_request("GET", "/positions")
        return response.get("positions", [])
    
    async def get_market_price(self, symbol: str) -> Optional[float]:
        """Get current market price for symbol"""
        # Get price from orderbook mid-price
        orderbook = await self.get_orderbook(symbol)
        if orderbook and "bids" in orderbook and "asks" in orderbook:
            bids = orderbook["bids"]
            asks = orderbook["asks"]
            if bids and asks:
                best_bid = float(bids[0][0])
                best_ask = float(asks[0][0])
                return (best_bid + best_ask) / 2
        return None
    
    async def get_orderbook(self, symbol: str) -> Dict:
        """Get orderbook for symbol"""
        # Pacifica uses /book endpoint with symbol query param
        response = await self._make_request("GET", f"/book?symbol={symbol}")
        if response.get("success") and response.get("data"):
            data = response["data"]
            # Convert Pacifica format to standard format
            # Pacifica returns: l: [[bids], [asks]]
            if "l" in data and isinstance(data["l"], list) and len(data["l"]) >= 2:
                bids = [[item["p"], item["a"]] for item in data["l"][0]] if data["l"][0] else []
                asks = [[item["p"], item["a"]] for item in data["l"][1]] if data["l"][1] else []
                return {"bids": bids, "asks": asks}
        return {}
    
    async def create_market_order(self, symbol: str, side: str, size: float, 
                                take_profit: Optional[float] = None, 
                                stop_loss: Optional[float] = None) -> Dict:
        """Create market order"""
        data = {
            "symbol": symbol,
            "side": side,
            "type": "market",
            "size": size
        }
        
        if take_profit:
            data["take_profit"] = take_profit
        if stop_loss:
            data["stop_loss"] = stop_loss
            
        return await self._make_request("POST", "/orders/create_market", data)
    
    async def cancel_all_orders(self, symbol: str = None) -> Dict:
        """Cancel all orders for symbol or all symbols"""
        data = {}
        if symbol:
            data["symbol"] = symbol
        return await self._make_request("DELETE", "/orders", data)

class VolumeBot:
    def __init__(self, config: TradingConfig, account_address: str = None):
        self.config = config
        self.api = PacificaAPI(config)
        self.account_address = account_address
        self.positions: Dict[str, Position] = {}
        self.total_volume = 0.0
        self.trades_count = 0
        self.running = False
        
    async def start(self):
        """Start the trading bot"""
        logger.info("Starting Pacifica Volume Bot...")
        self.running = True
        
        async with self.api:
            # Get initial account info
            account = await self.api.get_account_info(self.account_address)
            logger.info(f"Account balance: {account}")
            
            # Main trading loop
            while self.running:
                try:
                    await self._trading_cycle()
                    await asyncio.sleep(self.config.trade_frequency)
                except Exception as e:
                    logger.error(f"Trading cycle error: {e}")
                    await asyncio.sleep(5)
    
    async def stop(self):
        """Stop the trading bot"""
        logger.info("Stopping bot...")
        self.running = False
        
        # Close all positions
        async with self.api:
            for symbol in self.positions:
                await self._close_position(symbol)
    
    async def _trading_cycle(self):
        """Execute one trading cycle"""
        for symbol in self.config.symbols:
            try:
                await self._execute_volume_strategy(symbol)
            except Exception as e:
                logger.error(f"Error trading {symbol}: {e}")
    
    async def _execute_volume_strategy(self, symbol: str):
        """Execute volume farming strategy for a symbol"""
        # Get current market data
        price = await self.api.get_market_price(symbol)
        if not price:
            return
            
        orderbook = await self.api.get_orderbook(symbol)
        if not orderbook:
            return
            
        # Strategy 1: Quick round-trip if no position
        if symbol not in self.positions:
            await self._quick_round_trip(symbol, price)
        else:
            # Strategy 2: Check if we should close existing position
            await self._manage_existing_position(symbol, price)
    
    async def _quick_round_trip(self, symbol: str, current_price: float):
        """Execute trade based on market conditions"""
        # Variable position sizes ($5-10 to start small)
        position_value = random.uniform(5, min(self.config.max_position_size, 10))
        size = position_value / current_price

        # Choose side based on market conditions
        side = "buy" if self._should_go_long(symbol) else "sell"

        logger.info(f"Opening {side} position for {symbol} at ${current_price:.4f}, size: {size:.6f} (${position_value:.2f})")

        # Place market order
        order = await self.api.create_market_order(symbol, side, size)
        
        if order and "id" in order:
            # Record position
            self.positions[symbol] = Position(
                symbol=symbol,
                size=size if side == "buy" else -size,
                entry_price=current_price,
                side=side,
                timestamp=time.time()
            )
            
            self.trades_count += 1
            self.total_volume += position_value
            logger.info(f"Position opened. Total volume: ${self.total_volume:.2f}, Trades: {self.trades_count}")
    
    async def _manage_existing_position(self, symbol: str, current_price: float):
        """Manage existing position - close if profitable or cut losses"""
        position = self.positions[symbol]

        # Calculate P&L
        if position.side == "buy":
            pnl_pct = (current_price - position.entry_price) / position.entry_price
        else:
            pnl_pct = (position.entry_price - current_price) / position.entry_price

        # Variable hold times to avoid patterns (60-180 seconds)
        max_hold_time = random.uniform(60, 180)
        time_held = time.time() - position.timestamp

        should_close = (
            pnl_pct >= self.config.min_profit_threshold or  # Take profit
            pnl_pct <= -self.config.max_loss_threshold or   # Stop loss
            time_held > max_hold_time  # Variable time-based exit
        )

        if should_close:
            await self._close_position(symbol)
            logger.info(f"Position closed for {symbol}. P&L: {pnl_pct:.4f}%, Time held: {time_held:.1f}s")
    
    async def _close_position(self, symbol: str):
        """Close position for symbol"""
        if symbol not in self.positions:
            return
            
        position = self.positions[symbol]
        
        # Determine opposite side
        close_side = "sell" if position.side == "buy" else "buy"
        
        # Place closing order
        order = await self.api.create_market_order(symbol, close_side, abs(position.size))
        
        if order:
            # Update volume
            position_value = abs(position.size) * position.entry_price
            self.total_volume += position_value
            self.trades_count += 1
            
            # Remove position
            del self.positions[symbol]
            
            logger.info(f"Position closed for {symbol}. Total volume: ${self.total_volume:.2f}")
    
    def _should_go_long(self, symbol: str) -> bool:
        """Decision logic based on recent price action"""
        # Bull market mode - longs only
        return True

async def main():
    # Configuration
    config = TradingConfig(
        api_key="7a7voQH3WWD1fi6B25gWSzCUicvmrbtJh8sb2McJeWeg",
        max_position_size=100.0,  # $100 max per position
        trade_frequency=45,  # 45 seconds between trades
        symbols=["SOL-USD", "BTC-USD", "ETH-USD"]
    )
    
    # Create and start bot
    bot = VolumeBot(config)
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())