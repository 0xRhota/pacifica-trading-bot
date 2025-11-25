"""High Volume Scalping Strategy - 1.5% gain target, quick exits"""

import logging
from typing import Dict, List
from strategies.base_strategy import BaseStrategy
import pandas as pd

logger = logging.getLogger(__name__)


class HighVolumeScalpingStrategy(BaseStrategy):
    """
    High volume scalping strategy
    - Quick entries/exits (0.3-0.5% profit targets)
    - Tight stops (0.2-0.3%)
    - High frequency trading
    - Target: Many small profitable trades
    """
    
    def __init__(self, profit_target: float = 0.015, stop_loss: float = 0.003, max_positions: int = 15, let_runners_run: bool = True):
        """
        Initialize high volume scalping strategy
        
        Args:
            profit_target: Profit target as decimal (0.015 = 1.5%) - only takes profit if momentum weakens
            stop_loss: Stop loss as decimal (0.003 = 0.3%) - always protects downside
            max_positions: Max concurrent positions
            let_runners_run: If True, holds winners when momentum is strong (default: True)
        """
        self.profit_target = profit_target
        self.stop_loss = stop_loss
        self.max_positions = max_positions
        self.let_runners_run = let_runners_run
    
    async def get_decisions(self, market_data: Dict, positions: List[Dict], context: Dict) -> List[Dict]:
        """Get scalping decisions based on RSI oversold and quick profit targets"""
        decisions = []
        
        # Check existing positions for exits
        for pos in positions:
            symbol = pos.get('symbol')
            entry_price = pos.get('entry_price', 0)
            current_price = pos.get('current_price', entry_price)
            
            if entry_price == 0:
                continue
            
            # Get market data for this position to check momentum
            market_data_for_symbol = market_data.get(symbol, {})
            indicators = market_data_for_symbol.get('indicators', {})
            rsi = indicators.get('rsi')
            macd = indicators.get('macd', {})
            macd_signal = macd.get('signal') if isinstance(macd, dict) else None
            macd_histogram = macd.get('histogram') if isinstance(macd, dict) else None
            
            # Calculate P&L
            side = pos.get('side', 'LONG')
            if side == 'LONG':
                pnl_pct = (current_price - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - current_price) / entry_price
            
            # Always exit on stop loss (protect downside)
            if pnl_pct <= -self.stop_loss:
                decisions.append({
                    'action': 'CLOSE',
                    'symbol': symbol,
                    'reason': f'Stop loss hit ({pnl_pct*100:.2f}%)',
                    'confidence': 0.9
                })
                continue
            
            # Smart profit taking: only take profit if momentum is weakening
            if pnl_pct >= self.profit_target:
                if self.let_runners_run:
                    # Check if momentum is still strong
                    momentum_strong = False
                    
                    # RSI climbing = bullish momentum (for LONG positions)
                    if side == 'LONG' and rsi is not None:
                        # If RSI is between 30-70, it's still climbing (momentum)
                        # If RSI > 70, it's overbought (consider taking profit)
                        if rsi < 70:
                            momentum_strong = True
                    
                    # MACD histogram positive = bullish momentum
                    if macd_histogram and macd_histogram > 0:
                        momentum_strong = True
                    
                    # MACD above signal = bullish trend
                    if macd_signal and isinstance(macd, dict) and macd.get('macd', 0) > macd_signal:
                        momentum_strong = True
                    
                    # If momentum is strong, let it run (don't close)
                    if momentum_strong:
                        logger.debug(f"Holding {symbol} runner - momentum strong (RSI: {rsi:.1f}, P&L: {pnl_pct*100:.2f}%)")
                        continue
                    
                    # Momentum weakening - take profit
                    decisions.append({
                        'action': 'CLOSE',
                        'symbol': symbol,
                        'reason': f'Profit target reached ({pnl_pct*100:.2f}%) - momentum weakening (RSI: {rsi:.1f if rsi else "N/A"})',
                        'confidence': 0.9
                    })
                else:
                    # Original behavior: always take profit at target
                    decisions.append({
                        'action': 'CLOSE',
                        'symbol': symbol,
                        'reason': f'Profit target reached ({pnl_pct*100:.2f}%)',
                        'confidence': 0.9
                    })
                continue
        
        # Check if we can open new positions
        open_positions_count = len(positions)
        if open_positions_count >= self.max_positions:
            return decisions
        
        # Look for entry opportunities (RSI oversold for high volume scalping)
        for symbol, data in market_data.items():
            # Skip if already have position
            if any(p.get('symbol') == symbol for p in positions):
                continue
            
            indicators = data.get('indicators', {})
            rsi = indicators.get('rsi')
            price = data.get('price', 0)
            
            if rsi is None or price == 0:
                continue
            
            # Entry: RSI < 30 (oversold) - high volume scalping strategy
            # This generates many small trades with quick profit targets
            if rsi < 30:
                # Calculate confidence based on how oversold (lower RSI = higher confidence)
                confidence = 0.5 + (30 - rsi) / 60  # 0.5 to 1.0
                confidence = min(confidence, 0.9)  # Cap at 0.9
                
                decisions.append({
                    'action': 'BUY',
                    'symbol': symbol,
                    'reason': f'RSI oversold ({rsi:.1f}), high-volume scalping entry targeting {self.profit_target*100:.1f}% profit',
                    'confidence': confidence
                })
                
                # Limit to max positions
                if len(decisions) + open_positions_count >= self.max_positions:
                    break
        
        return decisions

