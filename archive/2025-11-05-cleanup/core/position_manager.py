"""Position Manager - Unified position tracking"""

import asyncio
import logging
from typing import List, Dict, Optional
from trade_tracker import TradeTracker
from dexes.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class PositionManager:
    """Unified position tracking - works with any DEX"""
    
    def __init__(self, adapter: BaseAdapter, logger_instance):
        self.adapter = adapter
        self.logger = logger_instance
        self.tracker = TradeTracker(dex=adapter.get_name())
    
    async def get_positions(self) -> List[Dict]:
        """Get positions from adapter, validate against markets, update current prices"""
        positions = await self.adapter.get_positions()
        
        # Validate each position and update current prices
        validated = []
        markets = set(self.adapter.get_active_markets())
        
        # Fetch all market data in parallel for performance
        symbols_to_fetch = [p.get('symbol') for p in positions if p.get('symbol') and p.get('symbol') in markets]
        if symbols_to_fetch:
            market_data_tasks = [self.adapter.get_market_data(s) for s in symbols_to_fetch]
            market_data_results = await asyncio.gather(*market_data_tasks, return_exceptions=True)
            market_data_map = dict(zip(symbols_to_fetch, market_data_results))
        else:
            market_data_map = {}
        
        for pos in positions:
            symbol = pos.get('symbol')
            if not symbol:
                self.logger.warning("Position missing symbol", component="position_manager", data={"pos": pos})
                continue
            
            # Check: Does symbol exist in markets?
            if symbol not in markets:
                self.logger.warning(f"Position symbol {symbol} not in markets", 
                                   component="position_manager")
                continue
            
            # Get current price from pre-fetched data
            market_data = market_data_map.get(symbol)
            if market_data and not isinstance(market_data, Exception):
                pos['current_price'] = market_data.get('price', pos.get('entry_price', 0))
            else:
                # Fallback to entry price if market data fetch failed
                pos['current_price'] = pos.get('entry_price', 0)
            
            validated.append(pos)
        
        return validated
    
    def log_entry(self, symbol: str, side: str, entry_price: float, size: float, order_id: str = None):
        """Log new position entry - order_id is persisted in TradeTracker"""
        # Convert side to lowercase for TradeTracker
        side_lower = side.lower() if side else "buy"
        # TradeTracker expects: order_id, symbol, side, size, entry_price, notes
        trade_id = self.tracker.log_entry(order_id, symbol, side_lower, size, entry_price)
        return trade_id
    
    def get_order_id_for_symbol(self, symbol: str) -> Optional[str]:
        """Get order_id for symbol from TradeTracker (persistent storage)"""
        return self.tracker.get_order_id_for_symbol(symbol)
    
    def log_exit(self, order_id: str, exit_price: float, pnl: float, exit_reason: str = None):
        """Log position exit by order_id"""
        # TradeTracker.log_exit expects: order_id, exit_price, exit_reason, fees
        # Calculate fees as 0 for now (can be enhanced later)
        fees = 0.0
        self.tracker.log_exit(order_id, exit_price, exit_reason, fees)
    
    def get_recently_closed_symbols(self, hours: int = 2) -> List[str]:
        """Get symbols recently closed"""
        recent_trades = self.tracker.get_recent_trades(hours=hours, limit=100)
        return [t['symbol'] for t in recent_trades if t.get('status') == 'closed']

